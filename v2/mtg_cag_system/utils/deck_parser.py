"""
Deck Parser Utilities

Helper functions for parsing user input for deck building:
- Color identity parsing (WUBRG, Golgari, etc.)
- Format name fuzzy matching
- Archetype normalization
"""

from typing import List, Optional, Tuple


class DeckParser:
    """Parse and normalize deck building parameters"""

    # Color mappings
    COLOR_CODES = {
        'W': 'White',
        'U': 'Blue',
        'B': 'Black',
        'R': 'Red',
        'G': 'Green',
        'C': 'Colorless'
    }

    # Guild names (2-color combinations)
    GUILDS = {
        'azorius': ['W', 'U'],
        'dimir': ['U', 'B'],
        'rakdos': ['B', 'R'],
        'gruul': ['R', 'G'],
        'selesnya': ['G', 'W'],
        'orzhov': ['W', 'B'],
        'izzet': ['U', 'R'],
        'golgari': ['B', 'G'],
        'boros': ['R', 'W'],
        'simic': ['G', 'U']
    }

    # Shard names (3-color combinations - allied)
    SHARDS = {
        'bant': ['W', 'U', 'G'],
        'esper': ['W', 'U', 'B'],
        'grixis': ['U', 'B', 'R'],
        'jund': ['B', 'R', 'G'],
        'naya': ['R', 'G', 'W']
    }

    # Wedge names (3-color combinations - enemy)
    WEDGES = {
        'abzan': ['W', 'B', 'G'],
        'jeskai': ['U', 'R', 'W'],
        'sultai': ['B', 'G', 'U'],
        'mardu': ['R', 'W', 'B'],
        'temur': ['G', 'U', 'R']
    }

    # Format aliases
    FORMAT_ALIASES = {
        'standard': ['standard', 'std'],
        'modern': ['modern', 'mod'],
        'pioneer': ['pioneer', 'pio'],
        'legacy': ['legacy', 'leg'],
        'vintage': ['vintage', 'vin'],
        'commander': ['commander', 'edh', 'cmd'],
        'pauper': ['pauper', 'pau'],
        'historic': ['historic', 'hist'],
        'timeless': ['timeless'],
        'brawl': ['brawl'],
        'oathbreaker': ['oathbreaker', 'oath']
    }

    @classmethod
    def parse_colors(cls, color_input: str) -> List[str]:
        """
        Parse color input into list of color codes

        Supports:
        - Single letters: "R", "U", "B"
        - Combined: "WU", "WUBRG"
        - Guild names: "Azorius", "Golgari"
        - Shard names: "Jund", "Esper"
        - Wedge names: "Abzan", "Temur"

        Args:
            color_input: Color string (e.g., "WUBRG", "Golgari", "R")

        Returns:
            List of color codes (e.g., ["W", "U", "B", "R", "G"])
        """
        if not color_input:
            return []

        color_input = color_input.strip().lower()

        # Check guild names
        if color_input in cls.GUILDS:
            return cls.GUILDS[color_input]

        # Check shard names
        if color_input in cls.SHARDS:
            return cls.SHARDS[color_input]

        # Check wedge names
        if color_input in cls.WEDGES:
            return cls.WEDGES[color_input]

        # Parse individual color codes
        colors = []
        for char in color_input.upper():
            if char in cls.COLOR_CODES:
                if char not in colors:  # Avoid duplicates
                    colors.append(char)

        return colors

    @classmethod
    def get_color_description(cls, colors: List[str]) -> str:
        """
        Get human-readable description of colors

        Args:
            colors: List of color codes

        Returns:
            Description string (e.g., "Red/Green (Gruul)")
        """
        if not colors:
            return "Colorless"

        if len(colors) == 1:
            return cls.COLOR_CODES.get(colors[0], colors[0])

        # Check if it's a known combination
        color_set = set(colors)

        # Check guilds
        for name, guild_colors in cls.GUILDS.items():
            if color_set == set(guild_colors):
                return f"{'/'.join(cls.COLOR_CODES[c] for c in colors)} ({name.capitalize()})"

        # Check shards
        for name, shard_colors in cls.SHARDS.items():
            if color_set == set(shard_colors):
                return f"{'/'.join(cls.COLOR_CODES[c] for c in colors)} ({name.capitalize()})"

        # Check wedges
        for name, wedge_colors in cls.WEDGES.items():
            if color_set == set(wedge_colors):
                return f"{'/'.join(cls.COLOR_CODES[c] for c in colors)} ({name.capitalize()})"

        # 5-color
        if len(colors) == 5:
            return "Five-Color (WUBRG)"

        # Generic multi-color
        return "/".join(cls.COLOR_CODES[c] for c in colors)

    @classmethod
    def parse_format(cls, format_input: str) -> Tuple[str, float]:
        """
        Parse format name with fuzzy matching

        Args:
            format_input: Format string (e.g., "modern", "EDH", "std")

        Returns:
            Tuple of (canonical_format_name, confidence_score)
        """
        if not format_input:
            return ("Standard", 0.0)

        format_lower = format_input.strip().lower()

        # Check exact matches and aliases
        for canonical, aliases in cls.FORMAT_ALIASES.items():
            if format_lower in aliases:
                return (canonical.capitalize(), 1.0)

        # Fuzzy matching - check if input is substring of any format
        best_match = None
        best_score = 0.0

        for canonical, aliases in cls.FORMAT_ALIASES.items():
            for alias in aliases:
                if format_lower in alias or alias in format_lower:
                    score = len(format_lower) / max(len(alias), len(format_lower))
                    if score > best_score:
                        best_score = score
                        best_match = canonical.capitalize()

        if best_match:
            return (best_match, best_score)

        # No match found - return input as-is with low confidence
        return (format_input.capitalize(), 0.3)

    @classmethod
    def normalize_archetype(cls, archetype_input: str) -> str:
        """
        Normalize archetype name

        Args:
            archetype_input: Archetype string (e.g., "aggro", "control")

        Returns:
            Normalized archetype name
        """
        if not archetype_input:
            return "midrange"

        archetype_lower = archetype_input.strip().lower()

        # Known archetypes
        archetypes = {
            'aggro': ['aggro', 'aggressive', 'beatdown', 'weenie'],
            'control': ['control', 'draw-go', 'permission'],
            'midrange': ['midrange', 'mid', 'value'],
            'combo': ['combo', 'engine'],
            'tempo': ['tempo'],
            'ramp': ['ramp', 'big mana'],
            'tribal': ['tribal', 'typal']
        }

        for canonical, aliases in archetypes.items():
            if archetype_lower in aliases:
                return canonical

        # Default to input if no match
        return archetype_lower
