"""
Deck Builder Service for V3 architecture.

Handles deck construction logic including card selection,
mana curve balancing, and applying improvement suggestions.
"""

from typing import List, Optional, Dict, Any
import random
from ..models.deck import (
    Deck,
    DeckCard,
    MTGCard,
    DeckBuildRequest,
    CardSearchFilters,
    DeckImprovementPlan,
)
from ..database.card_repository import CardRepository


class DeckBuilderService:
    """
    Service for building and refining MTG decks.
    
    Handles initial deck construction and iterative improvements
    based on quality verification feedback.
    """
    
    def __init__(self, card_repository: CardRepository):
        """
        Initialize deck builder service.
        
        Args:
            card_repository: Card repository for data access
        """
        self.card_repo = card_repository
    
    def build_initial_deck(self, request: DeckBuildRequest) -> Deck:
        """
        Build initial deck from request parameters.
        
        Args:
            request: Deck build request
            
        Returns:
            Initial deck
        """
        deck = Deck(
            cards=[],
            format=request.format,
            archetype=request.archetype,
            colors=request.colors,
        )
        
        # Calculate land count (typically 40% for 60-card, 37% for Commander)
        if request.deck_size == 100:  # Commander
            land_count = 37
        else:  # Standard 60-card
            land_count = int(request.deck_size * 0.4)
        
        nonland_count = request.deck_size - land_count
        
        # Add lands
        lands = self._select_lands(request.colors, land_count)
        deck.cards.extend(lands)
        
        # Add nonland spells based on archetype
        spells = self._select_spells(request, nonland_count)
        deck.cards.extend(spells)
        
        deck.calculate_totals()
        return deck
    
    def refine_deck(
        self,
        deck: Deck,
        suggestions: List[str],
        request: DeckBuildRequest,
        improvement_plan: Optional[DeckImprovementPlan] = None
    ) -> Deck:
        """
        Refine deck based on quality verification suggestions.
        
        Args:
            deck: Current deck
            suggestions: Improvement suggestions from quality verifier
            request: Original build request
            improvement_plan: Optional structured improvement plan from LLM
            
        Returns:
            Refined deck
        """
        # 1. Apply LLM Improvement Plan if available
        if improvement_plan:
            # Remove cards
            for removal in improvement_plan.removals:
                deck = self._remove_card(deck, removal.card_name, removal.quantity)
            
            # Add cards
            for addition in improvement_plan.additions:
                deck = self._add_card(deck, addition.card_name, addition.quantity)
        
        # 2. Apply Heuristic Suggestions (fallback or supplementary)
        # Only apply if no specific plan for that aspect
        for suggestion in suggestions:
            if "mana curve" in suggestion.lower() and not improvement_plan:
                deck = self._adjust_mana_curve(deck, request)
            elif "land" in suggestion.lower() and not improvement_plan:
                deck = self._adjust_lands(deck, request)
            elif "synergy" in suggestion.lower() and not improvement_plan:
                deck = self._improve_synergy(deck, request)
        
        deck.calculate_totals()
        return deck
    
    def _remove_card(self, deck: Deck, card_name: str, quantity: int) -> Deck:
        """Remove specific card from deck."""
        new_cards = []
        removed_count = 0
        
        for deck_card in deck.cards:
            if deck_card.card.name.lower() == card_name.lower():
                if removed_count < quantity:
                    # Reduce quantity or remove
                    remaining = deck_card.quantity - (quantity - removed_count)
                    if remaining > 0:
                        deck_card.quantity = remaining
                        new_cards.append(deck_card)
                    removed_count += (deck_card.quantity - max(0, remaining))
                else:
                    new_cards.append(deck_card)
            else:
                new_cards.append(deck_card)
        
        deck.cards = new_cards
        return deck

    def _add_card(self, deck: Deck, card_name: str, quantity: int) -> Deck:
        """Add specific card to deck."""
        # Check if already in deck
        for deck_card in deck.cards:
            if deck_card.card.name.lower() == card_name.lower():
                deck_card.quantity += quantity
                return deck
        
        # Not in deck, fetch from repo
        card = self.card_repo.get_by_name(card_name)
        if card:
            deck.cards.append(DeckCard(card=card, quantity=quantity))
        else:
            # Try fuzzy search if exact match fails
            results = self.card_repo.search(CardSearchFilters(text_query=card_name, limit=1))
            if results:
                deck.cards.append(DeckCard(card=results[0], quantity=quantity))
        
        return deck

    def _select_lands(self, colors: List[str], count: int) -> List[DeckCard]:
        """
        Select appropriate lands for the deck.
        
        Args:
            colors: Deck colors
            count: Number of lands needed
            
        Returns:
            List of DeckCard with lands
        """
        lands = []
        
        # For now, simple implementation: basic lands
        # In a real implementation, would include dual lands, fetch lands, etc.
        if not colors or len(colors) == 0:
            # Colorless - use Wastes or generic lands
            lands.append(DeckCard(
                card=MTGCard(
                    id="wastes",
                    name="Wastes",
                    type_line="Basic Land",
                    types=["Land"],
                    oracle_text="Tap: Add {C}.",
                    rarity="Common"
                ),
                quantity=count
            ))
        elif len(colors) == 1:
            # Mono-color - all basic lands
            basic_land_name = self._get_basic_land_name(colors[0])
            lands.append(DeckCard(
                card=MTGCard(
                    id=basic_land_name.lower(),
                    name=basic_land_name,
                    type_line="Basic Land — " + self._get_land_subtype(colors[0]),
                    types=["Land"],
                    subtypes=[self._get_land_subtype(colors[0])],
                    oracle_text=f"Tap: Add {{{colors[0]}}}.",
                    rarity="Common"
                ),
                quantity=count
            ))
        else:
            # Multi-color - distribute among colors
            per_color = count // len(colors)
            remainder = count % len(colors)
            
            for i, color in enumerate(colors):
                basic_land_name = self._get_basic_land_name(color)
                quantity = per_color + (1 if i < remainder else 0)
                lands.append(DeckCard(
                    card=MTGCard(
                        id=basic_land_name.lower(),
                        name=basic_land_name,
                        type_line="Basic Land — " + self._get_land_subtype(color),
                        types=["Land"],
                        subtypes=[self._get_land_subtype(color)],
                        oracle_text=f"Tap: Add {{{color}}}.",
                        rarity="Common"
                    ),
                    quantity=quantity
                ))
        
        return lands
    
    def _select_spells(self, request: DeckBuildRequest, count: int) -> List[DeckCard]:
        """
        Select nonland spells for the deck.
        
        Args:
            request: Deck build request
            count: Number of spells needed
            
        Returns:
            List of DeckCard with spells
        """
        spells = []
        
        # Define CMC distribution based on archetype
        cmc_distribution = self._get_cmc_distribution(request.archetype, count)
        
        for cmc, needed_count in cmc_distribution.items():
            # Search for cards at this CMC
            filters = CardSearchFilters(
                colors=request.colors,
                cmc_min=float(cmc),
                cmc_max=float(cmc),
                format_legal=request.format,
                limit=needed_count * 2  # Get more options
            )
            
            cards = self.card_repo.search(filters)
            
            # Filter out lands
            cards = [c for c in cards if "Land" not in c.types]
            
            # Select cards (prefer creatures for aggro, spells for control)
            selected = self._select_cards_by_archetype(
                cards,
                request.archetype,
                needed_count
            )
            
            # Add to deck (typically 2-4 copies each)
            cards_per_slot = 3  # Default to 3 copies
            slots_needed = needed_count // cards_per_slot
            
            for i, card in enumerate(selected[:slots_needed]):
                spells.append(DeckCard(card=card, quantity=cards_per_slot))
        
        return spells
    
    def _get_cmc_distribution(
        self,
        archetype: Optional[str],
        total_count: int
    ) -> Dict[int, int]:
        """
        Get CMC distribution based on archetype.
        
        Args:
            archetype: Deck archetype
            total_count: Total number of spells
            
        Returns:
            Dictionary mapping CMC to count
        """
        if archetype and "aggro" in archetype.lower():
            # Aggro: low curve (1-3 CMC heavy)
            return {
                1: int(total_count * 0.25),
                2: int(total_count * 0.35),
                3: int(total_count * 0.25),
                4: int(total_count * 0.10),
                5: int(total_count * 0.05),
            }
        elif archetype and "control" in archetype.lower():
            # Control: higher curve with more interaction
            return {
                2: int(total_count * 0.30),
                3: int(total_count * 0.25),
                4: int(total_count * 0.20),
                5: int(total_count * 0.15),
                6: int(total_count * 0.10),
            }
        else:
            # Midrange: balanced curve
            return {
                1: int(total_count * 0.10),
                2: int(total_count * 0.25),
                3: int(total_count * 0.30),
                4: int(total_count * 0.20),
                5: int(total_count * 0.10),
                6: int(total_count * 0.05),
            }
    
    def _select_cards_by_archetype(
        self,
        cards: List[MTGCard],
        archetype: Optional[str],
        count: int
    ) -> List[MTGCard]:
        """
        Select cards based on archetype preference.
        
        Args:
            cards: Available cards
            archetype: Deck archetype
            count: Number of cards to select
            
        Returns:
            Selected cards
        """
        if not cards:
            return []
        
        if archetype and "aggro" in archetype.lower():
            # Prefer creatures
            creatures = [c for c in cards if "Creature" in c.types]
            if creatures:
                return random.sample(creatures, min(count, len(creatures)))
        elif archetype and "control" in archetype.lower():
            # Prefer instants and sorceries
            spells = [c for c in cards if "Instant" in c.types or "Sorcery" in c.types]
            if spells:
                return random.sample(spells, min(count, len(spells)))
        
        # Default: random selection
        return random.sample(cards, min(count, len(cards)))
    
    def _adjust_mana_curve(self, deck: Deck, request: DeckBuildRequest) -> Deck:
        """Adjust mana curve to be more optimal."""
        # Placeholder: would implement curve smoothing logic
        return deck
    
    def _adjust_lands(self, deck: Deck, request: DeckBuildRequest) -> Deck:
        """Adjust land count to optimal ratio."""
        # Placeholder: would implement land ratio adjustment
        return deck
    
    def _improve_synergy(self, deck: Deck, request: DeckBuildRequest) -> Deck:
        """Improve card synergies in the deck."""
        # Placeholder: would implement synergy improvement
        return deck
    
    def _get_basic_land_name(self, color: str) -> str:
        """Get basic land name for color."""
        mapping = {
            "W": "Plains",
            "U": "Island",
            "B": "Swamp",
            "R": "Mountain",
            "G": "Forest",
        }
        return mapping.get(color, "Wastes")
    
    def _get_land_subtype(self, color: str) -> str:
        """Get land subtype for color."""
        return self._get_basic_land_name(color)
