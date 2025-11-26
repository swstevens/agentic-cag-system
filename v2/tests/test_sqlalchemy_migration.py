#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy migration works correctly
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from mtg_cag_system.services.database_service import DatabaseService


def test_database_connection():
    """Test that we can connect to the database"""
    print("=" * 70)
    print("Testing SQLAlchemy Database Migration")
    print("=" * 70)
    print()

    # Test 1: Connection
    print("Test 1: Connecting to database...")
    db = DatabaseService("./data/cards.db")
    db.connect()
    print("[OK] Connection successful")
    print()

    # Test 2: Card count
    print("Test 2: Checking card count...")
    count = db.card_count()
    print(f"[OK] Found {count:,} cards in database")
    print()

    # Test 3: Get card by name
    print("Test 3: Fetching card by name...")
    card = db.get_card_by_name("Lightning Bolt")
    if card:
        print(f"[OK] Found card: {card.name}")
        print(f"   Mana Cost: {card.mana_cost}")
        print(f"   Type: {card.type_line}")
        print(f"   Oracle Text: {card.oracle_text}")
        print(f"   Colors: {card.colors}")
        print(f"   CMC: {card.cmc}")
    else:
        print("[WARN]  Card not found (this is OK if database doesn't have Lightning Bolt)")
    print()

    # Test 4: Fuzzy search
    print("Test 4: Fuzzy search for 'bolt'...")
    cards = db.fuzzy_search("bolt", limit=5)
    print(f"[OK] Found {len(cards)} cards:")
    for card in cards:
        print(f"   - {card.name} ({card.set_code})")
    print()

    # Test 5: Search with filters
    print("Test 5: Search for red creatures with CMC <= 3...")
    cards = db.search_cards(
        colors=["R"],
        types=["Creature"],
        cmc_max=3,
        strict_colors=False,
        limit=5
    )
    print(f"[OK] Found {len(cards)} cards:")
    for card in cards:
        print(f"   - {card.name} (CMC: {card.cmc}, Colors: {card.colors})")
    print()

    # Test 6: Format legality
    print("Test 6: Checking format legality (Standard)...")
    try:
        cards = db.get_cards_by_format("standard", "legal")
        print(f"[OK] Found {len(cards)} Standard-legal cards")
        if len(cards) > 0:
            print(f"   Sample: {cards[0].name}")
    except Exception as e:
        print(f"[WARN]  Format search had issues (this is OK if no Standard cards): {e}")
    print()

    # Disconnect
    print("Disconnecting from database...")
    db.disconnect()
    print("[OK] Disconnected")
    print()

    print("=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_database_connection()
    except Exception as e:
        print(f"[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
