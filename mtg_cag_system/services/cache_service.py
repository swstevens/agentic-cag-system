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
        # Private: Internal cache storage (users shouldn't access directly)
        self.__l1_cache: Dict[str, CacheEntry] = {}
        self.__l2_cache: Dict[str, CacheEntry] = {}
        self.__l3_cache: Dict[str, CacheEntry] = {}

        # Public: Configuration (users can modify)
        self.l1_max_size = 200
        self.l2_max_size = 1000
        self.l3_max_size = 10000

    def _generate_cache_key(self, query: str, context: Optional[Dict] = None) -> str:
        """Generate cache key from query and context"""
        data = {"query": query, "context": context or {}}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get from cache, checking all tiers (Public API)"""
        # Check L1
        if key in self.__l1_cache:
            entry = self.__l1_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                return entry.value
            else:
                del self.__l1_cache[key]

        # Check L2
        if key in self.__l2_cache:
            entry = self.__l2_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                # Promote to L1 if frequently accessed
                if entry.access_count > 5:
                    self._promote_to_l1(key, entry)
                return entry.value
            else:
                del self.__l2_cache[key]

        # Check L3
        if key in self.__l3_cache:
            entry = self.__l3_cache[key]
            if not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                return entry.value
            else:
                del self.__l3_cache[key]

        return None

    def set(self, key: str, value: Any, tier: int = 2, ttl: Optional[int] = None):
        """Set cache entry in specified tier (Public API)"""
        entry = CacheEntry(
            key=key,
            value=value,
            cached_at=datetime.now(),
            ttl=ttl
        )

        if tier == 1:
            self._evict_if_needed(self.__l1_cache, self.l1_max_size)
            self.__l1_cache[key] = entry
        elif tier == 2:
            self._evict_if_needed(self.__l2_cache, self.l2_max_size)
            self.__l2_cache[key] = entry
        else:
            self._evict_if_needed(self.__l3_cache, self.l3_max_size)
            self.__l3_cache[key] = entry

    def _promote_to_l1(self, key: str, entry: CacheEntry):
        """Promote entry from L2 to L1 (Protected - internal logic)"""
        self._evict_if_needed(self.__l1_cache, self.l1_max_size)
        self.__l1_cache[key] = entry
        if key in self.__l2_cache:
            del self.__l2_cache[key]

    def _evict_if_needed(self, cache: Dict[str, CacheEntry], max_size: int):
        """Evict least recently used entries if cache is full (Protected - internal logic)"""
        if len(cache) >= max_size:
            # Find LRU entry
            lru_key = min(cache.keys(), key=lambda k: cache[k].last_accessed)
            del cache[lru_key]

    def clear_tier(self, tier: int):
        """Clear specific cache tier (Public API)"""
        if tier == 1:
            self.__l1_cache.clear()
        elif tier == 2:
            self.__l2_cache.clear()
        else:
            self.__l3_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics (Public API)"""
        return {
            "l1_size": len(self.__l1_cache),
            "l2_size": len(self.__l2_cache),
            "l3_size": len(self.__l3_cache),
            "l1_max": self.l1_max_size,
            "l2_max": self.l2_max_size,
            "l3_max": self.l3_max_size
        }
