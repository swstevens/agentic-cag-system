"""
Repository interface - abstracts card data access.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from ..models.card import MTGCard, CardColor, CardType


class SearchCriteria(BaseModel):
    """Type-safe search criteria for card queries"""
    colors: Optional[List[CardColor]] = None
    types: Optional[List[CardType]] = None
    format: Optional[str] = None
    cmc_min: Optional[float] = None
    cmc_max: Optional[float] = None
    text_query: Optional[str] = None
    rarity: Optional[str] = None
    limit: int = 100


class ICardRepository(ABC):
    """
    Repository interface for card data access.

    Follows Repository Pattern - abstracts data source (cache + database)
    behind a simple interface. Makes testing easier with mock repositories.
    """

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Get a card by exact name.

        Args:
            name: Card name

        Returns:
            MTGCard if found, None otherwise
        """
        pass

    @abstractmethod
    def search(self, criteria: SearchCriteria) -> List[MTGCard]:
        """
        Search for cards matching criteria.

        Args:
            criteria: SearchCriteria with filters

        Returns:
            List of matching MTGCard objects
        """
        pass

    @abstractmethod
    def fuzzy_search(self, name: str, limit: int = 10) -> List[MTGCard]:
        """
        Fuzzy search for cards by name (handles typos).

        Args:
            name: Partial or misspelled card name
            limit: Maximum results to return

        Returns:
            List of closest matching MTGCard objects
        """
        pass
