"""
Core data models for V3 architecture.

Reuses card models from v2 and adds new models for
deck building, quality metrics, and iteration tracking.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Reuse from v2
class CardColor(str, Enum):
    WHITE = "W"
    BLUE = "U"
    BLACK = "B"
    RED = "R"
    GREEN = "G"
    COLORLESS = "C"


class CardType(str, Enum):
    CREATURE = "Creature"
    INSTANT = "Instant"
    SORCERY = "Sorcery"
    ENCHANTMENT = "Enchantment"
    ARTIFACT = "Artifact"
    PLANESWALKER = "Planeswalker"
    LAND = "Land"
    BATTLE = "Battle"
    KINDRED = "Kindred"


class MTGCard(BaseModel):
    """Model representing a Magic: The Gathering card"""
    id: str = Field(..., description="Unique card identifier")
    name: str = Field(..., description="Card name")
    mana_cost: Optional[str] = Field(None, description="Mana cost (e.g., '{2}{U}{U}')")
    cmc: float = Field(0.0, description="Converted mana cost")
    colors: List[str] = Field(default_factory=list)
    color_identity: List[str] = Field(default_factory=list)
    type_line: str = Field(..., description="Full type line")
    types: List[str] = Field(default_factory=list)
    subtypes: List[str] = Field(default_factory=list)
    oracle_text: Optional[str] = Field(None, description="Rules text")
    power: Optional[str] = Field(None, description="Creature power")
    toughness: Optional[str] = Field(None, description="Creature toughness")
    loyalty: Optional[str] = Field(None, description="Planeswalker loyalty")
    set_code: str = Field(default="", description="Set code")
    rarity: str = Field(default="", description="Card rarity")
    legalities: Dict[str, str] = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


# New V3 Models

class DeckCard(BaseModel):
    """A card with quantity in a deck."""
    card: MTGCard
    quantity: int = Field(..., ge=1, description="Number of copies in deck")


class Deck(BaseModel):
    """A Magic: The Gathering deck."""
    cards: List[DeckCard] = Field(default_factory=list)
    format: str = Field(..., description="Format (Standard, Modern, Commander, etc.)")
    archetype: Optional[str] = Field(None, description="Deck archetype (Aggro, Control, etc.)")
    colors: List[str] = Field(default_factory=list, description="Deck color identity")
    total_cards: int = Field(0, description="Total number of cards")
    
    def calculate_totals(self) -> None:
        """Calculate total cards and update deck metadata."""
        self.total_cards = sum(dc.quantity for dc in self.cards)
        
        # Extract color identity from cards
        color_set = set()
        for deck_card in self.cards:
            color_set.update(deck_card.card.color_identity)
        self.colors = sorted(list(color_set))
    
    def get_lands(self) -> List[DeckCard]:
        """Get all land cards in the deck."""
        return [dc for dc in self.cards if "Land" in dc.card.types]
    
    def get_nonlands(self) -> List[DeckCard]:
        """Get all non-land cards in the deck."""
        return [dc for dc in self.cards if "Land" not in dc.card.types]
    
    def get_cards_by_cmc(self, cmc: int) -> List[DeckCard]:
        """Get all cards with specific CMC."""
        return [dc for dc in self.cards if dc.card.cmc == cmc]


class DeckQualityMetrics(BaseModel):
    """Quality metrics for deck analysis."""
    mana_curve_score: float = Field(..., ge=0.0, le=1.0, description="Mana curve quality (0-1)")
    land_ratio_score: float = Field(..., ge=0.0, le=1.0, description="Land ratio quality (0-1)")
    synergy_score: float = Field(..., ge=0.0, le=1.0, description="Card synergy quality (0-1)")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Deck consistency (0-1)")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score (0-1)")
    issues: List[str] = Field(default_factory=list, description="Identified issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    
    def calculate_overall(self) -> None:
        """Calculate overall score as weighted average."""
        self.overall_score = (
            self.mana_curve_score * 0.3 +
            self.land_ratio_score * 0.25 +
            self.synergy_score * 0.25 +
            self.consistency_score * 0.2
        )


class IterationRecord(BaseModel):
    """Record of a single iteration in the FSM."""
    iteration: int = Field(..., description="Iteration number")
    deck_snapshot: Deck = Field(..., description="Deck state at this iteration")
    quality_metrics: DeckQualityMetrics = Field(..., description="Quality metrics for this iteration")
    improvements_applied: List[str] = Field(default_factory=list, description="Improvements applied this iteration")
    timestamp: datetime = Field(default_factory=datetime.now)


class IterationState(BaseModel):
    """Tracks iteration state across FSM execution."""
    iteration_count: int = Field(0, description="Current iteration number")
    max_iterations: int = Field(5, description="Maximum allowed iterations")
    quality_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Quality threshold to meet")
    history: List[IterationRecord] = Field(default_factory=list, description="Iteration history")
    
    def should_continue(self, current_quality: float) -> bool:
        """Determine if iteration should continue."""
        return (
            self.iteration_count < self.max_iterations and
            current_quality < self.quality_threshold
        )
    
    def add_record(self, record: IterationRecord) -> None:
        """Add an iteration record to history."""
        self.history.append(record)
        self.iteration_count = record.iteration


class DeckBuildRequest(BaseModel):
    """User request for deck building."""
    format: str = Field(..., description="Format (Standard, Modern, Commander, etc.)")
    colors: List[str] = Field(..., description="Deck colors (W, U, B, R, G)")
    archetype: Optional[str] = Field(None, description="Deck archetype (Aggro, Control, Midrange, Combo)")
    strategy: Optional[str] = Field(None, description="Free-form strategy description")
    budget: Optional[float] = Field(None, description="Budget constraint (not implemented yet)")
    quality_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Quality threshold (0-1)")
    max_iterations: int = Field(5, ge=1, le=10, description="Maximum iterations")
    deck_size: int = Field(60, description="Target deck size")


class CardSearchFilters(BaseModel):
    """Filters for card search queries."""
    colors: Optional[List[str]] = None
    types: Optional[List[str]] = None
    cmc_min: Optional[float] = None
    cmc_max: Optional[float] = None
    rarity: Optional[str] = None
    format_legal: Optional[str] = None
    text_query: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
