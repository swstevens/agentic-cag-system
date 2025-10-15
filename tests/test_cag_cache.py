"""
Test script for CAG Cache with LRU eviction
"""

from mtg_cag_system.models.card import MTGCard, CardColor, CardType
from mtg_cag_system.services.cag_cache import CAGCache


def create_test_card(name: str, cmc: float = 1.0) -> MTGCard:
    """Helper to create a test card"""
    return MTGCard(
        id=f"test_{name}",
        name=name,
        mana_cost="{R}",
        cmc=cmc,
        colors=[CardColor.RED],
        color_identity=[CardColor.RED],
        type_line="Instant",
        types=[CardType.INSTANT],
        subtypes=[],
        oracle_text=f"Test card: {name}",
        power=None,
        toughness=None,
        loyalty=None,
        set_code="TST",
        rarity="common",
        legalities={},
        keywords=[]
    )


def test_basic_operations():
    """Test basic get/put operations"""
    print("=" * 60)
    print("TEST 1: Basic Operations")
    print("=" * 60)

    cache = CAGCache(max_size=5)

    # Add some cards
    bolt = create_test_card("Lightning Bolt")
    cache.put(bolt)

    counterspell = create_test_card("Counterspell")
    cache.put(counterspell)

    # Test retrieval
    retrieved = cache.get("Lightning Bolt")
    assert retrieved is not None
    assert retrieved.name == "Lightning Bolt"
    print("✓ Card retrieval works")

    # Test case-insensitive lookup
    retrieved = cache.get("lightning bolt")
    assert retrieved is not None
    print("✓ Case-insensitive lookup works")

    # Test miss
    missing = cache.get("Black Lotus")
    assert missing is None
    print("✓ Cache miss returns None")

    # Test contains
    assert cache.contains("Lightning Bolt")
    assert not cache.contains("Black Lotus")
    print("✓ Contains check works")

    print(f"\nStats: {cache.get_stats()}\n")


def test_lru_eviction():
    """Test LRU eviction policy"""
    print("=" * 60)
    print("TEST 2: LRU Eviction")
    print("=" * 60)

    cache = CAGCache(max_size=3)

    # Add 3 cards (filling the cache)
    cards = [
        create_test_card("Card A"),
        create_test_card("Card B"),
        create_test_card("Card C"),
    ]

    for card in cards:
        cache.put(card)

    print(f"Cache filled with 3 cards: {cache.get_lru_order()}")
    print(f"Stats: {cache.get_stats()}")

    # Access Card A and Card B (making Card C the LRU)
    cache.get("Card A")
    cache.get("Card B")

    print(f"\nAfter accessing A and B, LRU order: {cache.get_lru_order()}")
    print("(Card C should be first = least recently used)")

    # Add a 4th card - should evict Card C
    print("\nAdding Card D (should evict Card C)...")
    cache.put(create_test_card("Card D"))

    print(f"LRU order after eviction: {cache.get_lru_order()}")
    assert not cache.contains("Card C"), "Card C should have been evicted"
    assert cache.contains("Card A"), "Card A should still be in cache"
    assert cache.contains("Card B"), "Card B should still be in cache"
    assert cache.contains("Card D"), "Card D should be in cache"
    print("✓ LRU eviction works correctly")

    print(f"\nStats: {cache.get_stats()}\n")


def test_batch_operations():
    """Test batch loading"""
    print("=" * 60)
    print("TEST 3: Batch Operations")
    print("=" * 60)

    cache = CAGCache(max_size=10)

    cards = [
        create_test_card(f"Card {i}") for i in range(5)
    ]

    cache.put_batch(cards)
    assert len(cache.get_all_cards()) == 5
    print(f"✓ Batch put: loaded {len(cache.get_all_cards())} cards")

    print(f"Stats: {cache.get_stats()}\n")


def test_context_generation():
    """Test LLM context string generation"""
    print("=" * 60)
    print("TEST 4: Context String Generation")
    print("=" * 60)

    cache = CAGCache(max_size=10)

    # Add a few detailed cards
    bolt = MTGCard(
        id="test_bolt",
        name="Lightning Bolt",
        mana_cost="{R}",
        cmc=1.0,
        colors=[CardColor.RED],
        color_identity=[CardColor.RED],
        type_line="Instant",
        types=[CardType.INSTANT],
        subtypes=[],
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        power=None,
        toughness=None,
        loyalty=None,
        set_code="LEA",
        rarity="common",
        legalities={"vintage": "legal"},
        keywords=[]
    )

    grizzly = MTGCard(
        id="test_grizzly",
        name="Grizzly Bears",
        mana_cost="{1}{G}",
        cmc=2.0,
        colors=[CardColor.GREEN],
        color_identity=[CardColor.GREEN],
        type_line="Creature — Bear",
        types=[CardType.CREATURE],
        subtypes=["Bear"],
        oracle_text=None,
        power="2",
        toughness="2",
        loyalty=None,
        set_code="LEA",
        rarity="common",
        legalities={"vintage": "legal"},
        keywords=[]
    )

    cache.put(bolt)
    cache.put(grizzly)

    context = cache.get_context_string()
    print(context)
    print("\n✓ Context string generated successfully")

    assert "Lightning Bolt" in context
    assert "Grizzly Bears" in context
    assert "deals 3 damage" in context
    assert "2/2" in context
    print("✓ Context contains card details\n")


def test_access_statistics():
    """Test access count and statistics"""
    print("=" * 60)
    print("TEST 5: Access Statistics")
    print("=" * 60)

    cache = CAGCache(max_size=5)

    bolt = create_test_card("Lightning Bolt")
    cache.put(bolt)

    # Access the card multiple times
    for _ in range(10):
        cache.get("Lightning Bolt")

    # Try to get a card that doesn't exist
    for _ in range(5):
        cache.get("Black Lotus")

    stats = cache.get_stats()
    print(f"Stats after accesses: {stats}")

    assert stats["hits"] == 10, f"Expected 10 hits, got {stats['hits']}"
    assert stats["misses"] == 5, f"Expected 5 misses, got {stats['misses']}"
    print("✓ Hit/miss tracking works correctly\n")


if __name__ == "__main__":
    test_basic_operations()
    test_lru_eviction()
    test_batch_operations()
    test_context_generation()
    test_access_statistics()

    print("=" * 60)
    print("ALL TESTS PASSED! ✓")
    print("=" * 60)
