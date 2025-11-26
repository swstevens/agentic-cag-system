from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


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
    KINDRED = "Kindred"  # Formerly "Tribal"


class MTGCard(BaseModel):
    """Model representing a Magic: The Gathering card"""
    id: str = Field(..., description="Unique card identifier")
    name: str = Field(..., description="Card name")
    mana_cost: Optional[str] = Field(None, description="Mana cost (e.g., '{2}{U}{U}')")
    cmc: float = Field(0.0, description="Converted mana cost")
    colors: List[CardColor] = Field(default_factory=list)
    color_identity: List[CardColor] = Field(default_factory=list)
    type_line: str = Field(..., description="Full type line")
    types: List[str] = Field(default_factory=list)  # Changed from List[CardType] to List[str] for flexibility
    subtypes: List[str] = Field(default_factory=list)
    oracle_text: Optional[str] = Field(None, description="Rules text")
    power: Optional[str] = Field(None, description="Creature power")
    toughness: Optional[str] = Field(None, description="Creature toughness")
    loyalty: Optional[str] = Field(None, description="Planeswalker loyalty")
    set_code: str = Field(default="", description="Set code")  # Made optional with default for AtomicCards
    rarity: str = Field(default="", description="Card rarity")  # Made optional with default for AtomicCards
    legalities: Dict[str, str] = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class CardCollection(BaseModel):
    """Collection of MTG cards for CAG preloading"""
    cards: List[MTGCard]
    total_count: int
    format_filter: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    cached_at: datetime = Field(default_factory=datetime.now)

    def to_context_string(self) -> str:
        """Convert collection to string for CAG context window"""
        context_parts = []
        for card in self.cards:
            card_str = (
                f"Card: {card.name}\n"
                f"Cost: {card.mana_cost or 'N/A'}\n"
                f"Type: {card.type_line}\n"
                f"Text: {card.oracle_text or 'N/A'}\n"
            )
            if card.power and card.toughness:
                card_str += f"P/T: {card.power}/{card.toughness}\n"
            context_parts.append(card_str)
        return "\n---\n".join(context_parts)
