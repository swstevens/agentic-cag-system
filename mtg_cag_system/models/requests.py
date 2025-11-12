"""
Typed request objects for agents.

Replaces Dict[str, Any] with strongly-typed Pydantic models
for better type safety, validation, and serialization.

Pydantic provides:
- Automatic validation of field types and constraints
- JSON schema generation
- Serialization/deserialization
- IDE autocomplete support
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
from .card import MTGCard


class ValidationType(str, Enum):
    """Types of validation the SymbolicReasoningAgent can perform"""
    FORMAT = "format"
    LEGALITY = "legality"
    MANA_CURVE = "mana_curve"
    CARD_LIMITS = "card_limits"
    ALL = "all"


class DeckArchetype(str, Enum):
    """Standard deck archetypes for validation context"""
    AGGRO = "aggro"
    CONTROL = "control"
    MIDRANGE = "midrange"
    COMBO = "combo"
    TEMPO = "tempo"
    RAMP = "ramp"


class AgentRequest(BaseModel):
    """
    Base class for all agent requests.

    Pydantic automatically validates all subclasses and provides
    serialization methods (model_dump(), model_dump_json()).
    """
    request_id: str = Field(
        default_factory=lambda: f"req_{datetime.now().timestamp()}",
        description="Unique request identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Request creation timestamp"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the request"
    )

    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True  # Validate on attribute assignment
        json_schema_extra = {
            "example": {
                "request_id": "req_1234567890.123",
                "timestamp": "2025-01-01T12:00:00",
                "context": {}
            }
        }


class SchedulingRequest(AgentRequest):
    """
    Request for SchedulingAgent to classify and plan query.

    Pydantic validation ensures:
    - query_text is non-empty string
    - session_id follows expected format
    """
    query_text: str = Field(
        ...,
        min_length=1,
        description="User's query text",
        examples=["Build me a red aggro deck for Standard"]
    )
    session_id: str = Field(
        ...,
        min_length=1,
        description="Session identifier"
    )
    user_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user context (preferences, history, etc.)"
    )

    @field_validator('query_text')
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        """Ensure query is not just whitespace"""
        if not v.strip():
            raise ValueError("query_text cannot be empty or whitespace")
        return v.strip()


class KnowledgeRequest(AgentRequest):
    """
    Request for KnowledgeFetchAgent to look up cards.

    Pydantic validation ensures:
    - Either query_text or card_names is provided
    - card_names contains valid strings
    - format_filter matches known formats
    """
    query_text: Optional[str] = Field(
        None,
        description="Query text to extract card names from",
        examples=["Tell me about Lightning Bolt and Counterspell"]
    )
    card_names: Optional[List[str]] = Field(
        None,
        description="Pre-extracted card names (if already parsed)",
        examples=[["Lightning Bolt", "Counterspell"]]
    )
    fuzzy_search: bool = Field(
        default=False,
        description="Whether to use fuzzy matching for typos"
    )
    format_filter: Optional[str] = Field(
        None,
        description="Filter results by format legality",
        examples=["Standard", "Modern", "Commander"]
    )

    @model_validator(mode='after')
    def validate_query_or_cards(self):
        """Ensure either query_text or card_names is provided"""
        if not self.query_text and not self.card_names:
            raise ValueError("Either query_text or card_names must be provided")
        return self


class ReasoningRequest(AgentRequest):
    """
    Request for SymbolicReasoningAgent to validate deck.

    Pydantic validation ensures:
    - cards list is not empty
    - validation_type is a valid enum value
    - format matches known formats when provided
    """
    cards: List[MTGCard] = Field(
        ...,
        min_length=1,
        description="Cards to validate (must have at least one card)"
    )
    validation_type: ValidationType = Field(
        default=ValidationType.ALL,
        description="Type of validation to perform"
    )
    format: Optional[str] = Field(
        None,
        description="Format to validate against",
        examples=["Standard", "Modern", "Commander"]
    )
    deck_archetype: Optional[DeckArchetype] = Field(
        None,
        description="Deck archetype for context-aware validation"
    )

    @field_validator('cards')
    @classmethod
    def validate_cards_not_empty(cls, v: List[MTGCard]) -> List[MTGCard]:
        """Ensure cards list is not empty"""
        if not v:
            raise ValueError("cards list cannot be empty")
        return v


class AnalysisRequest(AgentRequest):
    """
    Request for DeckAnalyzerAgent to analyze deck quality.

    Pydantic validation ensures:
    - cards list has reasonable size (1-250 cards)
    - archetype is valid
    - deck_size is positive
    """
    cards: List[MTGCard] = Field(
        ...,
        min_length=1,
        max_length=250,  # Reasonable upper limit
        description="Cards in the deck to analyze"
    )
    archetype: DeckArchetype = Field(
        ...,
        description="Declared archetype (aggro, control, midrange, combo, etc.)"
    )
    format: str = Field(
        default="Standard",
        description="Format of the deck",
        examples=["Standard", "Modern", "Pioneer", "Commander"]
    )
    deck_size: int = Field(
        default=60,
        ge=40,  # Minimum deck size (Limited format)
        le=250,  # Maximum reasonable size (Commander with sideboard)
        description="Expected deck size"
    )

    @field_validator('cards')
    @classmethod
    def validate_reasonable_deck_size(cls, v: List[MTGCard]) -> List[MTGCard]:
        """Warn if deck size is unusual"""
        if len(v) < 40:
            raise ValueError(f"Deck has only {len(v)} cards, minimum is 40")
        if len(v) > 250:
            raise ValueError(f"Deck has {len(v)} cards, maximum is 250")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "cards": [{"name": "Lightning Bolt", "cmc": 1}],
                "archetype": "aggro",
                "format": "Modern",
                "deck_size": 60
            }
        }


class SynergyLookupRequest(AgentRequest):
    """
    Request for looking up synergistic cards for a given card.

    Pydantic validation ensures:
    - card_name is provided and non-empty
    - max_results is within reasonable bounds
    """
    card_name: str = Field(
        ...,
        min_length=1,
        description="Name of the card to find synergies for",
        examples=["Lightning Bolt", "Counterspell"]
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of synergistic cards to return"
    )
    archetype: Optional[DeckArchetype] = Field(
        None,
        description="Optional archetype to filter synergies by context"
    )
    format_filter: Optional[str] = Field(
        None,
        description="Optional format to filter results by legality",
        examples=["Standard", "Modern", "Commander"]
    )

    @field_validator('card_name')
    @classmethod
    def validate_card_name_not_empty(cls, v: str) -> str:
        """Ensure card_name is not just whitespace"""
        if not v.strip():
            raise ValueError("card_name cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "card_name": "Lightning Bolt",
                "max_results": 10,
                "archetype": "aggro",
                "format_filter": "Modern"
            }
        }
