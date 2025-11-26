#!/usr/bin/env python3
"""
Test vector-enhanced deck builder with synergy detection.

This script tests the deck builder with vector similarity search enabled
to find synergistic cards based on the current deck composition.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.vector_store_service import VectorStoreService
from mtg_cag_system.services.deck_builder_service_v2 import DeckBuilderServiceV2
from mtg_cag_system.repositories.card_repository import CardRepository
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer
from mtg_cag_system.caching.lru_cache import LRUCache


async def main():
    print("=" * 80)
    print("Vector-Enhanced Deck Builder Test")
    print("=" * 80)
    print()

    # Initialize database and vector store
    print("📀 Loading database...")
    db = DatabaseService(db_path="./data/cards_atomic.db")
    db.connect()

    print("🔮 Loading vector embeddings...")
    vector_store = VectorStoreService(persist_directory="./data/chroma")

    if not vector_store.is_initialized():
        print("❌ Vector embeddings not found. Run 'python scripts/build_embeddings.py' first.")
        db.disconnect()
        return

    # Create repository and analyzer
    print("🏗️  Setting up deck builder...")
    cache = LRUCache(max_size=2000)
    repository = CardRepository(cache, db)
    analyzer = DeckAnalyzer()

    # Create deck builder WITH vector store
    deck_builder = DeckBuilderServiceV2(
        repository=repository,
        analyzer=analyzer,
        vector_store=vector_store,  # Enable vector-enhanced selection
        max_iterations=15  # Increased iterations for better completion
    )

    # Build a deck
    print()
    print("Building Green Aggro deck for Standard format...")
    print()

    result = await deck_builder.build_deck(
        colors=["Green"],
        archetype="aggro",
        deck_format="Standard"
    )

    # Display results
    print()
    print("=" * 80)
    print("DECK BUILDER RESULTS")
    print("=" * 80)
    print(f"Deck size: {result['deck_size']}/{result['target_size']}")
    print(f"Valid: {result['is_valid']}")
    print()

    if result['deck']:
        print(f"Cards in deck:")
        for i, card in enumerate(result['deck'][:10], 1):
            print(f"  {i}. {card.name} ({card.mana_cost or 'N/A'}) - {card.type_line}")
        if len(result['deck']) > 10:
            print(f"  ... and {len(result['deck']) - 10} more cards")

    print()
    if result['analysis']:
        print("Deck Analysis:")
        print(f"  Archetype match: {result['analysis'].archetype_match:.1%}")
        print(f"  Mana curve: {result['analysis'].mana_curve_score:.1%}")
        print(f"  Color balance: {result['analysis'].color_balance_score:.1%}")

    print()
    if result['is_valid']:
        print("✅ DECK COMPLETE!")
    else:
        print(f"⚠️  Deck incomplete: {result['deck_size']}/{result['target_size']}")

    db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
