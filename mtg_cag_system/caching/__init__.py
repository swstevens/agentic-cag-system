"""
Unified caching implementations following Strategy Pattern.

All cache implementations implement ICache interface, making them
interchangeable and testable.
"""

from .lru_cache import LRUCache
from .tiered_cache import TieredCache

__all__ = [
    "LRUCache",
    "TieredCache",
]
