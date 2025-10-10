from typing import List, Optional, Dict, Any
from ..models.card import MTGCard, CardCollection
from .cache_service import MultiTierCache
from .database_service import DatabaseService


class KnowledgeService:
    """Service for managing CAG knowledge base"""

    def __init__(self, cache_service: MultiTierCache, database_service: Optional[DatabaseService] = None):
        self.cache = cache_service
        self.db = database_service
        self.knowledge_base: Optional[CardCollection] = None
        self.preloaded_context: Optional[str] = None
        self.kv_cache_ready = False

    async def load_cards_from_mtgjson(self, json_path: str, format_filter: Optional[str] = "Standard") -> CardCollection:
        """Load MTG cards from MTGJSON file"""
        # In production, this would actually parse MTGJSON
        # For now, example structure
        cards = []  # Parse from JSON

        collection = CardCollection(
            cards=cards,
            total_count=len(cards),
            format_filter=format_filter
        )

        self.knowledge_base = collection
        return collection

    async def preload_knowledge(self, collection: CardCollection):
        """Preload cards into CAG context"""
        # Convert to context string for preloading
        self.preloaded_context = collection.to_context_string()

        # Cache individual cards in L1 for fast lookup
        for card in collection.cards:
            cache_key = f"card:{card.name.lower()}"
            self.cache.set(cache_key, card.dict(), tier=1, ttl=None)

        # Mark KV cache as ready
        self.kv_cache_ready = True

        print(f"Preloaded {len(collection.cards)} cards into CAG context")
        print(f"Context size: {len(self.preloaded_context)} characters")

    def get_card_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Retrieve card from cache, with database fallback

        Flow:
        1. Check L1/L2/L3 cache tiers
        2. If cache miss, query SQLite database
        3. Cache the result in L3 for future lookups
        4. Return card or None
        """
        # Try cache first (L1/L2/L3)
        cache_key = f"card:{name.lower()}"
        card_data = self.cache.get(cache_key)
        if card_data:
            return MTGCard(**card_data)

        # Cache miss - fallback to database
        if self.db:
            card = self.db.get_card_by_name(name)
            if card:
                # Cache in L3 for future lookups
                self.cache.set(cache_key, card.dict(), tier=3, ttl=None)
                print(f"📀 Database hit: {name} (cached to L3)")
                return card

        # Not found in cache or database
        return None

    def search_cards(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[MTGCard]:
        """Search for cards matching criteria"""
        if not self.knowledge_base:
            return []

        results = []
        query_lower = query.lower()

        for card in self.knowledge_base.cards:
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
        """Get relevant context for a query (CAG approach)"""
        # In CAG, we return the entire preloaded context
        # The LLM will use its attention mechanism to focus on relevant parts
        return self.preloaded_context or ""
