"""
Typed response objects for agents.

Leverages Pydantic for automatic validation, serialization, and type safety.
These replace the generic data dicts in AgentResponse with strongly-typed models.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from .card import MTGCard
from .query import QueryType
from .deck_analysis import DeckAnalysisResult


class SchedulingResponse(BaseModel):
    """
    Response from SchedulingAgent with query classification and planning.

    Pydantic ensures:
    - query_type is valid QueryType enum
    - All required fields are present
    - Nested structures are validated
    """
    query_type: QueryType = Field(
        ...,
        description="Classified query type"
    )
    extracted_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted requirements (format, colors, strategy, etc.)"
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Recommended next steps for query processing"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in classification (0.0-1.0)"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "query_type": "deck_building",
                "extracted_requirements": {
                    "format": "Modern",
                    "colors": ["Red"],
                    "strategy": "aggro"
                },
                "next_steps": ["fetch_cards", "validate_deck"],
                "confidence": 0.95
            }
        }


class KnowledgeResponse(BaseModel):
    """
    Response from KnowledgeFetchAgent with card lookup results.

    Pydantic validates:
    - All cards are valid MTGCard objects
    - Cache statistics are non-negative integers
    """
    cards: List[MTGCard] = Field(
        default_factory=list,
        description="Found cards"
    )
    extracted_card_names: List[str] = Field(
        default_factory=list,
        description="Card names extracted from query by LLM"
    )
    cache_hits: int = Field(
        default=0,
        ge=0,
        description="Number of cards found in cache"
    )
    db_hits: int = Field(
        default=0,
        ge=0,
        description="Number of cards found in database"
    )
    not_found: List[str] = Field(
        default_factory=list,
        description="Card names that couldn't be found"
    )
    answer: str = Field(
        default="",
        description="Natural language answer about the cards"
    )

    @property
    def total_hits(self) -> int:
        """Total cards found"""
        return len(self.cards)

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate (0.0-1.0)"""
        total = self.cache_hits + self.db_hits
        return self.cache_hits / total if total > 0 else 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "cards": [{"name": "Lightning Bolt", "cmc": 1}],
                "extracted_card_names": ["Lightning Bolt", "Counterspell"],
                "cache_hits": 1,
                "db_hits": 1,
                "not_found": [],
                "answer": "Lightning Bolt is a powerful red instant that deals 3 damage."
            }
        }


class ReasoningResponse(BaseModel):
    """
    Response from SymbolicReasoningAgent with validation results.

    Pydantic validates:
    - is_valid is boolean
    - All nested validation results are properly structured
    """
    is_valid: bool = Field(
        ...,
        description="Overall validation result"
    )
    validations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Individual validation results"
    )
    reasoning: List[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning for validation decisions"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for improving the deck"
    )
    invalid_cards: List[str] = Field(
        default_factory=list,
        description="Names of cards that failed validation"
    )

    @property
    def has_errors(self) -> bool:
        """Check if any validation failed"""
        return not self.is_valid or len(self.invalid_cards) > 0

    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "validations": [
                    {"validator": "format", "passed": True, "message": "All cards legal in Modern"}
                ],
                "reasoning": ["Checked format legality", "All cards passed"],
                "suggestions": ["Consider adding more removal"],
                "invalid_cards": []
            }
        }


class AnalysisResponse(BaseModel):
    """
    Response from DeckAnalyzerAgent with comprehensive analysis.

    Pydantic validates:
    - analysis_result is a valid DeckAnalysisResult with all nested validations
    - execution_time is non-negative
    """
    analysis_result: DeckAnalysisResult = Field(
        ...,
        description="Comprehensive deck analysis"
    )
    execution_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken for analysis in seconds"
    )

    @property
    def is_competitive(self) -> bool:
        """Check if deck is competitive"""
        return self.analysis_result.is_competitive

    @property
    def needs_major_changes(self) -> bool:
        """Check if deck needs major restructuring"""
        return self.analysis_result.needs_major_changes

    @property
    def overall_score(self) -> float:
        """Get overall deck quality score (0-100)"""
        return self.analysis_result.overall_score

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_result": {
                    "overall_score": 78.5,
                    "overall_assessment": "Solid midrange deck with good mana curve",
                    "is_competitive": True,
                    "needs_major_changes": False
                },
                "execution_time": 2.3
            }
        }


class SynergyResult(BaseModel):
    """Individual synergy result for a card"""
    name: str = Field(
        ...,
        description="Card name"
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0.0-1.0)"
    )
    card_id: Optional[str] = Field(
        None,
        description="Card ID from database"
    )


class SynergyLookupResponse(BaseModel):
    """
    Response from synergy lookup with list of synergistic cards.

    Pydantic validates:
    - source_card is provided
    - synergies list contains valid SynergyResult objects
    """
    source_card: str = Field(
        ...,
        description="The card that was queried for synergies"
    )
    synergies: List[SynergyResult] = Field(
        default_factory=list,
        description="List of synergistic cards with similarity scores"
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total number of synergies found"
    )
    execution_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken for synergy lookup in seconds"
    )

    @property
    def top_synergies(self) -> List[SynergyResult]:
        """Get synergies sorted by similarity score (highest first)"""
        return sorted(self.synergies, key=lambda s: s.similarity_score, reverse=True)

    class Config:
        json_schema_extra = {
            "example": {
                "source_card": "Lightning Bolt",
                "synergies": [
                    {
                        "name": "Chain Lightning",
                        "similarity_score": 0.95,
                        "card_id": "card_123"
                    },
                    {
                        "name": "Shock",
                        "similarity_score": 0.87,
                        "card_id": "card_456"
                    }
                ],
                "total_found": 2,
                "execution_time": 0.15
            }
        }
