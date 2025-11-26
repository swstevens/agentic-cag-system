"""
CAG (Cache-Augmented Generation) Cache Service

Two-tier caching system:
- Tier 1 (CAG Cache): Hot cards preloaded into LLM context, with LRU eviction
- Tier 2 (RAG Lookup): To be implemented - either document search or SQLite
"""

from typing import Optional, Dict, Any, List, OrderedDict as OrderedDictType
from collections import OrderedDict
from datetime import datetime
from pydantic import BaseModel
from ..models.card import MTGCard


class CacheEntry(BaseModel):
    """Single cache entry with metadata"""
    card: MTGCard
    cached_at: datetime
    access_count: int = 0
    last_accessed: datetime

    class Config:
        arbitrary_types_allowed = True


class CAGCache:
    """
    Cache-Augmented Generation Cache with LRU eviction

    This cache stores MTG cards that are preloaded into the LLM context.
    Uses OrderedDict for efficient LRU implementation.
    """

    def __init__(self, max_size: int = 2000):
        """
        Initialize CAG cache

        Args:
            max_size: Maximum number of cards to keep in cache (default: 200)
        """
        # Private: OrderedDict for efficient LRU (maintains insertion order)
        self.__cache: OrderedDictType[str, CacheEntry] = OrderedDict()

        # Public: Configuration
        self.max_size = max_size

        # Public: Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, card_name: str) -> Optional[MTGCard]:
        """
        Get card from cache (Public API)

        Args:
            card_name: Name of the card to retrieve

        Returns:
            MTGCard if found, None otherwise
        """
        key = self._make_key(card_name)

        if key in self.__cache:
            # Cache hit - move to end (most recently used)
            self.__cache.move_to_end(key)
            entry = self.__cache[key]

            # Update access metadata
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            self.hits += 1
            return entry.card

        # Cache miss
        self.misses += 1
        return None

    def put(self, card: MTGCard) -> None:
        """
        Add card to cache (Public API)

        If cache is full, evicts least recently used card.

        Args:
            card: MTGCard object to cache
        """
        key = self._make_key(card.name)

        # If card already exists, update it and move to end
        if key in self.__cache:
            del self.__cache[key]

        # Check if we need to evict
        if len(self.__cache) >= self.max_size:
            self._evict_lru()

        # Add new entry at end (most recently used)
        entry = CacheEntry(
            card=card,
            cached_at=datetime.now(),
            last_accessed=datetime.now()
        )
        self.__cache[key] = entry

    def put_batch(self, cards: list[MTGCard]) -> None:
        """
        Add multiple cards to cache (Public API)

        Args:
            cards: List of MTGCard objects to cache
        """
        for card in cards:
            self.put(card)

    def contains(self, card_name: str) -> bool:
        """
        Check if card is in cache without updating access (Public API)

        Args:
            card_name: Name of the card to check

        Returns:
            True if card is in cache, False otherwise
        """
        key = self._make_key(card_name)
        return key in self.__cache

    def get_all_cards(self) -> list[MTGCard]:
        """
        Get all cards currently in cache (Public API)

        Returns:
            List of all cached MTGCard objects
        """
        return [entry.card for entry in self.__cache.values()]

    def get_context_string(self) -> str:
        """
        Generate context string for LLM preloading (Public API)

        Returns:
            Formatted string of all cached cards for LLM context
        """
        cards = self.get_all_cards()

        if not cards:
            return "No cards preloaded in CAG cache."

        context_parts = [f"=== Preloaded MTG Cards ({len(cards)} cards) ===\n"]

        for card in cards:
            card_info = [
                f"Card: {card.name}",
                f"  Mana Cost: {card.mana_cost or 'N/A'}",
                f"  CMC: {card.cmc}",
                f"  Type: {card.type_line}",
                f"  Text: {card.oracle_text or 'N/A'}",
            ]

            if card.power and card.toughness:
                card_info.append(f"  P/T: {card.power}/{card.toughness}")

            if card.loyalty:
                card_info.append(f"  Loyalty: {card.loyalty}")

            context_parts.append("\n".join(card_info))
            context_parts.append("")  # Blank line between cards

        return "\n".join(context_parts)

    def clear(self) -> None:
        """Clear all entries from cache (Public API)"""
        self.__cache.clear()
        print("Cache cleared")
        
    def preload_format_cards(self, cards: List[MTGCard]) -> None:
        """
        Preload a list of format-legal cards into cache
        
        Args:
            cards: List of MTGCard objects to preload
        """
        self.clear()  # Clear existing cache
        for card in cards:
            self.put(card)
        print(f"✅ Preloaded {len(cards)} cards into cache")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics (Public API)

        Returns:
            Dictionary with cache statistics
        """
        total_accesses = self.hits + self.misses
        hit_rate = (self.hits / total_accesses * 100) if total_accesses > 0 else 0.0

        return {
            "size": len(self.__cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{hit_rate:.2f}%",
            "utilization": f"{len(self.__cache) / self.max_size * 100:.1f}%"
        }

    def get_lru_order(self) -> list[str]:
        """
        Get cards in LRU order (least recently used first) (Public API)

        Useful for debugging and monitoring.

        Returns:
            List of card names in LRU order
        """
        return [
            self.__cache[key].card.name
            for key in self.__cache.keys()
        ]

    def _make_key(self, card_name: str) -> str:
        """
        Generate cache key from card name (Protected - internal helper)

        Args:
            card_name: Card name

        Returns:
            Normalized cache key (lowercase)
        """
        return card_name.lower().strip()

    def _evict_lru(self) -> None:
        """
        Evict least recently used entry (Protected - internal logic)

        OrderedDict maintains insertion order, and we move accessed items
        to the end, so the first item is always the LRU.
        """
        if self.__cache:
            # Remove first item (least recently used)
            evicted_key, evicted_entry = self.__cache.popitem(last=False)
            self.evictions += 1
            print(f"[CAG Cache] Evicted LRU card: {evicted_entry.card.name}")
