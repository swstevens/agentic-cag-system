"""
Cache interface - unified contract for all caching strategies.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from pydantic import BaseModel


class CacheStats(BaseModel):
    """Statistics about cache performance"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class ICache(ABC):
    """
    Unified cache interface following Strategy Pattern.

    All cache implementations (LRU, Tiered, TTL) implement this interface,
    making them interchangeable.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        pass

    @abstractmethod
    def evict(self, key: str) -> None:
        """
        Remove specific key from cache.

        Args:
            key: Cache key to evict
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from cache."""
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """
        Get cache performance statistics.

        Returns:
            CacheStats with hits, misses, evictions, and size
        """
        pass
