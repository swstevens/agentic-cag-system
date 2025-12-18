"""
Test script for Commander deck building with format rules validation.

Tests the new format-aware deck building system, specifically:
1. Singleton rule enforcement (1 copy per card except basic lands)
2. 100-card deck size requirement
3. Legendary card handling (max 1 copy due to singleton rule)
4. Quality verification with Commander-specific standards
5. Format-aware card copy limits
"""

import asyncio
import sys
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from v3.models.deck import DeckBuildRequest, Deck, DeckCard
from v3.models.format_rules import FormatRules
from v3.database.database_service import DatabaseService
from v3.database.card_repository import CardRepository
from v3.services.agent_deck_builder_service import AgentDeckBuilderService
from v3.services.quality_verifier_service import QualityVerifierService


@pytest.mark.asyncio
async def test_commander_deck_building():
    """
    Test building a Commander deck and verify format rules are applied.
    """
    print("\n" + "="*70)
    print("COMMANDER DECK BUILDING TEST")
    print("="*70)

    # Initialize services
    print("\n[1] Initializing database and services...")
    db_service = DatabaseService()
    card_repo = CardRepository(db_service)
    deck_builder = AgentDeckBuilderService(card_repo)
    quality_verifier = QualityVerifierService()

    # Create Commander deck build request
    print("\n[2] Creating Commander deck build request...")
    request = DeckBuildRequest(
        format="Commander",
        colors=["R", "G"],
        archetype="Midrange",
        strategy="Build a red-green midrange Commander deck with creature synergies",
        quality_threshold=0.7,
        max_iterations=2,
        deck_size=100,  # Commander requirement
    )

    print(f"\n   Format: {request.format}")
    print(f"   Colors: {', '.join(request.colors)}")
    print(f"   Archetype: {request.archetype}")
    print(f"   Target Size: {request.deck_size}")

    # Verify format rules
    print("\n[3] Verifying format rules...")
    rules = FormatRules.get_rules("Commander")
    print(f"\n   Format Rules for Commander:")
    print(f"   - Deck Size: {rules['deck_size_min']}-{rules['deck_size_max']} (singleton)")
    print(f"   - Copy Limit: {rules['copy_limit']} (singleton rule)")
    print(f"   - Is Singleton: {rules['singleton_rule']}")
    print(f"   - Land Ratio: {FormatRules.get_land_ratio('Commander'):.0%}")
    print(f"   - Land Count (Midrange): {FormatRules.get_land_count('Commander', 'Midrange')}")

    # Build initial deck
    print("\n[4] Building initial Commander deck...")
    print("    (This may take a moment as the LLM builds the deck...)")
    try:
        deck = await deck_builder.build_initial_deck(request)
        print(f"\n    ✓ Deck built successfully!")
        print(f"    - Total cards: {deck.total_cards}")
        print(f"    - Unique cards: {len(deck.cards)}")
    except Exception as e:
        print(f"\n    ✗ Failed to build deck: {e}")
        return False

    # Analyze deck composition
    print("\n[5] Analyzing deck composition...")
    lands = deck.get_lands()
    nonlands = deck.get_nonlands()
    land_count = sum(dc.quantity for dc in lands)
    land_ratio = land_count / deck.total_cards if deck.total_cards > 0 else 0

    print(f"\n    Land Composition:")
    print(f"    - Total lands: {land_count} ({land_ratio:.1%})")
    print(f"    - Total spells: {sum(dc.quantity for dc in nonlands)}")
    print(f"    - Land cards in deck: {len(lands)}")

    # Check singleton rule compliance
    print("\n[6] Checking singleton rule compliance...")
    singleton_violations = []
    legendary_count = 0
    basic_lands = 0

    for deck_card in deck.cards:
        card = deck_card.card
        is_legendary = "Legendary" in card.type_line
        is_basic_land = "Land" in card.types and card.type_line.startswith("Basic")

        if is_legendary:
            legendary_count += 1

        if is_basic_land:
            basic_lands += 1
        elif deck_card.quantity > 1:
            singleton_violations.append(
                f"  - {card.name}: {deck_card.quantity} copies (should be 1)"
            )

    if singleton_violations:
        print(f"\n    ✗ Singleton rule violations found:")
        for violation in singleton_violations[:5]:  # Show first 5
            print(violation)
        if len(singleton_violations) > 5:
            print(f"    ... and {len(singleton_violations) - 5} more")
    else:
        print(f"    ✓ No singleton rule violations detected!")

    print(f"\n    Summary:")
    print(f"    - Legendary cards: {legendary_count}")
    print(f"    - Basic lands: {basic_lands}")
    print(f"    - Non-singleton cards: {len(nonlands)}")

    # Check deck size
    print("\n[7] Verifying deck size...")
    target_size = FormatRules.get_deck_size("Commander")
    if deck.total_cards == target_size:
        print(f"    ✓ Deck size is correct: {deck.total_cards} cards")
    else:
        print(f"    ✗ Deck size mismatch!")
        print(f"      Expected: {target_size}")
        print(f"      Got: {deck.total_cards}")
        return False

    # Run quality verification
    print("\n[8] Running quality verification...")
    try:
        metrics = await quality_verifier.verify_deck(deck, "Commander")

        print(f"\n    Quality Metrics:")
        print(f"    - Mana Curve Score: {metrics.mana_curve_score:.2f}")
        print(f"    - Land Ratio Score: {metrics.land_ratio_score:.2f}")
        print(f"    - Synergy Score: {metrics.synergy_score:.2f}")
        print(f"    - Consistency Score: {metrics.consistency_score:.2f}")
        print(f"    - Overall Score: {metrics.overall_score:.2f}")

        if metrics.issues:
            print(f"\n    Issues ({len(metrics.issues)}):")
            for issue in metrics.issues[:3]:
                print(f"    - {issue}")

        if metrics.suggestions:
            print(f"\n    Suggestions ({len(metrics.suggestions)}):")
            for suggestion in metrics.suggestions[:3]:
                print(f"    - {suggestion}")

    except Exception as e:
        print(f"    ✗ Quality verification failed: {e}")
        return False

    # Print detailed deck list
    print("\n[9] Deck List (first 30 cards):")
    print("\n    LANDS:")
    for dc in lands[:5]:
        print(f"    {dc.quantity}x {dc.card.name}")
    if len(lands) > 5:
        print(f"    ... and {len(lands) - 5} more land types")

    print("\n    SPELLS (first 25):")
    for i, dc in enumerate(nonlands[:25]):
        print(f"    {dc.quantity}x {dc.card.name} ({dc.card.type_line})")
    if len(nonlands) > 25:
        print(f"    ... and {len(nonlands) - 25} more spells")

    # Final summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    success = (
        deck.total_cards == target_size
        and len(singleton_violations) == 0
        and metrics.overall_score > 0
    )

    if success:
        print("\n✓ COMMANDER DECK TEST PASSED!")
        print(f"\n  Successfully built a {request.format} deck:")
        print(f"  - Size: {deck.total_cards} cards (100-card format)")
        print(f"  - Singleton rule: Enforced ✓")
        print(f"  - Quality score: {metrics.overall_score:.2f}")
        print(f"  - Land ratio: {land_ratio:.1%}")
    else:
        print("\n✗ COMMANDER DECK TEST FAILED")
        if deck.total_cards != target_size:
            print(f"  - Size mismatch: {deck.total_cards} != {target_size}")
        if singleton_violations:
            print(f"  - Singleton violations: {len(singleton_violations)}")
        if metrics.overall_score == 0:
            print(f"  - Quality verification failed")

    print("\n" + "="*70 + "\n")
    return success


@pytest.mark.asyncio
async def test_format_comparison():
    """
    Compare format rules across different formats.
    """
    print("\n" + "="*70)
    print("FORMAT RULES COMPARISON")
    print("="*70)

    formats = ["Standard", "Modern", "Commander", "Brawl"]

    print("\n{:<15} {:<15} {:<15} {:<15} {:<15}".format(
        "Format", "Size", "Copy Limit", "Singleton", "Land Ratio"
    ))
    print("-" * 75)

    for format_name in formats:
        rules = FormatRules.get_rules(format_name)
        size = rules["deck_size_max"]
        copy_limit = rules["copy_limit"]
        singleton = "Yes" if rules["singleton_rule"] else "No"
        land_ratio = FormatRules.get_land_ratio(format_name)

        print("{:<15} {:<15} {:<15} {:<15} {:<15}".format(
            format_name,
            f"{size} cards",
            f"{copy_limit} copies",
            singleton,
            f"{land_ratio:.0%}"
        ))

    print("\n" + "="*70 + "\n")


async def main():
    """Run all tests."""
    print("\n╔════════════════════════════════════════════════════════════════════╗")
    print("║         COMMANDER DECK BUILDING TEST SUITE v3                      ║")
    print("║     Testing format-aware deck building and validation              ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    # Show format comparison
    await test_format_comparison()

    # Test Commander deck building
    success = await test_commander_deck_building()

    if success:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
