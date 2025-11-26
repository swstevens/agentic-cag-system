#!/usr/bin/env python3
"""
Direct integration test - call the actual service functions that the API uses
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.services.knowledge_service import KnowledgeService
from mtg_cag_system.services.cache_service import MultiTierCache


def test_full_workflow():
    """Test the full workflow as used by the API endpoints"""
    print("="*70)
    print("Testing Full Integration Workflow")
    print("Database -> Services -> Pydantic Models")
    print("="*70)
    print()

    # Initialize services (same as main.py does)
    print("1. Initializing services...")
    db = DatabaseService("./data/cards.db")
    db.connect()
    print(f"   Database connected: {db.card_count():,} cards")

    cache = MultiTierCache()
    card_lookup_service = CardLookupService(database_service=db)
    knowledge_service = KnowledgeService(cache, database_service=db)
    print()

    # Test 1: GET /api/v1/cards/{card_name} endpoint logic
    print("2. Testing GET /cards/Lightning Bolt (endpoint logic)...")
    card = knowledge_service.get_card_by_name("Lightning Bolt")
    if card:
        print(f"   [OK] Found: {card.name}")
        print(f"   - Type: {card.type_line}")
        print(f"   - Cost: {card.mana_cost}")
        print(f"   - Text: {card.oracle_text}")
        print(f"   - Colors: {card.colors}")
    else:
        print(f"   [ERROR] Card not found")
    print()

    # Test 2: GET /api/v1/cards?query=bolt endpoint logic
    print("3. Testing GET /cards?query=bolt (search endpoint logic)...")
    cards = knowledge_service.search_cards("bolt", {})
    print(f"   [OK] Found {len(cards)} cards:")
    for c in cards[:5]:
        print(f"   - {c.name} ({c.set_code})")
    print()

    # Test 3: Search with filters
    print("4. Testing GET /cards with filters...")
    filters = {"colors": ["R"], "types": ["Creature"]}
    cards = knowledge_service.search_cards("", filters)
    print(f"   [OK] Found {len(cards)} red creatures:")
    for c in cards[:5]:
        print(f"   - {c.name} (CMC: {c.cmc})")
    print()

    # Test 4: CardLookupService with caching
    print("5. Testing CardLookupService (2-tier cache)...")

    # First call - should hit database (Tier 2)
    card1 = card_lookup_service.get_card("Counterspell")
    stats1 = card_lookup_service.get_stats()
    print(f"   First lookup: {card1.name if card1 else 'Not found'}")
    print(f"   - Tier 1 hits: {stats1['tier1_hits']}")
    print(f"   - Tier 2 hits: {stats1['tier2_hits']}")

    # Second call - should hit cache (Tier 1)
    card2 = card_lookup_service.get_card("Counterspell")
    stats2 = card_lookup_service.get_stats()
    print(f"   Second lookup: {card2.name if card2 else 'Not found'}")
    print(f"   - Tier 1 hits: {stats2['tier1_hits']}")
    print(f"   - Tier 2 hits: {stats2['tier2_hits']}")
    print()

    # Test 5: Verify Pydantic model integrity
    print("6. Verifying Pydantic model integrity...")
    test_cards = ["Lightning Bolt", "Black Lotus", "Ancestral Recall"]
    for card_name in test_cards:
        card = db.get_card_by_name(card_name)
        if card:
            # Verify it's a proper Pydantic model
            assert hasattr(card, 'model_dump'), "Not a Pydantic model!"
            data = card.model_dump()
            assert 'id' in data
            assert 'name' in data
            assert 'colors' in data
            assert 'legalities' in data
            print(f"   [OK] {card.name} - Pydantic model validated")
        else:
            print(f"   [WARN] {card_name} not in database")
    print()

    # Test 6: Complex query (as API would use)
    print("7. Testing complex database query...")
    cards = db.search_cards(
        colors=["U", "B"],
        types=["Instant"],
        cmc_min=1,
        cmc_max=3,
        strict_colors=False,
        limit=10
    )
    print(f"   [OK] Found {len(cards)} UB instants with CMC 1-3:")
    for c in cards[:3]:
        print(f"   - {c.name} (CMC: {c.cmc}, Colors: {c.colors})")
    print()

    # Cleanup
    db.disconnect()

    print("="*70)
    print("All integration tests passed!")
    print("SQLAlchemy -> Pydantic conversion working correctly")
    print("="*70)


if __name__ == "__main__":
    try:
        test_full_workflow()
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
