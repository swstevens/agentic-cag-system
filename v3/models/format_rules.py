"""
Magic: The Gathering format rules and constants.

Centralized configuration for all format-specific rules including deck size,
card copy limits, and format-specific constraints. This is the single source
of truth for format requirements across the application.
"""

from typing import Dict, Literal
from enum import Enum


class MTGFormat(str, Enum):
    """Supported Magic: The Gathering formats."""
    STANDARD = "Standard"
    MODERN = "Modern"
    PIONEER = "Pioneer"
    LEGACY = "Legacy"
    VINTAGE = "Vintage"
    COMMANDER = "Commander"
    BRAWL = "Brawl"


class FormatRules:
    """
    Configuration for Magic: The Gathering format rules.

    This is the single source of truth for all format-specific constraints.
    Update these values if MTG rules change.
    """

    # Format configuration dictionary
    # Each format defines: deck_size_min, deck_size_max, copy_limit, singleton_rule
    FORMATS: Dict[str, Dict[str, int | bool]] = {
        # 60-card formats
        "Standard": {
            "deck_size_min": 60,
            "deck_size_max": 60,
            "copy_limit": 4,  # Max 4 copies of any non-land card
            "singleton_rule": False,  # Can have multiple copies
            "legendary_max": 3,  # Legendaries can have up to 3 for redundancy
        },
        "Modern": {
            "deck_size_min": 60,
            "deck_size_max": 60,
            "copy_limit": 4,
            "singleton_rule": False,
            "legendary_max": 3,
        },
        "Pioneer": {
            "deck_size_min": 60,
            "deck_size_max": 60,
            "copy_limit": 4,
            "singleton_rule": False,
            "legendary_max": 3,
        },
        "Legacy": {
            "deck_size_min": 60,
            "deck_size_max": 60,
            "copy_limit": 4,
            "singleton_rule": False,
            "legendary_max": 3,
        },
        "Vintage": {
            "deck_size_min": 60,
            "deck_size_max": 60,
            "copy_limit": 4,
            "singleton_rule": False,
            "legendary_max": 3,
        },
        # Standard Brawl (60-card format with Commander, not singleton)
        "Brawl": {
            "deck_size_min": 60,
            "deck_size_max": 60,
            "copy_limit": 4,  # Standard copy limit (changed from historic singleton)
            "singleton_rule": False,  # Modern Brawl is NOT singleton
            "legendary_max": 1,  # Commander must be legendary creature or Planeswalker
        },
        # 100-card singleton format
        "Commander": {
            "deck_size_min": 100,
            "deck_size_max": 100,
            "copy_limit": 1,  # Singleton rule: exactly 1 copy per card (except basic lands)
            "singleton_rule": True,  # Enforce singleton rule
            "legendary_max": 1,  # Can only have 1 copy due to singleton rule
        },
    }

    # Mana curve standards by format (ideal % of cards at each CMC bracket)
    MANA_CURVE_STANDARDS: Dict[str, Dict[str, float]] = {
        "Standard": {
            "0-1": 0.15,  # 15% of cards at CMC 0-1
            "2-3": 0.40,  # 40% at CMC 2-3
            "4-5": 0.25,  # 25% at CMC 4-5
            "6+": 0.10,   # 10% at CMC 6+
        },
        "Modern": {
            "0-1": 0.15,
            "2-3": 0.40,
            "4-5": 0.25,
            "6+": 0.10,
        },
        "Pioneer": {
            "0-1": 0.15,
            "2-3": 0.40,
            "4-5": 0.25,
            "6+": 0.10,
        },
        "Legacy": {
            "0-1": 0.15,
            "2-3": 0.40,
            "4-5": 0.25,
            "6+": 0.10,
        },
        "Vintage": {
            "0-1": 0.15,
            "2-3": 0.40,
            "4-5": 0.25,
            "6+": 0.10,
        },
        "Brawl": {
            "0-1": 0.15,  # Similar to Standard - 60-card format
            "2-3": 0.40,
            "4-5": 0.25,
            "6+": 0.10,   # 60-card format curve (not 100-card)
        },
        "Commander": {
            "0-1": 0.08,  # Lower early game density in Commander
            "2-3": 0.25,
            "4-5": 0.30,
            "6+": 0.27,   # Higher density of expensive spells
        },
    }

    # Land ratio standards by format (ideal % of lands)
    LAND_RATIO_STANDARDS: Dict[str, float] = {
        "Standard": 0.40,   # ~24 lands in 60-card deck
        "Modern": 0.40,
        "Pioneer": 0.40,
        "Legacy": 0.40,
        "Vintage": 0.40,
        "Brawl": 0.40,     # ~24 lands in 60-card deck (like Standard)
        "Commander": 0.37,  # ~37 lands in 100-card deck
    }

    # Archetype guidelines
    ARCHETYPE_LAND_COUNTS: Dict[str, Dict[str, int]] = {
        "Standard": {
            "Aggro": 22,
            "Midrange": 24,
            "Control": 26,
            "Combo": 23,
        },
        "Modern": {
            "Aggro": 22,
            "Midrange": 24,
            "Control": 26,
            "Combo": 23,
        },
        "Pioneer": {
            "Aggro": 22,
            "Midrange": 24,
            "Control": 26,
            "Combo": 23,
        },
        "Legacy": {
            "Aggro": 22,
            "Midrange": 24,
            "Control": 26,
            "Combo": 23,
        },
        "Vintage": {
            "Aggro": 22,
            "Midrange": 24,
            "Control": 26,
            "Combo": 23,
        },
        "Brawl": {
            "Aggro": 22,     # 60-card format (like Standard)
            "Midrange": 24,
            "Control": 26,
            "Combo": 23,
        },
        "Commander": {
            "Aggro": 35,
            "Midrange": 36,
            "Control": 38,
            "Combo": 35,
        },
    }

    @classmethod
    def get_rules(cls, format_name: str) -> Dict[str, int | bool]:
        """
        Get format rules by format name.

        Args:
            format_name: Format name (e.g., "Standard", "Commander")

        Returns:
            Dictionary with format rules

        Raises:
            ValueError: If format is not supported
        """
        format_lower = format_name.lower()

        # Normalize format name
        for format_key in cls.FORMATS.keys():
            if format_key.lower() == format_lower:
                return cls.FORMATS[format_key]

        raise ValueError(f"Unknown format: {format_name}. Supported formats: {list(cls.FORMATS.keys())}")

    @classmethod
    def get_deck_size(cls, format_name: str) -> int:
        """Get target deck size for format."""
        rules = cls.get_rules(format_name)
        return rules["deck_size_max"]

    @classmethod
    def get_copy_limit(cls, format_name: str) -> int:
        """Get max copies allowed per card in format."""
        rules = cls.get_rules(format_name)
        return rules["copy_limit"]

    @classmethod
    def is_singleton(cls, format_name: str) -> bool:
        """Check if format uses singleton rule (1 copy per card)."""
        rules = cls.get_rules(format_name)
        return rules["singleton_rule"]

    @classmethod
    def get_legendary_max(cls, format_name: str) -> int:
        """Get max copies of legendary cards in format."""
        rules = cls.get_rules(format_name)
        return rules["legendary_max"]

    @classmethod
    def get_land_count(cls, format_name: str, archetype: str = "Midrange") -> int:
        """Get recommended land count for format and archetype."""
        format_lower = format_name.lower()
        archetype_lower = archetype.lower() if archetype else "midrange"

        # Find matching format
        for format_key, archetypes in cls.ARCHETYPE_LAND_COUNTS.items():
            if format_key.lower() == format_lower:
                # Find matching archetype
                for arch_key, count in archetypes.items():
                    if arch_key.lower() == archetype_lower:
                        return count
                # Default to midrange if archetype not found
                return archetypes.get("Midrange", 24)

        # Fallback for unknown format
        return 24

    @classmethod
    def get_land_ratio(cls, format_name: str) -> float:
        """Get ideal land ratio (0-1) for format."""
        format_lower = format_name.lower()

        for format_key, ratio in cls.LAND_RATIO_STANDARDS.items():
            if format_key.lower() == format_lower:
                return ratio

        # Default to 40%
        return 0.40

    @classmethod
    def get_mana_curve_standards(cls, format_name: str) -> Dict[str, float]:
        """Get mana curve distribution standards for format."""
        format_lower = format_name.lower()

        for format_key, standards in cls.MANA_CURVE_STANDARDS.items():
            if format_key.lower() == format_lower:
                return standards

        # Default to Standard curve
        return cls.MANA_CURVE_STANDARDS["Standard"]
