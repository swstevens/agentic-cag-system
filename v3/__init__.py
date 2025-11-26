"""V3 Architecture - FSM-based MTG Deck Building System with CAG."""

from .fsm.orchestrator import FSMOrchestrator
from .fsm.states import (
    ParseRequestNode, 
    BuildInitialDeckNode, 
    RefineDeckNode, 
    VerifyQualityNode, 
    StateData
)
from .models.deck import (
    MTGCard,
    Deck,
    DeckCard,
    DeckBuildRequest,
    DeckQualityMetrics,
    IterationState,
)
from .database.database_service import DatabaseService
from .database.card_repository import CardRepository
from .services.deck_builder_service import DeckBuilderService
from .services.quality_verifier_service import QualityVerifierService
from .caching import ICache, CacheStats, LRUCache

__all__ = [
    # FSM
    "FSMOrchestrator",
    "ParseRequestNode",
    "BuildInitialDeckNode",
    "RefineDeckNode",
    "VerifyQualityNode",
    "StateData",
    # Models
    "MTGCard",
    "Deck",
    "DeckCard",
    "DeckBuildRequest",
    "DeckQualityMetrics",
    "IterationState",
    # Database
    "DatabaseService",
    "CardRepository",
    # Services
    "DeckBuilderService",
    "QualityVerifierService",
    # Caching (CAG)
    "ICache",
    "CacheStats",
    "LRUCache",
]
