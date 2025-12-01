"""
Quality Verifier Service for V3 architecture.

Analyzes deck quality across multiple dimensions and
provides improvement suggestions for iteration.
"""

from typing import List, Dict, Optional
from ..models.deck import Deck, DeckQualityMetrics, DeckCard
from .llm_service import LLMService


class QualityVerifierService:
    """
    Service for verifying deck quality.
    
    Analyzes mana curve, land ratio, synergies, and consistency
    to determine if a deck meets quality thresholds.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize quality verifier.
        
        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self.llm_service = llm_service
    
    async def verify_deck(self, deck: Deck) -> DeckQualityMetrics:
        """
        Verify deck quality across all dimensions.
        
        Args:
            deck: Deck to verify
            
        Returns:
            Quality metrics with scores and suggestions
        """
        metrics = DeckQualityMetrics(
            mana_curve_score=self._analyze_mana_curve(deck),
            land_ratio_score=self._analyze_land_ratio(deck),
            synergy_score=self._analyze_synergies(deck),
            consistency_score=self._analyze_consistency(deck),
            overall_score=0.0,
            issues=[],
            suggestions=[],
            improvement_plan=None
        )
        
        # Check deck size
        target_size = 60 # Standard
        if deck.total_cards != target_size:
            metrics.issues.append(f"Deck size is {deck.total_cards}, expected {target_size}")
            # Heavy penalty for wrong deck size
            metrics.overall_score = 0.0
        
        metrics.calculate_overall()
        
        # Generate issues and suggestions (heuristics)
        metrics.issues = self._identify_issues(deck, metrics)
        metrics.suggestions = self._generate_suggestions(deck, metrics)
        
        # LLM Analysis (if available)
        if self.llm_service:
            try:
                plan = await self.llm_service.analyze_deck(deck)
                metrics.improvement_plan = plan
                
                # Merge LLM suggestions into main list
                if plan.analysis:
                    metrics.suggestions.append(f"LLM Analysis: {plan.analysis}")
                
                for addition in plan.additions:
                    metrics.suggestions.append(
                        f"Add {addition.quantity}x {addition.card_name}: {addition.reason}"
                    )
                
                for removal in plan.removals:
                    metrics.suggestions.append(
                        f"Remove {removal.quantity}x {removal.card_name}: {removal.reason}"
                    )
                    
            except Exception as e:
                metrics.issues.append(f"LLM analysis failed: {str(e)}")
        
        return metrics
    
    def _analyze_mana_curve(self, deck: Deck) -> float:
        """
        Analyze mana curve quality.
        
        A good curve follows a bell-like distribution centered around 2-3 CMC.
        
        Args:
            deck: Deck to analyze
            
        Returns:
            Score from 0.0 to 1.0
        """
        nonlands = deck.get_nonlands()
        if not nonlands:
            return 0.0
        
        # Count cards at each CMC
        cmc_counts: Dict[int, int] = {}
        total_nonlands = 0
        
        for deck_card in nonlands:
            cmc = int(deck_card.card.cmc)
            cmc_counts[cmc] = cmc_counts.get(cmc, 0) + deck_card.quantity
            total_nonlands += deck_card.quantity
        
        if total_nonlands == 0:
            return 0.0
        
        # Calculate distribution percentages
        cmc_percentages = {
            cmc: count / total_nonlands
            for cmc, count in cmc_counts.items()
        }
        
        # Ideal distribution (bell curve centered at 2-3)
        ideal = {
            0: 0.05,
            1: 0.15,
            2: 0.25,
            3: 0.25,
            4: 0.15,
            5: 0.10,
            6: 0.05,
        }
        
        # Calculate deviation from ideal
        total_deviation = 0.0
        for cmc in range(7):
            actual = cmc_percentages.get(cmc, 0.0)
            expected = ideal.get(cmc, 0.0)
            total_deviation += abs(actual - expected)
        
        # Convert deviation to score (lower deviation = higher score)
        # Max deviation would be 2.0 (everything at wrong CMC)
        score = max(0.0, 1.0 - (total_deviation / 2.0))
        
        return score
    
    def _analyze_land_ratio(self, deck: Deck) -> float:
        """
        Analyze land ratio quality.
        
        Ideal ratio is ~40% for 60-card decks, ~37% for Commander.
        
        Args:
            deck: Deck to analyze
            
        Returns:
            Score from 0.0 to 1.0
        """
        if deck.total_cards == 0:
            return 0.0
        
        lands = deck.get_lands()
        land_count = sum(dc.quantity for dc in lands)
        land_ratio = land_count / deck.total_cards
        
        # Determine ideal ratio based on deck size
        if deck.total_cards >= 99:  # Commander
            ideal_ratio = 0.37
        else:  # Standard 60-card
            ideal_ratio = 0.40
        
        # Calculate deviation from ideal
        deviation = abs(land_ratio - ideal_ratio)
        
        # Score based on deviation (within 5% is perfect, >10% is poor)
        if deviation <= 0.05:
            score = 1.0
        elif deviation <= 0.10:
            score = 0.7
        else:
            score = max(0.0, 0.5 - deviation)
        
        return score
    
    def _analyze_synergies(self, deck: Deck) -> float:
        """
        Analyze card synergies.
        
        Looks for keyword overlap, type synergies, and tribal themes.
        
        Args:
            deck: Deck to analyze
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Simple heuristic: count keyword overlap
        keyword_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        
        for deck_card in deck.cards:
            # Count keywords
            for keyword in deck_card.card.keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + deck_card.quantity
            
            # Count creature types (for tribal synergy)
            if "Creature" in deck_card.card.types:
                for subtype in deck_card.card.subtypes:
                    type_counts[subtype] = type_counts.get(subtype, 0) + deck_card.quantity
        
        # Score based on synergy clusters
        synergy_score = 0.0
        
        # Keyword synergies (having 4+ cards with same keyword is good)
        strong_keywords = [k for k, v in keyword_counts.items() if v >= 4]
        synergy_score += min(0.5, len(strong_keywords) * 0.15)
        
        # Tribal synergies (having 8+ creatures of same type is good)
        strong_tribes = [t for t, v in type_counts.items() if v >= 8]
        synergy_score += min(0.5, len(strong_tribes) * 0.25)
        
        return min(1.0, synergy_score)
    
    def _analyze_consistency(self, deck: Deck) -> float:
        """
        Analyze deck consistency.
        
        Measures how many 4-ofs and 3-ofs exist (more copies = more consistent).
        
        Args:
            deck: Deck to analyze
            
        Returns:
            Score from 0.0 to 1.0
        """
        nonlands = deck.get_nonlands()
        if not nonlands:
            return 0.0
        
        # Count cards by quantity
        four_ofs = sum(1 for dc in nonlands if dc.quantity == 4)
        three_ofs = sum(1 for dc in nonlands if dc.quantity == 3)
        two_ofs = sum(1 for dc in nonlands if dc.quantity == 2)
        one_ofs = sum(1 for dc in nonlands if dc.quantity == 1)
        
        total_unique = len(nonlands)
        
        # Higher consistency = more 4-ofs and 3-ofs
        consistency_score = (
            (four_ofs * 1.0) +
            (three_ofs * 0.75) +
            (two_ofs * 0.5) +
            (one_ofs * 0.25)
        ) / total_unique if total_unique > 0 else 0.0
        
        return min(1.0, consistency_score)
    
    def _identify_issues(self, deck: Deck, metrics: DeckQualityMetrics) -> List[str]:
        """
        Identify specific issues with the deck.
        
        Args:
            deck: Deck to analyze
            metrics: Quality metrics
            
        Returns:
            List of issue descriptions
        """
        issues = []
        
        if metrics.mana_curve_score < 0.6:
            issues.append("Mana curve is not optimal - too many high or low CMC cards")
        
        if metrics.land_ratio_score < 0.6:
            land_count = sum(dc.quantity for dc in deck.get_lands())
            issues.append(f"Land ratio ({land_count}/{deck.total_cards}) is not ideal")
        
        if metrics.synergy_score < 0.4:
            issues.append("Deck lacks synergies between cards")
        
        if metrics.consistency_score < 0.5:
            issues.append("Deck has too many 1-ofs and 2-ofs, reducing consistency")
        
        return issues
    
    def _generate_suggestions(self, deck: Deck, metrics: DeckQualityMetrics) -> List[str]:
        """
        Generate improvement suggestions.
        
        Args:
            deck: Deck to analyze
            metrics: Quality metrics
            
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        if metrics.mana_curve_score < 0.6:
            suggestions.append("Adjust mana curve to focus on 2-4 CMC cards")
        
        if metrics.land_ratio_score < 0.6:
            land_count = sum(dc.quantity for dc in deck.get_lands())
            ideal_count = int(deck.total_cards * 0.4)
            if land_count < ideal_count:
                suggestions.append(f"Add {ideal_count - land_count} more lands")
            else:
                suggestions.append(f"Remove {land_count - ideal_count} lands")
        
        if metrics.synergy_score < 0.4:
            suggestions.append("Add cards with overlapping keywords or tribal synergies")
        
        if metrics.consistency_score < 0.5:
            suggestions.append("Increase card quantities (prefer 3-4 copies of key cards)")
        
        return suggestions
