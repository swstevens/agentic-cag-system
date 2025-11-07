from .card import MTGCard, CardCollection, CardColor, CardType
from .card_orm import CardORM, Base
from .converters import orm_to_pydantic, pydantic_to_orm, orm_list_to_pydantic, pydantic_list_to_orm
from .query import UserQuery, QueryIntent, QueryType
from .agent import AgentState, AgentType, ReasoningStep, ReasoningChain
from .response import AgentResponse, FusedResponse
from .deck_analysis import (
    DeckAnalysisResult,
    ManaCurveAnalysis,
    LandRatioAnalysis,
    SynergyDetection,
    WinConditionAnalysis,
    ArchetypeConsistency,
    DeckStrengths,
    DeckWeaknesses,
    CurveQuality,
    LandRatioQuality,
)
from .requests import (
    AgentRequest,
    SchedulingRequest,
    KnowledgeRequest,
    ReasoningRequest,
    AnalysisRequest,
    ValidationType,
    DeckArchetype,
)
from .responses import (
    SchedulingResponse,
    KnowledgeResponse,
    ReasoningResponse,
    AnalysisResponse,
)

__all__ = [
    "MTGCard",
    "CardCollection",
    "CardColor",
    "CardType",
    "CardORM",
    "Base",
    "orm_to_pydantic",
    "pydantic_to_orm",
    "orm_list_to_pydantic",
    "pydantic_list_to_orm",
    "UserQuery",
    "QueryIntent",
    "QueryType",
    "AgentState",
    "AgentType",
    "ReasoningStep",
    "ReasoningChain",
    "AgentResponse",
    "FusedResponse",
    "DeckAnalysisResult",
    "ManaCurveAnalysis",
    "LandRatioAnalysis",
    "SynergyDetection",
    "WinConditionAnalysis",
    "ArchetypeConsistency",
    "DeckStrengths",
    "DeckWeaknesses",
    "CurveQuality",
    "LandRatioQuality",
    # New typed request/response models
    "AgentRequest",
    "SchedulingRequest",
    "KnowledgeRequest",
    "ReasoningRequest",
    "AnalysisRequest",
    "ValidationType",
    "DeckArchetype",
    "SchedulingResponse",
    "KnowledgeResponse",
    "ReasoningResponse",
    "AnalysisResponse",
]
