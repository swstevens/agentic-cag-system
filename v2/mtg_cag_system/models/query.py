from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class QueryType(str, Enum):
    DECK_BUILDING = "deck_building"
    CARD_SEARCH = "card_search"
    RULES_QUESTION = "rules_question"
    CARD_INTERACTION = "card_interaction"
    FORMAT_LEGALITY = "format_legality"
    COMBO_QUERY = "combo_query"


class QueryIntent(BaseModel):
    """Parsed user intent"""
    primary_intent: QueryType
    entities: List[str] = Field(default_factory=list, description="Card names, mechanics, etc.")
    constraints: Dict[str, Any] = Field(default_factory=dict)
    requires_symbolic_reasoning: bool = False
    requires_knowledge_fetch: bool = True
    temporal_context: Optional[str] = None


class UserQuery(BaseModel):
    """Incoming user query"""
    query_id: str = Field(default_factory=lambda: f"q_{datetime.now().timestamp()}")
    session_id: str
    query_text: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    # Parsed information (filled by router)
    intent: Optional[QueryIntent] = None
