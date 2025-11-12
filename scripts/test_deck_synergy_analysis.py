#!/usr/bin/env python3
"""
Test script for deck synergy analysis across the entire deck

This script demonstrates:
1. Creating an example deck
2. Analyzing synergy patterns in the deck
3. Finding cards that best complement the deck
4. Ranking cards by how well they synergize with the deck overall
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Set

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mtg_cag_system.services.pattern_synergy_service import PatternSynergyService


class DeckSynergyAnalyzer:
    """Analyzes synergies across an entire deck"""

    def __init__(self, pattern_synergy: PatternSynergyService):
        self.pattern_synergy = pattern_synergy

    def get_deck_patterns(self, deck: List[str]) -> Dict[str, Set[str]]:
        """
        Extract all synergy patterns from a deck

        Args:
            deck: List of card names

        Returns:
            Dict mapping pattern names to set of card names with that pattern
        """
        patterns = {}

        for card_name in deck:
            # Load pattern info from synergy patterns
            pattern_info = self.pattern_synergy.get_pattern_info(card_name)
            if not pattern_info.get('found'):
                continue

            card_patterns = pattern_info.get('patterns', [])
            for pattern in card_patterns:
                if pattern not in patterns:
                    patterns[pattern] = set()
                patterns[pattern].add(card_name)

        return patterns

    def find_complementary_cards(self, deck: List[str], max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Find cards from the pool that best complement the entire deck

        Analyzes all patterns in the deck and finds cards that have complementary patterns.
        Returns cards ranked by how well they synergize with the deck overall.
        """
        # Get all patterns in the current deck
        deck_patterns = self.get_deck_patterns(deck)

        print(f"\n{'=' * 80}")
        print("DECK PATTERN ANALYSIS")
        print(f"{'=' * 80}")
        print(f"Analyzing {len(deck)} cards in deck")
        print(f"Patterns found in deck ({len(deck_patterns)} types):")
        for pattern, cards in sorted(deck_patterns.items()):
            print(f"  • {pattern}: {len(cards)} cards")
            # Show up to 3 example cards
            examples = list(cards)[:3]
            print(f"    Examples: {', '.join(examples)}")

        # Find complementary patterns
        complementary_patterns = set()
        for pattern in deck_patterns.keys():
            complements = self.pattern_synergy.PATTERN_COMPLEMENTS.get(pattern, [])
            complementary_patterns.update(complements)

        print(f"\nComplementary patterns to search for ({len(complementary_patterns)}):")
        for pattern in sorted(complementary_patterns):
            print(f"  • {pattern}")

        # Find all cards in the pool that have complementary patterns
        synergistic_cards = {}

        # Load all synergy patterns
        synergy_patterns = self.pattern_synergy.synergy_patterns
        deck_card_names = set(deck)

        for card_name, card_data in synergy_patterns.items():
            # Skip cards already in deck
            if card_name in deck_card_names:
                continue

            card_patterns = set(card_data.get('patterns', []))

            # Calculate how many complementary patterns this card has
            complementary_count = len(card_patterns & complementary_patterns)

            if complementary_count > 0:
                # Calculate synergy score based on deck coverage
                deck_coverage = 0.0
                for deck_pattern in deck_patterns.keys():
                    complements = self.pattern_synergy.PATTERN_COMPLEMENTS.get(deck_pattern, [])
                    for card_pattern in card_patterns:
                        if card_pattern in complements:
                            pair_score = self.pattern_synergy.SYNERGY_SCORES.get(
                                (deck_pattern, card_pattern), 0.5
                            )
                            deck_coverage = max(deck_coverage, pair_score)

                if deck_coverage > 0:
                    synergistic_cards[card_name] = {
                        'synergy_score': deck_coverage,
                        'complementary_count': complementary_count,
                        'patterns': list(card_patterns),
                        'synergy_text': card_data.get('synergy_text', '')
                    }

        # Sort by synergy score and return top results
        sorted_cards = sorted(
            synergistic_cards.items(),
            key=lambda x: x[1]['synergy_score'],
            reverse=True
        )[:max_results]

        results = []
        for card_name, synergy_data in sorted_cards:
            results.append({
                'name': card_name,
                'synergy_score': synergy_data['synergy_score'],
                'complementary_count': synergy_data['complementary_count'],
                'patterns': synergy_data['patterns'],
                'synergy_text': synergy_data['synergy_text']
            })

        return results

    def print_synergy_recommendations(self, recommendations: List[Dict[str, Any]]):
        """Pretty print synergy recommendations"""
        print(f"\n{'=' * 80}")
        print("TOP SYNERGISTIC CARDS FOR DECK")
        print(f"{'=' * 80}")

        for i, card in enumerate(recommendations, 1):
            print(f"\n{i}. {card['name']}")
            print(f"   Synergy Score: {card['synergy_score']:.2%}")
            print(f"   Complements: {card['complementary_count']} deck patterns")
            print(f"   Patterns: {', '.join(card['patterns'])}")
            print(f"   Synergy Text: {card['synergy_text']}")


def main():
    """Run deck synergy analysis test"""

    print("\n" + "=" * 80)
    print("DECK SYNERGY ANALYSIS TEST")
    print("=" * 80)

    # Load synergy patterns
    patterns_path = "./data/synergy_patterns.json"
    if not os.path.exists(patterns_path):
        print(f"❌ Synergy patterns not found at {patterns_path}")
        print("   Run: python scripts/build_synergy_embeddings.py")
        return

    pattern_synergy = PatternSynergyService(synergy_patterns_path=patterns_path)

    # Create example decks to analyze
    example_decks = {
        "Soul Warden Life Gain": [
            "Soul Warden",
            "Zulaport Cutthroat",
            "Viscera Seer",
            "Teysa Karlov",
            "Zulaport Heron",
            "Cartel Aristocrat",
            "Flicker",
            "Ephemerate",
            "Mulldrifter",
            "Solemn Simulacrum",
            "Soulherder",
            "Carapace",
            "Kaya's Guile",
            "Wraith of Echoes",
        ],
        "Gruul Aggro": [
            "Llanowar Elves",
            "Kessig Prowler",
            "Atla Palani, Nest Tender",
            "Mayhem Devil",
            "Goblin Oriflamme",
            "Bushwhack",
            "Crater Explosion",
            "Embercleave",
            "Bonecrusher Giant",
            "Arson",
            "Escape Velocity",
            "Stomping Ground",
            "Tourach, Dread Cantor",
        ],
        "Dimir Control": [
            "Murktide",
            "Snapcaster Mage",
            "Solitude",
            "Brazen Careerist",
            "Subtlety",
            "Counterspell",
            "Unholy Heat",
            "Saga of the Swamp Witch",
            "Murktide",
            "Tarfire",
            "Consider",
            "Murktide",
            "Mishra's Bauble",
        ],
    }

    analyzer = DeckSynergyAnalyzer(pattern_synergy)

    for deck_name, deck_cards in example_decks.items():
        print(f"\n\n{'#' * 80}")
        print(f"ANALYZING: {deck_name}")
        print(f"{'#' * 80}")

        # Remove any duplicate cards for analysis
        unique_cards = list(dict.fromkeys(deck_cards))

        # Analyze synergies
        recommendations = analyzer.find_complementary_cards(unique_cards, max_results=15)
        analyzer.print_synergy_recommendations(recommendations)

    print(f"\n{'=' * 80}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
