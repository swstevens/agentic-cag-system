"""
CardRepository implementation using Repository Pattern.

Abstracts the two-tier card lookup (cache + database) behind a clean interface.
This makes testing easier (can mock the repository) and decouples data access
from business logic.
"""

from typing import List, Optional
from ..interfaces.repository import ICardRepository, SearchCriteria
from ..interfaces.cache import ICache
from ..models.card import MTGCard
from ..services.database_service import DatabaseService


class CardRepository(ICardRepository):
    """
    Repository for card data access.

    Implements two-tier lookup strategy:
    1. Check cache first (O(1) for hot cards)
    2. Fall back to database (O(log n) with indexes)
    3. Promote database hits to cache

    This is a wrapper around your existing CardLookupService pattern,
    but with a cleaner interface that follows SOLID principles.
    """

    def __init__(self, cache: ICache, database_service: DatabaseService):
        """
        Initialize repository with cache and database.

        Args:
            cache: Cache implementation (will be ICache-compliant)
            database_service: Database service for fallback queries
        """
        self.cache = cache
        self.database = database_service

    def get_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Get a card by exact name with two-tier lookup.

        Args:
            name: Card name (case-insensitive)

        Returns:
            MTGCard if found, None otherwise
        """
        # Tier 1: Check cache
        cache_key = name.lower()
        cached_card = self.cache.get(cache_key)
        if cached_card:
            return cached_card

        # Tier 2: Query database
        card = self.database.get_card_by_name(name)
        if card:
            # Promote to cache for future hits
            self.cache.put(cache_key, card)
            return card

        return None

    def search(self, criteria: SearchCriteria) -> List[MTGCard]:
        """
        Search for cards matching criteria.

        Note: Search results are not cached by default due to the
        large number of possible query combinations.

        Args:
            criteria: SearchCriteria with filters

        Returns:
            List of matching MTGCard objects
        """
        # Build filter dict for database service
        filters = {}

        if criteria.colors:
            filters["colors"] = [c.value for c in criteria.colors]

        if criteria.types:
            filters["types"] = [t.value for t in criteria.types]

        if criteria.format:
            filters["format"] = criteria.format

        if criteria.cmc_min is not None or criteria.cmc_max is not None:
            filters["cmc_min"] = criteria.cmc_min
            filters["cmc_max"] = criteria.cmc_max

        if criteria.text_query:
            filters["text"] = criteria.text_query

        if criteria.rarity:
            filters["rarity"] = criteria.rarity

        filters["limit"] = criteria.limit

        # Query database with unpacked filters
        cards = self.database.search_cards(
            query=filters.get("text"),
            colors=filters.get("colors"),
            types=filters.get("types"),
            cmc_min=filters.get("cmc_min"),
            cmc_max=filters.get("cmc_max"),
            rarity=filters.get("rarity"),
            format_legality={"standard": "legal"} if filters.get("format") == "Standard" else None,
            limit=filters.get("limit", 100)
        )

        # Optionally: preload popular cards into cache
        # This could be a background task or strategic caching
        for card in cards[:10]:  # Cache top 10 results
            cache_key = card.name.lower()
            if not self.cache.get(cache_key):
                self.cache.put(cache_key, card)

        return cards

    def fuzzy_search(self, name: str, limit: int = 10) -> List[MTGCard]:
        """
        Fuzzy search for cards by name (handles typos).

        Args:
            name: Partial or misspelled card name
            limit: Maximum results to return

        Returns:
            List of closest matching MTGCard objects
        """
        cards = self.database.fuzzy_search(name, limit=limit)

        # Cache the results for exact name matches
        for card in cards:
            cache_key = card.name.lower()
            if not self.cache.get(cache_key):
                self.cache.put(cache_key, card)

        return cards

    def preload_by_names(self, names: List[str]) -> None:
        """
        Preload specific cards into cache.

        Useful for warming the cache with known popular cards.

        Args:
            names: List of card names to preload
        """
        for name in names:
            cache_key = name.lower()
            if not self.cache.get(cache_key):
                card = self.database.get_card_by_name(name)
                if card:
                    self.cache.put(cache_key, card)

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (hits, misses, hit_rate, etc.)
        """
        stats = self.cache.get_stats()
        return {
            "cache_hits": stats.hits,
            "cache_misses": stats.misses,
            "cache_size": stats.size,
            "cache_hit_rate": stats.hit_rate,
            "cache_evictions": stats.evictions,
        }
