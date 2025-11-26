"""
Card Repository for V3 architecture with CAG support.

Provides high-level interface for card data access with
two-tier lookup: cache first, then database.
"""

from typing import List, Optional
from ..database.database_service import DatabaseService
from ..models.deck import MTGCard, CardSearchFilters
from ..caching import ICache, LRUCache


class CardRepository:
    """
    Repository for card data access with CAG (Cache-Augmented Generation).
    
    Implements two-tier lookup strategy:
    1. Check cache first (O(1) for hot cards)
    2. Fall back to database (O(log n) with indexes)
    3. Promote database hits to cache
    """
    
    def __init__(
        self,
        database_service: DatabaseService,
        cache: Optional[ICache] = None,
        cache_size: int = 2000
    ):
        """
        Initialize card repository.
        
        Args:
            database_service: Database service instance
            cache: Optional cache instance (creates LRUCache if None)
            cache_size: Cache size if creating default cache
        """
        self.db = database_service
        self.cache = cache or LRUCache(max_size=cache_size)
    
    def get_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Get a card by exact name with two-tier lookup.
        
        Args:
            name: Card name (case-insensitive)
            
        Returns:
            MTGCard if found, None otherwise
        """
        # Tier 1: Check cache
        cached_card = self.cache.get(name)
        if cached_card:
            return cached_card
        
        # Tier 2: Query database
        card_data = self.db.get_card_by_name(name)
        if card_data:
            card = MTGCard(**card_data)
            # Promote to cache for future hits
            self.cache.put(name, card)
            return card
        
        return None
    
    def get_by_id(self, card_id: str) -> Optional[MTGCard]:
        """
        Get a card by ID.
        
        Args:
            card_id: Unique card identifier
            
        Returns:
            MTGCard if found, None otherwise
        """
        # Try cache with ID as key
        cached_card = self.cache.get(card_id)
        if cached_card:
            return cached_card
        
        card_data = self.db.get_card_by_id(card_id)
        if card_data:
            card = MTGCard(**card_data)
            # Cache by both ID and name
            self.cache.put(card_id, card)
            self.cache.put(card.name, card)
            return card
        
        return None
    
    def search(self, filters: CardSearchFilters) -> List[MTGCard]:
        """
        Search for cards matching filters.
        
        Note: Search results are not cached by default due to the
        large number of possible query combinations.
        
        Args:
            filters: Search filters
            
        Returns:
            List of matching MTGCard objects
        """
        card_data_list = self.db.search_cards(
            colors=filters.colors,
            types=filters.types,
            cmc_min=filters.cmc_min,
            cmc_max=filters.cmc_max,
            rarity=filters.rarity,
            format_legal=filters.format_legal,
            text_query=filters.text_query,
            limit=filters.limit
        )
        
        cards = [MTGCard(**card_data) for card_data in card_data_list]
        
        # Optionally cache top results for future exact lookups
        for card in cards[:10]:  # Cache top 10 results
            if not self.cache.get(card.name):
                self.cache.put(card.name, card)
        
        return cards
    
    def get_cards_by_type(self, card_type: str, limit: int = 100) -> List[MTGCard]:
        """
        Get cards by type.
        
        Args:
            card_type: Card type (e.g., "Creature", "Instant")
            limit: Maximum results
            
        Returns:
            List of MTGCard objects
        """
        filters = CardSearchFilters(types=[card_type], limit=limit)
        return self.search(filters)
    
    def get_cards_by_colors(self, colors: List[str], limit: int = 100) -> List[MTGCard]:
        """
        Get cards by color identity.
        
        Args:
            colors: List of color codes (W, U, B, R, G)
            limit: Maximum results
            
        Returns:
            List of MTGCard objects
        """
        filters = CardSearchFilters(colors=colors, limit=limit)
        return self.search(filters)
    
    def get_lands(self, colors: Optional[List[str]] = None, limit: int = 50) -> List[MTGCard]:
        """
        Get land cards, optionally filtered by color production.
        
        Args:
            colors: Optional color filter
            limit: Maximum results
            
        Returns:
            List of land MTGCard objects
        """
        filters = CardSearchFilters(
            types=["Land"],
            colors=colors,
            limit=limit
        )
        return self.search(filters)
    
    def preload_popular_cards(self, card_names: List[str]) -> int:
        """
        Preload specific cards into cache (for CAG warmup).
        
        Args:
            card_names: List of card names to preload
            
        Returns:
            Number of cards successfully preloaded
        """
        count = 0
        for name in card_names:
            card = self.get_by_name(name)
            if card:
                count += 1
        return count
    
    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache stats
        """
        stats = self.cache.get_stats()
        return {
            "hits": stats.hits,
            "misses": stats.misses,
            "evictions": stats.evictions,
            "size": stats.size,
            "hit_rate": stats.hit_rate,
        }

