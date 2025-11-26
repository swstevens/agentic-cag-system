from typing import List, Optional, Dict, Any
from ..models.card import MTGCard, CardCollection
from .cache_service import MultiTierCache
from .database_service import DatabaseService


class KnowledgeService:
    """Service for managing CAG knowledge base"""

    def __init__(self, cache_service: MultiTierCache, database_service: Optional[DatabaseService] = None):
        # Private: Internal dependencies (should not be accessed directly)
        self.__cache = cache_service
        self.__db = database_service

        # Private: Internal state
        self.__knowledge_base: Optional[CardCollection] = None
        self.__preloaded_context: Optional[str] = None
        self.__tier1_hits = 0
        self.__tier2_hits = 0

        # Public: Status flags (read-only via property recommended)
        self.kv_cache_ready = False
        
    def get_stats(self) -> Dict[str, int]:
        """Get lookup statistics (Public API)"""
        return {
            "tier1_hits": self.__tier1_hits,
            "tier2_hits": self.__tier2_hits
        }

    async def load_cards_from_mtgjson(self, json_path: str, format_filter: Optional[str] = "Standard") -> CardCollection:
        """Load MTG cards from MTGJSON file (Public API)"""
        # In production, this would actually parse MTGJSON
        # For now, example structure
        cards = []  # Parse from JSON

        collection = CardCollection(
            cards=cards,
            total_count=len(cards),
            format_filter=format_filter
        )

        self.__knowledge_base = collection
        return collection

    async def preload_knowledge(self, collection: CardCollection):
        """Preload cards into CAG context (Public API)"""
        # Convert to context string for preloading
        self.__preloaded_context = collection.to_context_string()

        # Cache individual cards in L1 for fast lookup
        for card in collection.cards:
            cache_key = self._make_cache_key(card.name)
            self.__cache.set(cache_key, card.dict(), tier=1, ttl=None)

        # Mark KV cache as ready
        self.kv_cache_ready = True

        print(f"Preloaded {len(collection.cards)} cards into CAG context")
        print(f"Context size: {len(self.__preloaded_context)} characters")

    def get_card_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Retrieve card from cache, with database fallback (Public API)

        Flow:
        1. Check L1/L2/L3 cache tiers
        2. If cache miss, query SQLite database
        3. Cache the result in L3 for future lookups
        4. Return card or None
        """
        # Try cache first (L1/L2/L3)
        cache_key = self._make_cache_key(name)
        card_data = self.__cache.get(cache_key)
        if card_data:
            # Track tier 1 hit (CAG knowledge cache)
            self.__tier1_hits += 1
            return MTGCard(**card_data)

        # Cache miss - fallback to database
        if self.__db:
            card = self.__db.get_card_by_name(name)
            if card:
                # Cache in L3 for future lookups
                self.__cache.set(cache_key, card.dict(), tier=3, ttl=None)
                # Track tier 2 hit (database)
                self.__tier2_hits += 1
                print(f"[DB HIT] Database hit: {name} (cached to L3)")
                return card

        # Not found in cache or database
        return None

    def search_cards(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[MTGCard]:
        """Search for cards matching criteria (Public API)"""
        if not self.__knowledge_base:
            return []

        results = []
        query_lower = query.lower()

        for card in self.__knowledge_base.cards:
            # Simple text matching - in production would use more sophisticated search
            if (query_lower in card.name.lower() or
                (card.oracle_text and query_lower in card.oracle_text.lower())):

                # Apply filters
                if filters:
                    if "colors" in filters and not any(c in card.colors for c in filters["colors"]):
                        continue
                    if "types" in filters and not any(t in card.types for t in filters["types"]):
                        continue

                results.append(card)

        return results

    def get_context_for_query(self, query: str) -> str:
        """Get relevant context for a query - CAG approach (Public API)"""
        # In CAG, we return the entire preloaded context
        # The LLM will use its attention mechanism to focus on relevant parts
        return self.__preloaded_context or ""

    def _make_cache_key(self, card_name: str) -> str:
        """Generate cache key from card name (Protected - internal helper)"""
        return f"card:{card_name.lower()}"
