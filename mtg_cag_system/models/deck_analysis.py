"""
Pydantic models for deck analysis structured outputs
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from enum import Enum


class CurveQuality(str, Enum):
    """Mana curve quality assessment"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    TOO_LOW = "too_low"
    TOO_HIGH = "too_high"
    POOR = "poor"


class LandRatioQuality(str, Enum):
    """Land ratio quality assessment"""
    EXCELLENT = "excellent"
    GOOD = "good"
    TOO_FEW = "too_few_lands"
    TOO_MANY = "too_many_lands"


class ManaCurveAnalysis(BaseModel):
    """Structured mana curve analysis"""
    average_cmc: float = Field(description="Average converted mana cost of non-land cards")
    curve_quality: CurveQuality = Field(description="Overall curve quality assessment")
    curve_distribution: Dict[str, int] = Field(
        description="Distribution of cards by CMC (e.g., {'0': 2, '1': 8, '2': 12, ...})"
    )
    focus_percentage: float = Field(
        description="Percentage of cards in the archetype's focus CMC range"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Specific recommendations for improving the mana curve"
    )


class LandRatioAnalysis(BaseModel):
    """Structured land ratio analysis"""
    land_count: int = Field(description="Total number of lands in the deck")
    land_percentage: float = Field(description="Percentage of deck that is lands")
    ratio_quality: LandRatioQuality = Field(description="Quality assessment of land ratio")
    recommended_land_count: Optional[int] = Field(
        None,
        description="Recommended number of lands for this deck"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Specific recommendations for land ratio"
    )


class SynergyDetection(BaseModel):
    """Detected synergy or combo in the deck"""
    name: str = Field(description="Name or description of the synergy")
    card_names: List[str] = Field(description="Cards involved in this synergy")
    description: str = Field(description="Explanation of how the synergy works")
    strength: Literal["weak", "moderate", "strong", "game-winning"] = Field(
        description="Assessment of synergy strength"
    )


class WinConditionAnalysis(BaseModel):
    """Analysis of deck's win conditions"""
    primary_win_conditions: List[str] = Field(
        description="Main ways this deck wins the game"
    )
    backup_win_conditions: List[str] = Field(
        default_factory=list,
        description="Alternative ways to win if primary fails"
    )
    win_condition_quality: Literal["none", "weak", "acceptable", "good", "excellent"] = Field(
        description="Overall quality of win conditions"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improving win conditions"
    )


class ArchetypeConsistency(BaseModel):
    """Analysis of how well the deck follows its intended archetype"""
    declared_archetype: str = Field(description="The archetype the deck is trying to be")
    consistency_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How consistently the deck follows its archetype (0-1)"
    )
    archetype_strengths: List[str] = Field(
        description="Aspects where the deck excels for this archetype"
    )
    archetype_weaknesses: List[str] = Field(
        description="Aspects where the deck deviates or fails for this archetype"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for better archetype consistency"
    )


class DeckStrengths(BaseModel):
    """Overall deck strengths"""
    strong_matchups: List[str] = Field(
        default_factory=list,
        description="Types of decks this deck should beat"
    )
    key_cards: List[str] = Field(
        description="Most important cards in the deck"
    )
    unique_advantages: List[str] = Field(
        description="What this deck does better than others"
    )


class DeckWeaknesses(BaseModel):
    """Overall deck weaknesses"""
    weak_matchups: List[str] = Field(
        default_factory=list,
        description="Types of decks this deck struggles against"
    )
    vulnerabilities: List[str] = Field(
        description="Specific weaknesses or gaps in the deck"
    )
    missing_elements: List[str] = Field(
        default_factory=list,
        description="Important cards or effects the deck is missing"
    )


class DeckAnalysisResult(BaseModel):
    """Complete structured deck analysis from the DeckAnalyzerAgent"""

    # Overall assessment
    overall_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall deck quality score (0-100)"
    )
    overall_assessment: str = Field(
        description="High-level summary of the deck's quality"
    )

    # Detailed analyses
    mana_curve: ManaCurveAnalysis
    land_ratio: LandRatioAnalysis
    synergies: List[SynergyDetection] = Field(
        default_factory=list,
        description="Detected synergies and combos"
    )
    win_conditions: WinConditionAnalysis
    archetype_consistency: ArchetypeConsistency

    # Strengths and weaknesses
    strengths: DeckStrengths
    weaknesses: DeckWeaknesses

    # Action items
    priority_improvements: List[str] = Field(
        description="Top 3-5 improvements to make, in priority order"
    )

    # Metadata
    is_competitive: bool = Field(
        description="Whether this deck is competitive for its format"
    )
    needs_major_changes: bool = Field(
        description="Whether the deck needs significant restructuring"
    )
