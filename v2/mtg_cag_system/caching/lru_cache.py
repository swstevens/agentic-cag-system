"""
LRU (Least Recently Used) Cache implementation.

Refactored from CAGCache to implement ICache interface.
Uses OrderedDict for O(1) access and efficient LRU eviction.
"""

from typing import Optional, Any, OrderedDict as OrderedDictType
from collections import OrderedDict
from datetime import datetime
from ..interfaces.cache import ICache, CacheStats


class LRUCache(ICache):
    """
    LRU Cache implementation using OrderedDict.

    This is a refactored version of CAGCache that implements the
    unified ICache interface, making it interchangeable with other
    cache strategies.

    Features:
    - O(1) get/put operations
    - Automatic LRU eviction when max size reached
    - Access count tracking
    - Thread-safe for single-threaded async code
    """

    def __init__(self, max_size: int = 2000):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries (default: 2000)
        """
        self._cache: OrderedDictType[str, Any] = OrderedDict()
        self._max_size = max_size

        # Statistics tracking
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache with LRU tracking.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        key = self._normalize_key(key)

        if key in self._cache:
            # Cache hit - move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats.hits += 1
            return self._cache[key]

        # Cache miss
        self._stats.misses += 1
        return None

    def put(self, key: str, value: Any) -> None:
        """
        Store value in cache with LRU eviction if needed.

        Args:
            key: Cache key
            value: Value to cache
        """
        key = self._normalize_key(key)

        # If key exists, update and move to end
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return

        # If at capacity, evict LRU item
        if len(self._cache) >= self._max_size:
            self._evict_lru()

        # Add new entry
        self._cache[key] = value
        self._stats.size = len(self._cache)

    def evict(self, key: str) -> None:
        """
        Remove specific key from cache.

        Args:
            key: Cache key to evict
        """
        key = self._normalize_key(key)
        if key in self._cache:
            del self._cache[key]
            self._stats.evictions += 1
            self._stats.size = len(self._cache)

    def clear(self) -> None:
        """Clear all entries from cache."""
        self._cache.clear()
        self._stats = CacheStats()  # Reset stats

    def get_stats(self) -> CacheStats:
        """
        Get cache performance statistics.

        Returns:
            CacheStats with hits, misses, evictions, size, and hit_rate
        """
        self._stats.size = len(self._cache)
        return self._stats

    def _evict_lru(self) -> None:
        """Evict the least recently used item (first item in OrderedDict)."""
        if self._cache:
            self._cache.popitem(last=False)  # FIFO = oldest first
            self._stats.evictions += 1

    def _normalize_key(self, key: str) -> str:
        """Normalize cache key (lowercase for card names)."""
        return key.lower().strip()

    # Additional helper methods for compatibility with old CAGCache API
    def preload_cards(self, cards: list) -> None:
        """
        Preload multiple cards into cache.

        Args:
            cards: List of items to preload
        """
        for card in cards:
            # Assume cards have a 'name' attribute
            if hasattr(card, 'name'):
                self.put(card.name, card)
            else:
                # For dict-based cards
                self.put(card.get('name', ''), card)

    def get_size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def get_max_size(self) -> int:
        """Get maximum cache size."""
        return self._max_size
