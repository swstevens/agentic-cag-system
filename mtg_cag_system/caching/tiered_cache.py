"""
Tiered Cache implementation with L1/L2/L3 levels.

Refactored from MultiTierCache to implement ICache interface.
"""

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from ..interfaces.cache import ICache, CacheStats


class CacheEntry(BaseModel):
    """Cache entry with TTL and access tracking"""
    key: str
    value: Any
    cached_at: datetime = Field(default_factory=datetime.now)
    ttl: Optional[int] = None  # seconds
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True

    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl is None:
            return False
        return (datetime.now() - self.cached_at).total_seconds() > self.ttl


class TieredCache(ICache):
    """
    Multi-tier cache with automatic promotion.

    Implements 3-tier caching strategy:
    - L1: Hot cache (small, fast, frequently accessed)
    - L2: Warm cache (medium, recently accessed)
    - L3: Cold cache (large, infrequently accessed)

    Items are automatically promoted from L3→L2→L1 based on access patterns.
    """

    def __init__(
        self,
        l1_max_size: int = 200,
        l2_max_size: int = 1000,
        l3_max_size: int = 10000,
        promotion_threshold: int = 5
    ):
        """
        Initialize tiered cache.

        Args:
            l1_max_size: Maximum L1 entries (hot cache)
            l2_max_size: Maximum L2 entries (warm cache)
            l3_max_size: Maximum L3 entries (cold cache)
            promotion_threshold: Access count threshold for L2→L1 promotion
        """
        self._l1_cache: Dict[str, CacheEntry] = {}
        self._l2_cache: Dict[str, CacheEntry] = {}
        self._l3_cache: Dict[str, CacheEntry] = {}

        self._l1_max_size = l1_max_size
        self._l2_max_size = l2_max_size
        self._l3_max_size = l3_max_size
        self._promotion_threshold = promotion_threshold

        # Unified statistics
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache, checking all tiers.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        # Check L1 (hottest)
        if key in self._l1_cache:
            entry = self._l1_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self._stats.hits += 1
                return entry.value
            else:
                del self._l1_cache[key]

        # Check L2 (warm)
        if key in self._l2_cache:
            entry = self._l2_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self._stats.hits += 1

                # Promote to L1 if frequently accessed
                if entry.access_count >= self._promotion_threshold:
                    self._promote_to_l1(key, entry)

                return entry.value
            else:
                del self._l2_cache[key]

        # Check L3 (cold)
        if key in self._l3_cache:
            entry = self._l3_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self._stats.hits += 1
                return entry.value
            else:
                del self._l3_cache[key]

        # Cache miss
        self._stats.misses += 1
        return None

    def put(self, key: str, value: Any) -> None:
        """
        Store value in L2 cache by default.

        New entries start in L2 and can be promoted to L1 based on access.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Create new entry
        entry = CacheEntry(
            key=key,
            value=value,
            cached_at=datetime.now(),
            ttl=None
        )

        # Store in L2 by default
        if len(self._l2_cache) >= self._l2_max_size:
            self._evict_from_tier(2)

        self._l2_cache[key] = entry
        self._stats.size = self._total_size()

    def put_in_tier(self, key: str, value: Any, tier: int, ttl: Optional[int] = None) -> None:
        """
        Store value in specific tier with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            tier: Tier number (1=L1, 2=L2, 3=L3)
            ttl: Time to live in seconds (None = no expiration)
        """
        entry = CacheEntry(
            key=key,
            value=value,
            cached_at=datetime.now(),
            ttl=ttl
        )

        if tier == 1:
            if len(self._l1_cache) >= self._l1_max_size:
                self._evict_from_tier(1)
            self._l1_cache[key] = entry
        elif tier == 2:
            if len(self._l2_cache) >= self._l2_max_size:
                self._evict_from_tier(2)
            self._l2_cache[key] = entry
        elif tier == 3:
            if len(self._l3_cache) >= self._l3_max_size:
                self._evict_from_tier(3)
            self._l3_cache[key] = entry
        else:
            raise ValueError(f"Invalid tier: {tier}. Must be 1, 2, or 3.")

        self._stats.size = self._total_size()

    def evict(self, key: str) -> None:
        """
        Remove key from all tiers.

        Args:
            key: Cache key to evict
        """
        evicted = False

        if key in self._l1_cache:
            del self._l1_cache[key]
            evicted = True

        if key in self._l2_cache:
            del self._l2_cache[key]
            evicted = True

        if key in self._l3_cache:
            del self._l3_cache[key]
            evicted = True

        if evicted:
            self._stats.evictions += 1
            self._stats.size = self._total_size()

    def clear(self) -> None:
        """Clear all tiers."""
        self._l1_cache.clear()
        self._l2_cache.clear()
        self._l3_cache.clear()
        self._stats = CacheStats()

    def get_stats(self) -> CacheStats:
        """
        Get unified cache statistics.

        Returns:
            CacheStats with aggregated statistics from all tiers
        """
        self._stats.size = self._total_size()
        return self._stats

    def _promote_to_l1(self, key: str, entry: CacheEntry) -> None:
        """Promote entry from L2 to L1."""
        # Remove from L2
        if key in self._l2_cache:
            del self._l2_cache[key]

        # Add to L1 (evict if needed)
        if len(self._l1_cache) >= self._l1_max_size:
            self._evict_from_tier(1)

        self._l1_cache[key] = entry

    def _evict_from_tier(self, tier: int) -> None:
        """
        Evict least recently accessed item from specified tier.

        Args:
            tier: Tier to evict from (1, 2, or 3)
        """
        if tier == 1:
            cache = self._l1_cache
        elif tier == 2:
            cache = self._l2_cache
        elif tier == 3:
            cache = self._l3_cache
        else:
            return

        if not cache:
            return

        # Find LRU item (oldest last_accessed)
        lru_key = min(cache.keys(), key=lambda k: cache[k].last_accessed)
        del cache[lru_key]
        self._stats.evictions += 1

    def _total_size(self) -> int:
        """Calculate total entries across all tiers."""
        return len(self._l1_cache) + len(self._l2_cache) + len(self._l3_cache)

    # Additional methods for introspection
    def get_tier_sizes(self) -> Dict[str, int]:
        """Get size of each tier."""
        return {
            "l1": len(self._l1_cache),
            "l2": len(self._l2_cache),
            "l3": len(self._l3_cache),
            "total": self._total_size()
        }
