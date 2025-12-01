"""
Test script to demonstrate CAG (Cache-Augmented Generation) in v3.

Shows cache performance with and without caching enabled.
"""

import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from v3.database import DatabaseService, CardRepository
from v3.caching import LRUCache


async def test_without_cache():
    """Test card lookups without caching."""
    print("=" * 60)
    print("TEST 1: WITHOUT CACHING")
    print("=" * 60)
    
    db = DatabaseService()
    repo = CardRepository(db, cache=None, cache_size=0)  # No cache
    
    # Popular cards to look up
    popular_cards = [
        "Lightning Bolt",
        "Counterspell",
        "Dark Ritual",
        "Giant Growth",
        "Swords to Plowshares",
    ] * 10  # Repeat 10 times to simulate repeated lookups
    
    start = time.time()
    for card_name in popular_cards:
        card = repo.get_by_name(card_name)
    end = time.time()
    
    print(f"Looked up {len(popular_cards)} cards (5 unique, repeated 10x each)")
    print(f"Time: {(end - start) * 1000:.2f}ms")
    print(f"Avg per lookup: {(end - start) * 1000 / len(popular_cards):.2f}ms")
    print()


async def test_with_cache():
    """Test card lookups with LRU caching."""
    print("=" * 60)
    print("TEST 2: WITH LRU CACHING")
    print("=" * 60)
    
    db = DatabaseService()
    cache = LRUCache(max_size=100)
    repo = CardRepository(db, cache=cache)
    
    # Same popular cards
    popular_cards = [
        "Lightning Bolt",
        "Counterspell",
        "Dark Ritual",
        "Giant Growth",
        "Swords to Plowshares",
    ] * 10  # Repeat 10 times
    
    start = time.time()
    for card_name in popular_cards:
        card = repo.get_by_name(card_name)
    end = time.time()
    
    print(f"Looked up {len(popular_cards)} cards (5 unique, repeated 10x each)")
    print(f"Time: {(end - start) * 1000:.2f}ms")
    print(f"Avg per lookup: {(end - start) * 1000 / len(popular_cards):.2f}ms")
    print()
    
    # Show cache stats
    stats = repo.get_cache_stats()
    print("Cache Statistics:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate'] * 100:.1f}%")
    print(f"  Cache Size: {stats['size']}")
    print(f"  Evictions: {stats['evictions']}")
    print()


async def test_cache_warmup():
    """Test cache warmup with preloading."""
    print("=" * 60)
    print("TEST 3: CACHE WARMUP (Preloading)")
    print("=" * 60)
    
    db = DatabaseService()
    cache = LRUCache(max_size=100)
    repo = CardRepository(db, cache=cache)
    
    # Preload popular cards
    popular_cards = [
        "Lightning Bolt",
        "Counterspell",
        "Dark Ritual",
        "Giant Growth",
        "Swords to Plowshares",
        "Path to Exile",
        "Fatal Push",
        "Thoughtseize",
        "Brainstorm",
        "Ponder",
    ]
    
    print("Preloading popular cards...")
    preloaded = repo.preload_popular_cards(popular_cards)
    print(f"Preloaded {preloaded} cards into cache")
    print()
    
    # Now look them up (should all be cache hits)
    start = time.time()
    for card_name in popular_cards * 5:  # Repeat 5x
        card = repo.get_by_name(card_name)
    end = time.time()
    
    print(f"Looked up {len(popular_cards) * 5} cards (all from cache)")
    print(f"Time: {(end - start) * 1000:.2f}ms")
    print(f"Avg per lookup: {(end - start) * 1000 / (len(popular_cards) * 5):.2f}ms")
    print()
    
    # Show cache stats
    stats = repo.get_cache_stats()
    print("Cache Statistics:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate'] * 100:.1f}%")
    print()


async def main():
    """Run all cache tests."""
    print("\n" + "=" * 60)
    print("CAG (Cache-Augmented Generation) Performance Test")
    print("=" * 60 + "\n")
    
    await test_without_cache()
    await test_with_cache()
    await test_cache_warmup()
    
    print("=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("Caching provides significant performance improvements for")
    print("repeated card lookups, which is essential for CAG systems.")
    print("The LRU cache automatically manages memory and evicts old")
    print("entries when capacity is reached.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
