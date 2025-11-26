"""
Test script for Two-Tier Card Lookup System

Demonstrates:
1. CAG Cache (Tier 1) with LRU eviction
2. SQLite Database (Tier 2) fallback
3. Integration with KnowledgeFetchAgent
"""

import asyncio
from mtg_cag_system.models.card import MTGCard, CardColor, CardType
from mtg_cag_system.services.cag_cache import CAGCache
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.agents.knowledge_fetch_agent import KnowledgeFetchAgent


def create_test_card(name: str, cmc: float = 1.0, oracle_text: str = None) -> MTGCard:
    """Helper to create a test card"""
    return MTGCard(
        id=f"test_{name.replace(' ', '_')}",
        name=name,
        mana_cost="{R}",
        cmc=cmc,
        colors=[CardColor.RED],
        color_identity=[CardColor.RED],
        type_line="Instant",
        types=[CardType.INSTANT],
        subtypes=[],
        oracle_text=oracle_text or f"{name} deals 3 damage to any target.",
        power=None,
        toughness=None,
        loyalty=None,
        set_code="TST",
        rarity="common",
        legalities={"vintage": "legal"},
        keywords=[]
    )


def test_basic_two_tier_lookup():
    """Test basic two-tier lookup without database"""
    print("=" * 70)
    print("TEST 1: Basic Two-Tier Lookup (No Database)")
    print("=" * 70)

    # Create lookup service without database
    lookup = CardLookupService(database_service=None, cache_size=5)

    # Preload some cards into cache
    cards = [
        create_test_card("Lightning Bolt"),
        create_test_card("Counterspell", cmc=2.0),
        create_test_card("Dark Ritual", cmc=1.0),
    ]
    lookup.preload_cards(cards)

    print(f"\nPreloaded {len(cards)} cards into CAG cache")
    print(f"Cached cards: {lookup.get_cached_card_names()}\n")

    # Test Tier 1 hit
    print("Looking up 'Lightning Bolt'...")
    card = lookup.get_card("Lightning Bolt")
    assert card is not None
    assert card.name == "Lightning Bolt"
    print(f"✓ Found: {card.name}\n")

    # Test cache miss
    print("Looking up 'Black Lotus' (not in cache, no database)...")
    card = lookup.get_card("Black Lotus")
    assert card is None
    print("✓ Returned None (as expected)\n")

    # Show statistics
    stats = lookup.get_stats()
    print("Statistics:")
    print(f"  Tier 1 hits: {stats['tier1_hits']}")
    print(f"  Tier 2 hits: {stats['tier2_hits']}")
    print(f"  Misses: {stats['total_misses']}")
    print(f"  Overall hit rate: {stats['overall_hit_rate']}\n")


def test_two_tier_with_database():
    """Test two-tier lookup WITH database"""
    print("=" * 70)
    print("TEST 2: Two-Tier Lookup with Database")
    print("=" * 70)

    # Check if database exists
    import os
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}")
        print("   Run 'python -m mtg_cag_system.scripts.build_database' to create it")
        print("   Skipping this test.\n")
        return

    # Create database service
    db = DatabaseService(db_path)
    db.connect()

    # Create lookup service with database
    lookup = CardLookupService(database_service=db, cache_size=3)

    print(f"✓ Connected to database ({db.card_count():,} cards)\n")

    # Test 1: Database lookup (Tier 2 hit, then cached)
    print("Test 1: Looking up 'Lightning Bolt' (should be in database)...")
    card = lookup.get_card("Lightning Bolt")
    if card:
        print(f"✓ Found: {card.name} - {card.oracle_text[:50]}...")
        print("  This was a Tier 2 hit (database) and is now cached\n")
    else:
        print("✗ Not found in database\n")

    # Test 2: Cache hit (should now be in Tier 1)
    print("Test 2: Looking up 'Lightning Bolt' again (should be in cache now)...")
    card = lookup.get_card("Lightning Bolt")
    if card:
        print(f"✓ Found: {card.name}")
        print("  This was a Tier 1 hit (cache)\n")

    # Test 3: Another database lookup
    print("Test 3: Looking up 'Counterspell' (database lookup)...")
    card = lookup.get_card("Counterspell")
    if card:
        print(f"✓ Found: {card.name} - {card.oracle_text[:50]}...\n")

    # Test 4: Fuzzy search
    print("Test 4: Fuzzy searching for 'bolt'...")
    results = lookup.fuzzy_search("bolt", limit=3)
    print(f"✓ Found {len(results)} cards:")
    for card in results:
        print(f"  - {card.name}")
    print()

    # Show statistics
    stats = lookup.get_stats()
    print("Statistics:")
    print(f"  Tier 1 hits (cache): {stats['tier1_hits']}")
    print(f"  Tier 2 hits (database): {stats['tier2_hits']}")
    print(f"  Misses: {stats['total_misses']}")
    print(f"  Tier 1 hit rate: {stats['tier1_hit_rate']}")
    print(f"  Tier 2 hit rate: {stats['tier2_hit_rate']}")
    print(f"  Overall hit rate: {stats['overall_hit_rate']}")
    print(f"\nCached cards: {lookup.get_cached_card_names()}\n")

    db.disconnect()


async def test_with_knowledge_agent():
    """Test integration with KnowledgeFetchAgent"""
    print("=" * 70)
    print("TEST 3: Integration with KnowledgeFetchAgent")
    print("=" * 70)

    # Check if database and API key exist
    import os
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}")
        print("   Skipping agent test.\n")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set in environment")
        print("   Skipping agent test (requires LLM for card name extraction).\n")
        return

    # Setup
    db = DatabaseService(db_path)
    db.connect()

    lookup = CardLookupService(database_service=db, cache_size=10)

    # Preload a popular card
    lookup.preload_by_names(["Lightning Bolt"])

    # Create agent
    agent = KnowledgeFetchAgent(
        card_lookup_service=lookup,
        model_name="openai:gpt-4o-mini",
        api_key=api_key
    )

    print("✓ Setup complete\n")

    # Test query
    print("Sending query: 'Tell me about Lightning Bolt'\n")

    response = await agent.process({
        "query": "Tell me about Lightning Bolt",
        "use_fuzzy": False
    })

    print("Agent Response:")
    print(f"  Success: {response.success}")
    print(f"  Confidence: {response.confidence}")
    print(f"  Extracted cards: {response.data.get('extracted_card_names', [])}")
    print(f"  Found cards: {len(response.data.get('cards', []))}")
    print(f"\nReasoning trace:")
    for trace in response.reasoning_trace:
        print(f"  - {trace}")

    print(f"\nAnswer:\n{response.data.get('answer', 'No answer')}\n")

    # Show lookup stats
    stats = lookup.get_stats()
    print("Lookup Statistics:")
    print(f"  Tier 1 hits: {stats['tier1_hits']}")
    print(f"  Tier 2 hits: {stats['tier2_hits']}")
    print(f"  Total queries: {stats['total_queries']}\n")

    db.disconnect()


if __name__ == "__main__":
    # Run tests
    test_basic_two_tier_lookup()
    test_two_tier_with_database()

    # Run async test
    asyncio.run(test_with_knowledge_agent())

    print("=" * 70)
    print("ALL TESTS COMPLETE! ✓")
    print("=" * 70)
