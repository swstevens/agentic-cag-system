"""
Analyzer interface - defines contract for deck analysis strategies.
"""

from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from ..models.card import MTGCard
from ..models.deck_analysis import DeckAnalysisResult


class AnalysisContext(BaseModel):
    """Context information for deck analysis"""
    archetype: str
    format: str = "Standard"
    target_deck_size: int = 60
    metadata: dict = {}


class IAnalyzer(ABC):
    """
    Interface for deck analyzers.

    Enables Strategy Pattern - different analysis approaches
    (rule-based, LLM-based, composite) can be swapped at runtime.
    """

    @abstractmethod
    async def analyze(
        self,
        cards: List[MTGCard],
        context: AnalysisContext
    ) -> DeckAnalysisResult:
        """
        Analyze a deck and return structured results.

        Args:
            cards: List of cards in the deck
            context: Analysis context (archetype, format, etc.)

        Returns:
            DeckAnalysisResult with comprehensive analysis
        """
        pass
