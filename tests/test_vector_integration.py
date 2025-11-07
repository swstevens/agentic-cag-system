#!/usr/bin/env python3
"""
Simple test of vector search integration without full deck builder.

Tests the core VectorCardSelector functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.vector_store_service import VectorStoreService
from mtg_cag_system.services.vector_card_selector import VectorCardSelector


def main():
    print("=" * 80)
    print("Vector Search Integration Test")
    print("=" * 80)
    print()

    # Initialize services
    print("📀 Loading database...")
    db = DatabaseService(db_path="./data/cards_atomic.db")
    db.connect()

    print("🔮 Loading vector embeddings...")
    vector_store = VectorStoreService(persist_directory="./data/chroma")

    if not vector_store.is_initialized():
        print("❌ Vector embeddings not found. Run 'python scripts/build_embeddings.py' first.")
        db.disconnect()
        return

    # Create vector selector
    selector = VectorCardSelector(vector_store)

    # Get some initial Green aggro cards
    print("\n🟢 Fetching Green aggro creatures...")
    initial_deck = db.search_cards(
        colors=["G"],
        format_legality={"standard": "legal"},
        limit=8
    )

    print(f"Initial deck ({len(initial_deck)} cards):")
    for card in initial_deck[:5]:
        print(f"  - {card.name} ({card.mana_cost}): {card.oracle_text[:60]}...")

    # Get candidate cards
    print("\n🔍 Fetching candidates...")
    candidates = db.search_cards(
        colors=["G"],
        format_legality={"standard": "legal"},
        limit=30,
        offset=len(initial_deck)
    )

    print(f"Found {len(candidates)} candidates")

    # Test synergy-based selection
    print("\n⚙️ Testing synergy-based card selection...")
    archetype_keywords = ['haste', 'attack', 'damage', 'burn', 'fast', 'aggressive']

    selected = selector.select_synergistic_cards(
        current_deck=initial_deck,
        available_cards=candidates,
        archetype='aggro',
        archetype_keywords=archetype_keywords,
        needed=5,
        similarity_weight=0.4,
        archetype_weight=0.6
    )

    print(f"\n✅ Selected {len(selected)} synergistic cards:")
    for i, card in enumerate(selected, 1):
        print(f"  {i}. {card.name} ({card.mana_cost})")
        if card.oracle_text:
            print(f"     {card.oracle_text[:70]}...")

    # Test role finding
    print("\n🎯 Finding missing roles for aggro...")
    missing_roles = selector.find_missing_roles(
        current_deck=initial_deck,
        archetype='aggro',
        format_name='standard'
    )

    if missing_roles:
        for role_name, cards in list(missing_roles.items())[:3]:
            print(f"\n  {role_name.upper()}:")
            for card in cards[:3]:
                similarity = 1.0 - card.get('distance', 0) / 2.0
                print(f"    - {card['name']} (similarity: {similarity:.2%})")
    else:
        print("  No missing roles detected")

    db.disconnect()
    print("\n✅ Integration test completed!")


if __name__ == "__main__":
    main()
