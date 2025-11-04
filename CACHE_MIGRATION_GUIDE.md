# Cache Migration Guide

## ⚠️ CAGCache & MultiTierCache → Unified ICache Interface

The legacy `CAGCache` and `MultiTierCache` have been refactored into unified cache implementations that follow the `ICache` interface.

## Why Migrate?

- **Unified Interface**: All caches implement `ICache`, making them interchangeable
- **Strategy Pattern**: Easy to swap cache implementations without changing code
- **Better Testing**: Mock caches with simple interface
- **Type Safety**: Pydantic-based `CacheStats` for statistics
- **Cleaner API**: Consistent methods across all cache types

## Migration Path

### Before (Legacy CAGCache)

```python
from mtg_cag_system.services.cag_cache import CAGCache

# Create cache
cache = CAGCache(max_size=2000)

# Use cache
card = cache.get("Lightning Bolt")
cache.put("Counterspell", card_object)

# Get stats
print(f"Hits: {cache.hits}, Misses: {cache.misses}")
```

### After (New LRUCache)

```python
from mtg_cag_system.caching import LRUCache

# Create cache (same constructor)
cache = LRUCache(max_size=2000)

# Use cache (same API!)
card = cache.get("Lightning Bolt")
cache.put("Counterspell", card_object)

# Get stats (now returns Pydantic model)
stats = cache.get_stats()
print(f"Hits: {stats.hits}, Misses: {stats.misses}")
print(f"Hit Rate: {stats.hit_rate:.2%}")
```

### Before (Legacy MultiTierCache)

```python
from mtg_cag_system.services.cache_service import MultiTierCache

# Create cache
cache = MultiTierCache()
cache.l1_max_size = 200
cache.l2_max_size = 1000
cache.l3_max_size = 10000

# Use cache
value = cache.get("query_key")
cache.set("query_key", result, tier=2, ttl=3600)
```

### After (New TieredCache)

```python
from mtg_cag_system.caching import TieredCache

# Create cache with config in constructor
cache = TieredCache(
    l1_max_size=200,
    l2_max_size=1000,
    l3_max_size=10000,
    promotion_threshold=5
)

# Use cache (unified API)
value = cache.get("query_key")
cache.put("query_key", result)  # Goes to L2 by default

# Or specify tier explicitly
cache.put_in_tier("hot_key", result, tier=1, ttl=3600)

# Get tier-specific stats
tier_sizes = cache.get_tier_sizes()
print(f"L1: {tier_sizes['l1']}, L2: {tier_sizes['l2']}, L3: {tier_sizes['l3']}")
```

## Key Changes

### 1. Unified ICache Interface

All caches now implement:

```python
class ICache(ABC):
    def get(self, key: str) -> Optional[Any]
    def put(self, key: str, value: Any) -> None
    def evict(self, key: str) -> None
    def clear(self) -> None
    def get_stats(self) -> CacheStats
```

### 2. CacheStats Pydantic Model

Statistics are now returned as a Pydantic model:

```python
from mtg_cag_system.interfaces.cache import CacheStats

stats = cache.get_stats()
print(f"Hit Rate: {stats.hit_rate:.2%}")  # Computed property
print(f"Size: {stats.size}")
print(f"Evictions: {stats.evictions}")
```

### 3. Type Safety

```python
from mtg_cag_system.interfaces.cache import ICache
from mtg_cag_system.caching import LRUCache, TieredCache

def process_with_cache(cache: ICache):  # ← Type hint with interface
    result = cache.get("key")
    if result is None:
        result = expensive_operation()
        cache.put("key", result)
    return result

# Works with any ICache implementation
process_with_cache(LRUCache(max_size=1000))
process_with_cache(TieredCache())
```

## Migration for CardLookupService

### Before

```python
from mtg_cag_system.services.cag_cache import CAGCache
from mtg_cag_system.services.card_lookup_service import CardLookupService

cache = CAGCache(max_size=2000)
lookup_service = CardLookupService(cag_cache=cache, database_service=db)
```

### After

```python
from mtg_cag_system.caching import LRUCache
from mtg_cag_system.repositories import CardRepository

cache = LRUCache(max_size=2000)  # Implements ICache
repository = CardRepository(cache=cache, database_service=db)
```

## Migration for CardRepository

The new `CardRepository` accepts any `ICache` implementation:

```python
from mtg_cag_system.caching import LRUCache, TieredCache
from mtg_cag_system.repositories import CardRepository

# Option 1: LRU cache (simple, fast)
lru_cache = LRUCache(max_size=2000)
repo = CardRepository(cache=lru_cache, database_service=db)

# Option 2: Tiered cache (sophisticated, auto-promotion)
tiered_cache = TieredCache(l1_max_size=200, l2_max_size=1000)
repo = CardRepository(cache=tiered_cache, database_service=db)
```

## Backward Compatibility

### Keeping Old Code Working

The legacy `CAGCache` and `MultiTierCache` remain in place temporarily. They will eventually be removed.

To use old code without warnings:

```python
# Old imports still work (but are deprecated)
from mtg_cag_system.services.cag_cache import CAGCache
from mtg_cag_system.services.cache_service import MultiTierCache

# But you should migrate to:
from mtg_cag_system.caching import LRUCache, TieredCache
```

## Testing with Mock Caches

The unified interface makes testing easier:

```python
from mtg_cag_system.interfaces.cache import ICache
from typing import Optional, Any

class MockCache(ICache):
    """Mock cache for testing"""
    def __init__(self):
        self._store = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def put(self, key: str, value: Any) -> None:
        self._store[key] = value

    def evict(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def get_stats(self) -> CacheStats:
        return CacheStats(size=len(self._store))

# Use in tests
def test_repository_with_mock():
    mock_cache = MockCache()
    repo = CardRepository(cache=mock_cache, database_service=db)
    # ... test logic
```

## Performance Notes

### LRUCache (formerly CAGCache)

- **Use for**: Hot card caching, frequently accessed data
- **Complexity**: O(1) get/put
- **Memory**: Fixed size with automatic eviction
- **Best for**: Single-tier caching with predictable access patterns

### TieredCache (formerly MultiTierCache)

- **Use for**: Query result caching, multi-tier data
- **Complexity**: O(1) get/put per tier
- **Memory**: 3-tier with automatic promotion
- **Best for**: Data with varying access frequencies

## Timeline

- **Now**: New cache implementations available, old ones remain
- **v2.0**: Old caches deprecated with warnings
- **v3.0**: Old caches removed
- **Recommendation**: Migrate now to avoid future breakage

## Questions?

See the cache interface documentation in `mtg_cag_system/interfaces/cache.py` for more details.
