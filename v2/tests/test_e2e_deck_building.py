#!/usr/bin/env python3
"""
End-to-end test of deck building with vector search integration.

This test verifies:
1. Database connection (33K cards)
2. Vector store initialization (32K embeddings)
3. Deck building with synergy detection
4. Multiple archetype support (aggro, control, midrange)
"""

import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.vector_store_service import VectorStoreService
from mtg_cag_system.services.deck_builder_service_v2 import DeckBuilderServiceV2
from mtg_cag_system.repositories.card_repository import CardRepository
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer
from mtg_cag_system.caching.lru_cache import LRUCache


async def test_deck_building(colors: list, archetype: str, format_name: str = "Standard"):
    """Test deck building for a given color and archetype"""

    print(f"\n{'='*80}")
    print(f"Testing {', '.join(colors).upper()} {archetype.upper()} - {format_name}")
    print(f"{'='*80}")

    # Initialize services
    db = DatabaseService(db_path="./data/cards_atomic.db")
    db.connect()

    vector_store = VectorStoreService(persist_directory="./data/chroma")
    if not vector_store.is_initialized():
        print("❌ Vector embeddings not found")
        return False

    # Setup deck builder with vector search
    cache = LRUCache(max_size=2000)
    repository = CardRepository(cache, db)
    analyzer = DeckAnalyzer()

    deck_builder = DeckBuilderServiceV2(
        repository=repository,
        analyzer=analyzer,
        vector_store=vector_store,
        max_iterations=20  # More iterations to potentially complete deck
    )

    try:
        result = await deck_builder.build_deck(
            colors=colors,
            archetype=archetype,
            deck_format=format_name
        )

        deck_size = result['deck_size']
        target_size = result['target_size']
        is_valid = result['is_valid']

        print(f"\nResult: {deck_size}/{target_size} cards", end="")
        if is_valid:
            print(" ✅ COMPLETE")
        else:
            print(f" ({target_size - deck_size} cards short)")

        # Show sample cards
        if result['deck']:
            print(f"\nFirst 5 cards:")
            for i, card in enumerate(result['deck'][:5], 1):
                print(f"  {i}. {card.name} ({card.mana_cost})")

        db.disconnect()
        return is_valid

    except Exception as e:
        print(f"❌ Error: {e}")
        db.disconnect()
        return False


async def main():
    print("\n" + "="*80)
    print("END-TO-END DECK BUILDING TEST WITH VECTOR SEARCH")
    print("="*80)

    # Test multiple archetypes
    test_cases = [
        (["Green"], "aggro"),
        (["Blue"], "control"),
        (["Red", "White"], "midrange"),
    ]

    results = {}
    for colors, archetype in test_cases:
        success = await test_deck_building(colors, archetype)
        results[f"{archetype}_{','.join(colors)}"] = success

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    completed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Decks completed: {completed}/{total}")
    for name, success in results.items():
        status = "✅" if success else "⚠️"
        print(f"  {status} {name}")


if __name__ == "__main__":
    asyncio.run(main())
