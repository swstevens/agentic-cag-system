"""
Card Lookup Service - Two-Tier System

Tier 1: CAG Cache (hot cards with LRU eviction)
Tier 2: SQLite Database (all MTG cards)

This service provides a unified interface for card lookups with automatic
caching and fallback to database.
"""

from typing import Optional, List
from ..models.card import MTGCard
from .cag_cache import CAGCache
from .database_service import DatabaseService


class CardLookupService:
    """
    Two-tier card lookup service

    Flow:
    1. Check CAG cache (Tier 1) - O(1) lookup
    2. If miss, query SQLite database (Tier 2) - O(log n) indexed lookup
    3. If found in database, add to cache for future queries
    """

    def __init__(
        self,
        database_service: Optional[DatabaseService] = None,
        cache_size: int = 200
    ):
        """
        Initialize card lookup service

        Args:
            database_service: SQLite database service for Tier 2 lookups
            cache_size: Maximum number of cards to keep in CAG cache
        """
        # Private: Tier 1 - CAG Cache
        self.__cag_cache = CAGCache(max_size=cache_size)

        # Private: Tier 2 - Database
        self.__database = database_service

        # Public: Statistics
        self.tier1_hits = 0
        self.tier2_hits = 0
        self.total_misses = 0

    def get_card(self, card_name: str) -> Optional[MTGCard]:
        """
        Get card by name using two-tier lookup (Public API)

        Args:
            card_name: Name of the card to retrieve

        Returns:
            MTGCard if found, None otherwise
        """
        # Tier 1: Check CAG cache
        card = self.__cag_cache.get(card_name)
        if card:
            self.tier1_hits += 1
            print(f"[Tier 1 HIT] Found '{card_name}' in CAG cache")
            return card

        # Tier 2: Query database
        if self.__database:
            card = self.__database.get_card_by_name(card_name)
            if card:
                self.tier2_hits += 1
                print(f"[Tier 2 HIT] Found '{card_name}' in database, adding to cache")

                # Promote to cache for future queries
                self.__cag_cache.put(card)
                return card

        # Not found in either tier
        self.total_misses += 1
        print(f"[MISS] Card '{card_name}' not found in cache or database")
        return None

    def fuzzy_search(self, query: str, limit: int = 10) -> List[MTGCard]:
        """
        Fuzzy search for cards (Public API)

        First checks cache, then falls back to database fuzzy search.

        Args:
            query: Search term
            limit: Maximum number of results

        Returns:
            List of matching MTGCard objects
        """
        results = []

        # Check if query matches any cached cards (case-insensitive substring)
        cached_cards = self.__cag_cache.get_all_cards()
        query_lower = query.lower()

        for card in cached_cards:
            if query_lower in card.name.lower():
                results.append(card)
                if len(results) >= limit:
                    return results

        # If we need more results, query database
        if len(results) < limit and self.__database:
            db_results = self.__database.fuzzy_search(query, limit - len(results))

            # Add database results to cache and results list
            for card in db_results:
                if card not in results:  # Avoid duplicates
                    results.append(card)
                    self.__cag_cache.put(card)

        return results[:limit]

    def preload_cards(self, cards: List[MTGCard]) -> None:
        """
        Preload specific cards into CAG cache (Public API)

        Useful for preloading popular cards, starter decks, or user favorites.

        Args:
            cards: List of MTGCard objects to preload
        """
        self.__cag_cache.put_batch(cards)
        print(f"[Preload] Added {len(cards)} cards to CAG cache")

    def preload_by_names(self, card_names: List[str]) -> int:
        """
        Preload cards by name from database (Public API)

        Args:
            card_names: List of card names to preload

        Returns:
            Number of cards successfully preloaded
        """
        if not self.__database:
            print("[Preload] No database available, cannot preload by names")
            return 0

        loaded_count = 0
        for name in card_names:
            card = self.__database.get_card_by_name(name)
            if card:
                self.__cag_cache.put(card)
                loaded_count += 1

        print(f"[Preload] Loaded {loaded_count}/{len(card_names)} cards from database to cache")
        return loaded_count

    def get_cag_context(self) -> str:
        """
        Get CAG context string for LLM preloading (Public API)

        Returns:
            Formatted string of all cached cards for LLM context
        """
        return self.__cag_cache.get_context_string()

    def get_stats(self) -> dict:
        """
        Get lookup statistics (Public API)

        Returns:
            Dictionary with tier statistics
        """
        total_queries = self.tier1_hits + self.tier2_hits + self.total_misses
        cache_stats = self.__cag_cache.get_stats()

        return {
            "tier1_hits": self.tier1_hits,
            "tier2_hits": self.tier2_hits,
            "total_misses": self.total_misses,
            "total_queries": total_queries,
            "tier1_hit_rate": f"{(self.tier1_hits / total_queries * 100):.2f}%" if total_queries > 0 else "0.00%",
            "tier2_hit_rate": f"{(self.tier2_hits / total_queries * 100):.2f}%" if total_queries > 0 else "0.00%",
            "overall_hit_rate": f"{((self.tier1_hits + self.tier2_hits) / total_queries * 100):.2f}%" if total_queries > 0 else "0.00%",
            "cache_stats": cache_stats,
            "database_connected": self.__database is not None
        }

    def clear_cache(self) -> None:
        """Clear the CAG cache (Public API)"""
        self.__cag_cache.clear()
        print("[Cache] CAG cache cleared")

    def get_cached_card_names(self) -> List[str]:
        """
        Get list of all cards currently in cache (Public API)

        Returns:
            List of card names in LRU order
        """
        return self.__cag_cache.get_lru_order()
