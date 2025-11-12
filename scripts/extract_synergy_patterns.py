#!/usr/bin/env python3
"""
Extract Synergy Patterns from MTG Card Oracle Text

This script analyzes card oracle text to identify synergy patterns that can be used
to enhance vector embeddings for synergy-focused card searches.

Synergy patterns capture mechanical interactions such as:
- Life gain triggers and payoffs
- ETB (Enter the Battlefield) effects and synergies
- Death/sacrifice triggers and payoffs
- Discard payoffs
- Spell triggers (storm, prowess, etc.)
- Token generation and payoffs
- Card draw and payoffs
- Mana acceleration and payoffs

The script is designed to run once and rarely, outputting a persistent synergy mapping
that can be used by the embedding builder.

Usage:
    python scripts/extract_synergy_patterns.py --db ./data/cards_atomic.db --output ./data/synergy_patterns.json
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SynergyPatternExtractor:
    """Extracts synergy patterns from MTG card oracle text"""

    # Define synergy patterns with regex patterns and descriptive names
    SYNERGY_PATTERNS = {
        # LIFE GAIN PATTERNS
        "gains_life": [
            r"you gain \d+ life",
            r"you gain life",
            r"gain \d+ life",
            r"whenever you gain life",
        ],
        "life_gain_payoff": [
            r"whenever you gain life.*(?:create|draw|put|get|add|search)",
            r"if you gained life",
            r"for each point of life gained",
        ],

        # ENTER THE BATTLEFIELD (ETB) PATTERNS
        "etb_trigger": [
            r"when.*enters the battlefield",
            r"whenever.*enters the battlefield",
            r"as.*enters the battlefield",
        ],
        "etb_payoff": [
            r"whenever a creature.*enters the battlefield.*(?:create|draw|put|bounce|destroy)",
            r"whenever a permanent.*enters the battlefield",
        ],

        # DEATH/LEAVE BATTLEFIELD PATTERNS
        "creature_dies": [
            r"whenever a creature.*dies",
            r"when.*dies",
            r"whenever a creature.*is put into a graveyard",
        ],
        "death_payoff": [
            r"whenever a creature.*dies.*(?:create|draw|damage|search|put)",
            r"when.*dies.*(?:create|draw|damage)",
        ],

        # SACRIFICE PATTERNS
        "sacrifice_outlet": [
            r"sacrifice.*(?:creature|permanent|creature or land)",
            r"you may sacrifice",
            r"sacrifice a creature",
        ],
        "sacrifice_payoff": [
            r"whenever.*sacrifice",
            r"whenever you sacrifice",
            r"if you sacrificed",
        ],

        # DISCARD PATTERNS
        "discard_trigger": [
            r"whenever you discard",
            r"when.*is discarded",
            r"whenever a card.*is discarded",
        ],
        "discard_payoff": [
            r"whenever you discard.*(?:create|draw|damage|create|put)",
            r"whenever a card.*is discarded.*(?:create|draw)",
        ],

        # SPELL-RELATED PATTERNS
        "spell_cast": [
            r"whenever you cast",
            r"whenever a spell",
            r"whenever a player casts a spell",
            r"each time you cast",
        ],
        "storm_combo": [
            r"storm",
            r"spell mastery",
            r"prowess",
            r"whenever another creature attacks",
        ],

        # TOKEN PATTERNS
        "token_creation": [
            r"create.*token",
            r"creates? .* token",
            r"put .* token onto the battlefield",
        ],
        "token_payoff": [
            r"whenever .* token.*(?:enter|die|attack)",
            r"whenever a token.*(?:created|entered|died)",
        ],

        # CARD DRAW PATTERNS
        "card_draw": [
            r"draw .* card",
            r"whenever .* card.*drawn",
            r"whenever you draw a card",
        ],
        "draw_payoff": [
            r"whenever you draw a card.*(?:create|damage|get|put|untap)",
        ],

        # MANA PATTERNS
        "mana_ramp": [
            r"add .* mana",
            r"ramp",
            r"search .* basic land",
            r"search your library for a land",
        ],
        "mana_sink": [
            r"pay.*to",
            r"for each .*mana paid",
        ],

        # COLORED MANA PATTERNS (color-specific synergies)
        "color_matters": [
            r"white.*permanent",
            r"blue.*permanent",
            r"black.*permanent",
            r"red.*permanent",
            r"green.*permanent",
            r"multicolor",
            r"devotion to",
        ],

        # CREATURE TYPE PATTERNS (tribal synergies)
        "lord_effects": [
            r"creature.*get.*\+.*\+",
            r"other.*get.*\+.*\+",
            r"all .* creatures",
            r"creatures .* have",
        ],

        # RECURSION PATTERNS
        "recursion": [
            r"return .* from your graveyard",
            r"cast .* from your graveyard",
            r"graveyard.*hand",
            r"flashback",
        ],

        # FLICKER/BOUNCE PATTERNS
        "flicker": [
            r"exile.*return",
            r"bounce.*permanent",
            r"untap.*creature",
        ],

        # CARD ADVANTAGE PATTERNS
        "card_advantage": [
            r"leaves the battlefield.*draw",
            r"dies.*draw",
            r"enters.*draws",
        ],
    }

    def __init__(self):
        """Initialize the extractor"""
        self.patterns_found = defaultdict(set)
        self.card_patterns = defaultdict(set)

    def extract_patterns(self, card_name: str, oracle_text: Optional[str]) -> Set[str]:
        """
        Extract synergy patterns from a card's oracle text

        Args:
            card_name: Name of the card
            oracle_text: Oracle text to analyze

        Returns:
            Set of pattern names found in the card
        """
        if not oracle_text:
            return set()

        # Normalize text: lowercase, remove extra whitespace
        normalized_text = oracle_text.lower()
        normalized_text = re.sub(r"\s+", " ", normalized_text)

        found_patterns = set()

        # Check each pattern against the oracle text
        for pattern_name, regex_list in self.SYNERGY_PATTERNS.items():
            for regex_pattern in regex_list:
                if re.search(regex_pattern, normalized_text):
                    found_patterns.add(pattern_name)
                    break  # Found this pattern, move to next

        # Track which cards have which patterns
        if found_patterns:
            self.card_patterns[card_name] = found_patterns
            for pattern in found_patterns:
                self.patterns_found[pattern].add(card_name)

        return found_patterns

    def build_synergy_graph(self) -> Dict[str, Dict[str, float]]:
        """
        Build a synergy graph based on pattern co-occurrence

        Cards that share synergy patterns are more likely to synergize.

        Returns:
            Dictionary mapping card names to synergy scores with other cards
        """
        synergy_graph = defaultdict(lambda: defaultdict(float))

        # Get all cards with patterns
        cards_with_patterns = list(self.card_patterns.keys())

        # For each pair of cards, calculate synergy based on pattern overlap
        for i, card1 in enumerate(cards_with_patterns):
            patterns1 = self.card_patterns[card1]

            for card2 in cards_with_patterns[i + 1 :]:
                patterns2 = self.card_patterns[card2]

                # Calculate pattern overlap
                overlap = patterns1 & patterns2
                union = patterns1 | patterns2

                if union:
                    # Jaccard similarity
                    similarity = len(overlap) / len(union)

                    # Boost score if patterns complement each other
                    # e.g., "life_gain" + "life_gain_payoff"
                    complementary_boost = self._calculate_complementary_boost(
                        patterns1, patterns2
                    )

                    final_score = similarity + complementary_boost

                    if final_score > 0:
                        synergy_graph[card1][card2] = final_score
                        synergy_graph[card2][card1] = final_score

        return dict(synergy_graph)

    def _calculate_complementary_boost(self, patterns1: Set[str], patterns2: Set[str]) -> float:
        """
        Calculate boost for complementary pattern pairs

        Args:
            patterns1: Patterns found in first card
            patterns2: Patterns found in second card

        Returns:
            Boost score (0.0-0.5)
        """
        complementary_pairs = {
            ("gains_life", "life_gain_payoff"): 0.3,
            ("etb_trigger", "etb_payoff"): 0.3,
            ("creature_dies", "death_payoff"): 0.3,
            ("sacrifice_outlet", "sacrifice_payoff"): 0.3,
            ("discard_trigger", "discard_payoff"): 0.3,
            ("spell_cast", "storm_combo"): 0.25,
            ("token_creation", "token_payoff"): 0.3,
            ("card_draw", "draw_payoff"): 0.3,
            ("mana_ramp", "mana_sink"): 0.2,
            ("recursion", "creature_dies"): 0.2,
            ("flicker", "etb_trigger"): 0.25,
        }

        boost = 0.0
        for (pattern1, pattern2), score in complementary_pairs.items():
            if (pattern1 in patterns1 and pattern2 in patterns2) or (
                pattern2 in patterns1 and pattern1 in patterns2
            ):
                boost += score

        return min(boost, 0.5)  # Cap at 0.5

    def get_synergy_text(self, patterns: Set[str]) -> str:
        """
        Convert extracted patterns into synergy-focused text for embeddings

        Args:
            patterns: Set of pattern names

        Returns:
            Text representation of synergy signals
        """
        if not patterns:
            return ""

        # Create descriptive text for each pattern
        pattern_descriptions = {
            "gains_life": "Gains life trigger",
            "life_gain_payoff": "Life gain payoff effect",
            "etb_trigger": "Enter the battlefield trigger",
            "etb_payoff": "ETB synergy effect",
            "creature_dies": "Creature death trigger",
            "death_payoff": "Death trigger payoff",
            "sacrifice_outlet": "Sacrifice outlet",
            "sacrifice_payoff": "Sacrifice payoff effect",
            "discard_trigger": "Discard trigger",
            "discard_payoff": "Discard payoff effect",
            "spell_cast": "Spell cast trigger",
            "storm_combo": "Storm or prowess combo",
            "token_creation": "Token creation effect",
            "token_payoff": "Token synergy effect",
            "card_draw": "Card draw effect",
            "draw_payoff": "Draw payoff effect",
            "mana_ramp": "Mana acceleration",
            "mana_sink": "Mana sink effect",
            "color_matters": "Color-based synergy",
            "lord_effects": "Lord or buff effects",
            "recursion": "Recursion effect",
            "flicker": "Flicker or bounce effect",
            "card_advantage": "Card advantage effect",
        }

        # Build synergy text
        synergy_signals = []
        for pattern in sorted(patterns):
            desc = pattern_descriptions.get(pattern, pattern)
            synergy_signals.append(desc)

        return " | ".join(synergy_signals)


def extract_patterns_from_database(db_path: str) -> Dict[str, Dict]:
    """
    Extract synergy patterns from all cards in the database

    Args:
        db_path: Path to the cards database

    Returns:
        Dictionary mapping card ID to extracted patterns and signals
    """
    import sys
    import os

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from mtg_cag_system.services.database_service import DatabaseService

    logger.info(f"Loading database from {db_path}...")
    db = DatabaseService(db_path)
    db.connect()

    card_count = db.card_count()
    logger.info(f"Found {card_count} cards in database")

    extractor = SynergyPatternExtractor()

    # Process all cards
    batch_size = 1000
    processed = 0

    logger.info("Extracting synergy patterns...")
    for offset in range(0, card_count, batch_size):
        cards = db.search_cards(query=None, limit=batch_size, offset=offset)

        if not cards:
            break

        for card in cards:
            patterns = extractor.extract_patterns(card.name, card.oracle_text)
            processed += 1

            if processed % 5000 == 0:
                logger.info(f"Processed {processed}/{card_count} cards")

    logger.info(f"✅ Extracted patterns from {processed} cards")

    # Build results dictionary
    results = {}
    for card_name, patterns in extractor.card_patterns.items():
        synergy_text = extractor.get_synergy_text(patterns)
        results[card_name] = {
            "patterns": list(patterns),
            "synergy_text": synergy_text,
            "pattern_count": len(patterns),
        }

    db.disconnect()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Extract synergy patterns from MTG card oracle text"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/cards_atomic.db",
        help="Path to the cards database",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/synergy_patterns.json",
        help="Path to output synergy patterns file",
    )

    args = parser.parse_args()

    db_path = args.db
    output_path = args.output

    # Check database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}")
        logger.error("Run: python scripts/load_atomic_cards.py")
        return

    # Extract patterns
    synergy_patterns = extract_patterns_from_database(db_path)

    # Create output directory if needed
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save results
    with open(output_path, "w") as f:
        json.dump(synergy_patterns, f, indent=2)

    logger.info(f"✅ Synergy patterns saved to {output_path}")
    logger.info(f"   Total cards with patterns: {len(synergy_patterns)}")

    # Print statistics
    pattern_stats = defaultdict(int)
    for card_data in synergy_patterns.values():
        for pattern in card_data["patterns"]:
            pattern_stats[pattern] += 1

    logger.info("\nPattern distribution:")
    for pattern, count in sorted(pattern_stats.items(), key=lambda x: -x[1]):
        logger.info(f"  {pattern}: {count} cards")


if __name__ == "__main__":
    main()
