from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib
import json


class CacheEntry(BaseModel):
    """Single cache entry"""
    key: str
    value: Any
    cached_at: datetime
    ttl: Optional[int] = None  # seconds
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (datetime.now() - self.cached_at).total_seconds() > self.ttl


class MultiTierCache:
    """Multi-tier cache system for CAG"""

    def __init__(self):
        # L1: Hot cache - frequently accessed cards and knowledge
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l1_max_size = 200

        # L2: Warm cache - patterns and relationships
        self.l2_cache: Dict[str, CacheEntry] = {}
        self.l2_max_size = 1000

        # L3: Cold storage - historical data
        self.l3_cache: Dict[str, CacheEntry] = {}
        self.l3_max_size = 10000

    def _generate_key(self, query: str, context: Optional[Dict] = None) -> str:
        """Generate cache key from query and context"""
        data = {"query": query, "context": context or {}}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get from cache, checking all tiers"""
        # Check L1
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                return entry.value
            else:
                del self.l1_cache[key]

        # Check L2
        if key in self.l2_cache:
            entry = self.l2_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                # Promote to L1 if frequently accessed
                if entry.access_count > 5:
                    self._promote_to_l1(key, entry)
                return entry.value
            else:
                del self.l2_cache[key]

        # Check L3
        if key in self.l3_cache:
            entry = self.l3_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                return entry.value
            else:
                del self.l3_cache[key]

        return None

    def set(self, key: str, value: Any, tier: int = 2, ttl: Optional[int] = None):
        """Set cache entry in specified tier"""
        entry = CacheEntry(
            key=key,
            value=value,
            cached_at=datetime.now(),
            ttl=ttl
        )

        if tier == 1:
            self._evict_if_needed(self.l1_cache, self.l1_max_size)
            self.l1_cache[key] = entry
        elif tier == 2:
            self._evict_if_needed(self.l2_cache, self.l2_max_size)
            self.l2_cache[key] = entry
        else:
            self._evict_if_needed(self.l3_cache, self.l3_max_size)
            self.l3_cache[key] = entry

    def _promote_to_l1(self, key: str, entry: CacheEntry):
        """Promote entry from L2 to L1"""
        self._evict_if_needed(self.l1_cache, self.l1_max_size)
        self.l1_cache[key] = entry
        if key in self.l2_cache:
            del self.l2_cache[key]

    def _evict_if_needed(self, cache: Dict[str, CacheEntry], max_size: int):
        """Evict least recently used entries if cache is full"""
        if len(cache) >= max_size:
            # Find LRU entry
            lru_key = min(cache.keys(), key=lambda k: cache[k].last_accessed)
            del cache[lru_key]

    def clear_tier(self, tier: int):
        """Clear specific cache tier"""
        if tier == 1:
            self.l1_cache.clear()
        elif tier == 2:
            self.l2_cache.clear()
        else:
            self.l3_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "l1_size": len(self.l1_cache),
            "l2_size": len(self.l2_cache),
            "l3_size": len(self.l3_cache),
            "l1_max": self.l1_max_size,
            "l2_max": self.l2_max_size,
            "l3_max": self.l3_max_size
        }
