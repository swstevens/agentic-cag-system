"""
Knowledge Response Models

Structured response schemas for the KnowledgeFetchAgent
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from .card import MTGCard


class CardAnalysis(BaseModel):
    """Structured analysis of a single card"""
    card: MTGCard = Field(..., description="The card being analyzed")
    summary: str = Field(..., description="Brief 1-2 sentence summary of the card")
    strengths: List[str] = Field(default_factory=list, description="Card's strengths and advantages")
    weaknesses: List[str] = Field(default_factory=list, description="Card's weaknesses or limitations")
    synergies: List[str] = Field(default_factory=list, description="Cards or strategies that work well with this card")
    deck_recommendations: List[str] = Field(default_factory=list, description="Deck archetypes where this card excels")


class KnowledgeResponse(BaseModel):
    """Structured response from KnowledgeFetchAgent"""
    query_summary: str = Field(..., description="Summary of what the user asked about")
    cards_found: List[MTGCard] = Field(default_factory=list, description="All cards relevant to the query")
    primary_answer: str = Field(..., description="Direct answer to the user's question")
    card_analyses: List[CardAnalysis] = Field(default_factory=list, description="Detailed analysis of each card")
    interactions: Optional[str] = Field(None, description="How the cards interact with each other (if multiple cards)")
    recommended_cards: List[str] = Field(default_factory=list, description="Additional cards that might be relevant")

    class Config:
        json_schema_extra = {
            "example": {
                "query_summary": "User asked about Lightning Bolt",
                "cards_found": [],
                "primary_answer": "Lightning Bolt is a classic red instant that deals 3 damage for 1 mana.",
                "card_analyses": [],
                "interactions": None,
                "recommended_cards": ["Lava Spike", "Boros Charm"]
            }
        }
