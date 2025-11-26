"""
Caching layer for CAG (Cache-Augmented Generation).

Ported from v2 to support efficient card lookups.
"""

from .cache_interface import ICache, CacheStats
from .lru_cache import LRUCache

__all__ = [
    "ICache",
    "CacheStats",
    "LRUCache",
]
