#!/usr/bin/env python3
"""
Test script for deck building with synergy analysis

This script:
1. Builds a complete deck with 25 iterations
2. Analyzes synergies across the entire deck
3. Finds the most synergistic cards from the card pool
4. Reports which cards complement the deck best
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Set

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.services.pattern_synergy_service import PatternSynergyService
from mtg_cag_system.agents.knowledge_fetch_agent import KnowledgeFetchAgent
from mtg_cag_system.agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from mtg_cag_system.services.deck_builder_service import DeckBuilderService


class DeckSynergyAnalyzer:
    """Analyzes synergies across an entire deck"""

    def __init__(self, pattern_synergy: PatternSynergyService, card_lookup: CardLookupService):
        self.pattern_synergy = pattern_synergy
        self.card_lookup = card_lookup

    def get_deck_patterns(self, deck: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        Extract all synergy patterns from a deck

        Returns:
            Dict mapping pattern names to set of card names with that pattern
        """
        patterns = {}

        for card_data in deck:
            card_name = card_data.get('name', '')
            if not card_name:
                continue

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

    def find_complementary_cards(self, deck: List[Dict[str, Any]], max_results: int = 20) -> List[Dict[str, Any]]:
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
        deck_card_names = {card.get('name') for card in deck}

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


async def run_deck_build_test(max_iterations: int = 25):
    """Run a complete deck build test with synergy analysis"""

    print("\n" + "=" * 80)
    print("DECK BUILD TEST WITH SYNERGY ANALYSIS")
    print("=" * 80)

    # Initialize services
    print("\nInitializing services...")

    database_path = "./data/cards_atomic.db"
    if not os.path.exists(database_path):
        print(f"❌ Database not found at {database_path}")
        return

    db = DatabaseService(database_path)
    card_lookup = CardLookupService(database_service=db)
    knowledge_agent = KnowledgeFetchAgent(card_lookup_service=card_lookup)
    symbolic_agent = SymbolicReasoningAgent()

    # Initialize deck builder with higher iteration count
    deck_builder = DeckBuilderService(
        knowledge_agent=knowledge_agent,
        symbolic_agent=symbolic_agent,
        card_lookup=card_lookup,
        max_iterations=max_iterations
    )

    # Load synergy patterns
    patterns_path = "./data/synergy_patterns.json"
    if not os.path.exists(patterns_path):
        print(f"⚠️  Synergy patterns not found at {patterns_path}")
        print("    Run: python scripts/build_synergy_embeddings.py")
        return

    pattern_synergy = PatternSynergyService(synergy_patterns_path=patterns_path)
    synergy_analyzer = DeckSynergyAnalyzer(pattern_synergy, card_lookup)

    print("✅ Services initialized")

    # Build a Gruul Aggro deck
    requirements = {
        "query": "Build a Gruul Aggro deck",
        "format": "Modern",
        "colors": ["R", "G"],
        "strategy": "aggro",
        "budget": None
    }

    print(f"\nBuilding deck with {max_iterations} iterations...")
    print(f"Requirements: {requirements}")

    # Build the deck
    deck_result = await deck_builder.build_deck(requirements)

    deck = deck_result.get('deck', [])
    deck_size = len(deck)

    print(f"\n{'=' * 80}")
    print(f"DECK BUILD COMPLETE")
    print(f"{'=' * 80}")
    print(f"Final deck size: {deck_size} cards")
    print(f"Unique cards: {len(set(c.get('name') for c in deck))}")

    if deck_size == 0:
        print("❌ Deck build failed - no cards added")
        return

    # Print deck list
    print(f"\n{'=' * 80}")
    print("FINAL DECK LIST")
    print(f"{'=' * 80}")

    card_counts = {}
    for card in deck:
        card_name = card.get('name', 'Unknown')
        card_counts[card_name] = card_counts.get(card_name, 0) + 1

    for card_name, count in sorted(card_counts.items()):
        print(f"{count}x {card_name}")

    # Analyze synergies
    print(f"\n{'=' * 80}")
    print("SYNERGY ANALYSIS")
    print(f"{'=' * 80}")

    recommendations = synergy_analyzer.find_complementary_cards(deck, max_results=20)
    synergy_analyzer.print_synergy_recommendations(recommendations)

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    max_iterations = 25
    if len(sys.argv) > 1:
        try:
            max_iterations = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [max_iterations]")
            sys.exit(1)

    asyncio.run(run_deck_build_test(max_iterations=max_iterations))
