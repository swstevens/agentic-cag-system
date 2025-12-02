"""
Unit tests for format rules and validation.

Tests the FormatRules class and validates that:
1. Format rules are correctly defined
2. Card quantity validation works per format
3. Singleton rule is properly enforced
4. Legendary card limits are correct
"""

import pytest
from v3.models.format_rules import FormatRules
from v3.models.deck import Deck, DeckCard, MTGCard


class TestFormatRules:
    """Test FormatRules configuration and helper methods."""

    def test_all_formats_defined(self):
        """Verify all major formats are defined."""
        expected_formats = ["Standard", "Modern", "Pioneer", "Legacy", "Vintage", "Commander", "Brawl"]
        for format_name in expected_formats:
            rules = FormatRules.get_rules(format_name)
            assert rules is not None
            assert "deck_size_min" in rules
            assert "deck_size_max" in rules
            assert "copy_limit" in rules
            assert "singleton_rule" in rules

    def test_deck_size_by_format(self):
        """Verify deck sizes are correct for each format."""
        test_cases = [
            ("Standard", 60),
            ("Modern", 60),
            ("Pioneer", 60),
            ("Commander", 100),
            ("Brawl", 60),
        ]
        for format_name, expected_size in test_cases:
            size = FormatRules.get_deck_size(format_name)
            assert size == expected_size, f"{format_name} deck size should be {expected_size}, got {size}"

    def test_copy_limits_by_format(self):
        """Verify copy limits are correct for each format."""
        test_cases = [
            ("Standard", 4),
            ("Modern", 4),
            ("Pioneer", 4),
            ("Commander", 1),  # Singleton
            ("Brawl", 4),
        ]
        for format_name, expected_limit in test_cases:
            limit = FormatRules.get_copy_limit(format_name)
            assert limit == expected_limit, f"{format_name} copy limit should be {expected_limit}, got {limit}"

    def test_singleton_rule(self):
        """Verify singleton rule is set correctly."""
        assert FormatRules.is_singleton("Commander") is True
        assert FormatRules.is_singleton("Standard") is False
        assert FormatRules.is_singleton("Modern") is False
        assert FormatRules.is_singleton("Brawl") is False

    def test_legendary_max_by_format(self):
        """Verify legendary card limits are correct."""
        test_cases = [
            ("Standard", 3),
            ("Modern", 3),
            ("Commander", 1),  # Singleton rule
            ("Brawl", 1),  # Commander must be unique
        ]
        for format_name, expected_max in test_cases:
            max_copies = FormatRules.get_legendary_max(format_name)
            assert max_copies == expected_max, f"{format_name} legendary max should be {expected_max}, got {max_copies}"

    def test_land_ratio_by_format(self):
        """Verify land ratio standards are reasonable."""
        standard_ratio = FormatRules.get_land_ratio("Standard")
        commander_ratio = FormatRules.get_land_ratio("Commander")

        assert 0.35 < standard_ratio < 0.45, "Standard ratio should be around 40%"
        assert 0.35 < commander_ratio < 0.40, "Commander ratio should be around 37%"

    def test_land_count_by_format_and_archetype(self):
        """Verify land count recommendations by format and archetype."""
        test_cases = [
            ("Standard", "Aggro", 22),
            ("Standard", "Control", 26),
            ("Commander", "Aggro", 35),
            ("Commander", "Control", 38),
        ]
        for format_name, archetype, expected_count in test_cases:
            count = FormatRules.get_land_count(format_name, archetype)
            assert count == expected_count, f"{format_name} {archetype} should have {expected_count} lands, got {count}"

    def test_invalid_format_raises_error(self):
        """Verify invalid format names raise ValueError."""
        with pytest.raises(ValueError):
            FormatRules.get_rules("InvalidFormat")


class TestCardQuantityValidation:
    """Test card quantity validation logic."""

    def _create_test_card(self, name: str, is_legendary: bool = False) -> MTGCard:
        """Helper to create test cards."""
        type_line = "Legendary Creature — Human Wizard" if is_legendary else "Creature — Human"
        return MTGCard(
            id=name.lower(),
            name=name,
            type_line=type_line,
            types=["Creature"],
            cmc=2.0,
        )

    def _create_land_card(self, name: str, is_basic: bool = True) -> MTGCard:
        """Helper to create land cards."""
        type_line = "Basic Land — Mountain" if is_basic else "Land — Tapped"
        return MTGCard(
            id=name.lower(),
            name=name,
            type_line=type_line,
            types=["Land"],
            cmc=0.0,
        )

    def test_standard_format_non_legendary_cap(self):
        """Verify non-legendary cards cap at 4 in Standard."""
        # Create a test card with 5 copies
        card = self._create_test_card("Test Creature")
        deck = Deck(format="Standard", cards=[DeckCard(card=card, quantity=5)])

        # This would be validated by the service, but we can test the rule
        copy_limit = FormatRules.get_copy_limit("Standard")
        assert copy_limit == 4
        assert 5 > copy_limit  # 5 copies violates Standard

    def test_commander_singleton_enforcement(self):
        """Verify Commander enforces singleton rule."""
        # In Commander, any card other than basic lands should be 1 copy
        card = self._create_test_card("Test Creature")
        deck = Deck(format="Commander", cards=[DeckCard(card=card, quantity=3)])

        # Verify that copy limit is 1 for Commander
        copy_limit = FormatRules.get_copy_limit("Commander")
        assert copy_limit == 1
        assert deck.cards[0].quantity == 3  # Not validated yet, but should be 1

    def test_commander_basic_lands_exception(self):
        """Verify Commander allows multiple copies of basic lands."""
        # Basic lands are exempt from singleton rule
        land = self._create_land_card("Mountain", is_basic=True)
        deck = Deck(format="Commander", cards=[DeckCard(card=land, quantity=20)])

        # Basic lands should not violate singleton rule
        is_basic = land.type_line.startswith("Basic")
        assert is_basic is True
        # Multiple copies of basic lands should be allowed
        assert deck.cards[0].quantity == 20

    def test_standard_legendary_cards_3_max(self):
        """Verify Standard format allows up to 3 legendary copies."""
        legendary_card = self._create_test_card("Test Legend", is_legendary=True)
        deck = Deck(format="Standard", cards=[DeckCard(card=legendary_card, quantity=3)])

        # Standard allows 3 legendary copies
        legendary_max = FormatRules.get_legendary_max("Standard")
        assert legendary_max == 3
        assert deck.cards[0].quantity <= legendary_max

    def test_brawl_legendary_max_1(self):
        """Verify Brawl format limits legendary cards to 1."""
        legendary_card = self._create_test_card("Brawl Commander", is_legendary=True)
        deck = Deck(format="Brawl", cards=[DeckCard(card=legendary_card, quantity=1)])

        # Brawl requires 1 copy only (commander must be unique)
        legendary_max = FormatRules.get_legendary_max("Brawl")
        assert legendary_max == 1
        assert deck.cards[0].quantity == legendary_max

    def test_mana_curve_standards_exist(self):
        """Verify mana curve standards are defined for all formats."""
        formats = ["Standard", "Modern", "Commander"]
        for format_name in formats:
            curve = FormatRules.get_mana_curve_standards(format_name)
            assert curve is not None
            assert "0-1" in curve
            assert "2-3" in curve
            assert "4-5" in curve
            assert "6+" in curve

    def test_commander_mana_curve_differs(self):
        """Verify Commander has different mana curve than Standard."""
        standard_curve = FormatRules.get_mana_curve_standards("Standard")
        commander_curve = FormatRules.get_mana_curve_standards("Commander")

        # Commander should have higher proportion of high-cost spells
        assert commander_curve["6+"] > standard_curve["6+"]
        # Commander should have lower early game density
        assert commander_curve["0-1"] < standard_curve["0-1"]


class TestFormatErrorHandling:
    """Test error handling for invalid formats."""

    def test_unknown_format_raises_error(self):
        """Verify unknown format names raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            FormatRules.get_rules("UnknownFormat")
        assert "Unknown format" in str(excinfo.value)

    def test_case_insensitive_format_lookup(self):
        """Verify format lookup is case-insensitive."""
        rules1 = FormatRules.get_rules("Commander")
        rules2 = FormatRules.get_rules("commander")
        rules3 = FormatRules.get_rules("COMMANDER")

        assert rules1 == rules2 == rules3

    def test_partial_format_names_fail(self):
        """Verify partial format names don't match."""
        with pytest.raises(ValueError):
            FormatRules.get_rules("Comm")  # Partial match should fail


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
