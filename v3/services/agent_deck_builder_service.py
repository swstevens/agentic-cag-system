"""
Agent-based Deck Builder Service for V3 architecture.

Uses LLM reasoning with tool-calling to make intelligent decisions
about deck construction and refinement.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from ..models.deck import (
    Deck,
    DeckCard,
    MTGCard,
    DeckBuildRequest,
    CardSearchFilters,
    DeckImprovementPlan,
)
from ..models.format_rules import FormatRules
from ..database.card_repository import CardRepository
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


# Tool response models
class CardSearchResult(BaseModel):
    """Result from searching cards."""
    cards: List[Dict[str, Any]] = Field(description="List of cards found")
    count: int = Field(description="Number of cards found")


class CardSelection(BaseModel):
    """Single card selection for deck construction."""
    card_name: str = Field(description="Name of the card")
    quantity: int = Field(description="Number of copies (1-4)", ge=1, le=4)
    reasoning: str = Field(description="Why this card fits the deck strategy")


class DeckConstructionPlan(BaseModel):
    """LLM's plan for constructing a deck."""
    strategy: str = Field(description="Overall strategy for deck construction")
    card_selections: List[CardSelection] = Field(
        description="List of SPELL card selections. Do NOT include lands. Focus on 3-4 copies of key cards for consistency."
    )


class RefinementAction(BaseModel):
    """Single refinement action."""
    type: str = Field(description="Action type: 'add' or 'remove'")
    card_name: str = Field(description="Name of the card")
    quantity: int = Field(description="Number of copies", ge=1)
    reasoning: str = Field(description="Why this action improves the deck")


class RefinementPlan(BaseModel):
    """LLM's plan for refining a deck."""
    analysis: str = Field(description="Analysis of current deck state")
    actions: List[RefinementAction] = Field(
        description="List of actions to take (add/remove cards)"
    )


class AgentDeckBuilderService:
    """
    LLM-powered deck builder that reasons about card selection.
    
    Uses tool-calling to search cards and make intelligent decisions
    about deck construction based on archetype and strategy.
    """
    
    def __init__(
        self,
        card_repository: CardRepository,
        model_name: Optional[str] = None
    ):
        """
        Initialize agent deck builder.

        Args:
            card_repository: Card repository for data access
            model_name: LLM model to use (defaults to env var or gpt-4o-mini)
        """
        self.card_repo = card_repository
        self.current_request = None  # Store current request for tool access
        
        # Use provided model, or env var, or default
        self.model_name = model_name or os.getenv("DEFAULT_MODEL", "openai:gpt-4o-mini")

        # Agents will be created dynamically per request with format-specific prompts
        # This allows us to use FormatRules data for accurate guidelines
        self.build_agent = None
        self.refine_agent = None

    def _create_agents_for_format(self, format_name: str):
        """
        Create agents with format-specific system prompts.

        Args:
            format_name: Format to create agents for
        """
        # Generate dynamic prompts based on format
        build_prompt = PromptBuilder.build_deck_builder_system_prompt(format_name)
        refine_prompt = PromptBuilder.build_refine_agent_system_prompt(format_name)

        # Create agents with format-specific prompts
        self.build_agent = Agent(
            self.model_name,
            output_type=DeckConstructionPlan,
            system_prompt=build_prompt
        )

        self.refine_agent = Agent(
            self.model_name,
            output_type=RefinementPlan,
            system_prompt=refine_prompt
        )

        # Register tools for both agents
        self._register_tools()

    def _register_tools(self):
        """Register tools for the agents to use."""

        @self.build_agent.tool
        async def search_cards(
            ctx: RunContext,
            semantic_query: Optional[str] = None,
            colors: Optional[List[str]] = None,
            types: Optional[List[str]] = None,
            cmc_min: Optional[float] = None,
            cmc_max: Optional[float] = None,
            text_query: Optional[str] = None,
            limit: int = 20
        ) -> CardSearchResult:
            """
            Search for cards in the database.

            Args:
                semantic_query: Natural language query for semantic search (e.g., "fast goblin", "removal")
                colors: Card colors (W, U, B, R, G)
                types: Card types (Creature, Instant, Sorcery, etc.)
                cmc_min: Minimum converted mana cost
                cmc_max: Maximum converted mana cost
                text_query: Exact text to search in card name/text
                limit: Maximum results to return
            """
            logger.info(f"🔍 BUILD Agent search: query='{semantic_query}', colors={colors}, types={types}")

            filters = CardSearchFilters(
                colors=colors,
                cmc_min=cmc_min,
                cmc_max=cmc_max,
                text_query=text_query,
                format_legal=self.current_request.format if self.current_request else None,
                limit=limit
            )

            if semantic_query:
                cards = self.card_repo.semantic_search(semantic_query, filters, limit)
            else:
                cards = self.card_repo.search(filters)
            
            # Filter by types if specified
            if types:
                cards = [c for c in cards if any(t in c.types for t in types)]
            
            # Convert to dict for LLM
            card_dicts = [
                {
                    "name": c.name,
                    "cmc": c.cmc,
                    "type_line": c.type_line,
                    "colors": c.colors,
                    "is_legendary": "Legendary" in c.type_line,
                    "oracle_text": c.oracle_text[:100] if c.oracle_text else ""
                }
                for c in cards[:limit]
            ]
            
            return CardSearchResult(cards=card_dicts, count=len(card_dicts))
        
        @self.refine_agent.tool
        async def search_cards_refine(
            ctx: RunContext,
            semantic_query: Optional[str] = None,
            colors: Optional[List[str]] = None,
            types: Optional[List[str]] = None,
            cmc_min: Optional[float] = None,
            cmc_max: Optional[float] = None,
            text_query: Optional[str] = None,
            limit: int = 20
        ) -> CardSearchResult:
            """Same as search_cards but for refine agent."""
            filters = CardSearchFilters(
                colors=colors,
                cmc_min=cmc_min,
                cmc_max=cmc_max,
                text_query=text_query,
                format_legal=self.current_request.format if self.current_request else None,
                limit=limit
            )
            
            if semantic_query:
                cards = self.card_repo.semantic_search(semantic_query, filters, limit)
            else:
                cards = self.card_repo.search(filters)
            
            if types:
                cards = [c for c in cards if any(t in c.types for t in types)]
            
            card_dicts = [
                {
                    "name": c.name,
                    "cmc": c.cmc,
                    "type_line": c.type_line,
                    "colors": c.colors,
                    "is_legendary": "Legendary" in c.type_line,
                    "oracle_text": c.oracle_text[:100] if c.oracle_text else ""
                }
                for c in cards[:limit]
            ]

            return CardSearchResult(cards=card_dicts, count=len(card_dicts))
    
    async def build_initial_deck(self, request: DeckBuildRequest) -> Deck:
        """
        Build initial deck using LLM reasoning.

        Args:
            request: Deck build request

        Returns:
            Initial deck
        """
        # Create agents with format-specific prompts
        self._create_agents_for_format(request.format)

        # Get format-specific land count
        land_count = FormatRules.get_land_count(request.format, request.archetype)

        prompt = f"""Build a {request.archetype} deck for {request.format}.

Colors: {', '.join(request.colors)}
Strategy: {request.strategy}

IMPORTANT:
- You only need to select SPELL cards (creatures, instants, sorceries, etc.)
- Lands will be added automatically ({land_count} lands based on {request.archetype} archetype)
- Focus on building a spell suite that fits the format and archetype guidelines
- LIMIT yourself to 3-5 broad searches MAX (e.g., "aggressive creatures", "removal spells", "card draw")
- Each search returns 20 cards, so you have plenty of options from just a few searches
- Do NOT make many narrow searches - make fewer, broader searches for efficiency

Use the search_cards tool to find appropriate cards.
- Use semantic_query for high-level concepts (e.g. "aggressive creatures", "removal spells")
- Avoid making many similar searches - one broad search is better than many narrow ones

Build a focused, consistent spell suite with clear synergies using MINIMAL searches (3-5 maximum).
"""

        try:
            # Store request for tool access
            self.current_request = request

            result = await self.build_agent.run(prompt)
            plan: DeckConstructionPlan = result.output

            # Execute the plan
            deck = await self._execute_construction_plan(plan, request)
            return deck

        except Exception as e:
            logger.error(f"Agent deck building failed: {e}", exc_info=True)
            # Fallback to simple construction
            return self._fallback_build(request)
        finally:
            self.current_request = None
    
    async def refine_deck(
        self,
        deck: Deck,
        suggestions: List[str],
        request: DeckBuildRequest,
        improvement_plan: Optional[DeckImprovementPlan] = None
    ) -> Deck:
        """
        Refine deck using LLM reasoning.

        Args:
            deck: Current deck
            suggestions: Improvement suggestions
            request: Original build request
            improvement_plan: Optional improvement plan from quality verifier

        Returns:
            Refined deck
        """
        # Ensure agents are created for this format (might be different call chain)
        if self.refine_agent is None:
            self._create_agents_for_format(request.format)

        # Format current deck
        deck_list = [
            f"{dc.quantity}x {dc.card.name} (CMC: {dc.card.cmc}, {dc.card.type_line})"
            for dc in deck.cards
        ]

        prompt = f"""Refine this {request.archetype} deck:

Current deck:
{chr(10).join(deck_list)}

Suggestions:
{chr(10).join(suggestions)}

"""

        if improvement_plan:
            prompt += f"\nImprovement plan from quality analysis:\n"
            prompt += f"Analysis: {improvement_plan.analysis}\n"
            for removal in improvement_plan.removals:
                prompt += f"- Remove {removal.quantity}x {removal.card_name}: {removal.reason}\n"
            for addition in improvement_plan.additions:
                prompt += f"- Add {addition.quantity}x {addition.card_name}: {addition.reason}\n"

        target_size = FormatRules.get_deck_size(request.format)
        prompt += f"\nIMPORTANT CONSTRAINTS:"
        prompt += f"\n- Current deck size is {deck.total_cards}. Target size is {target_size}."
        prompt += "\n- If current < target, you MUST add more cards than you remove."
        prompt += "\n- If current > target, you MUST remove more cards than you add."
        prompt += "\n- If current == target, you MUST add and remove equal amounts."
        prompt += "\nUse search_cards_refine to find better cards (use semantic_query for best results). Provide a refinement plan."

        try:
            # Store request for tool access
            self.current_request = request

            result = await self.refine_agent.run(prompt)
            plan: RefinementPlan = result.output

            # Execute the refinement plan
            deck = await self._execute_refinement_plan(deck, plan, request)
            return deck

        except Exception as e:
            logger.error(f"Agent deck refinement failed: {e}", exc_info=True)
            # Fallback to simple refinement
            return deck
        finally:
            self.current_request = None
    
    async def _execute_construction_plan(
        self,
        plan: DeckConstructionPlan,
        request: DeckBuildRequest
    ) -> Deck:
        """Execute the LLM's construction plan."""
        logger.info(f"Executing construction plan: {plan.strategy}")
        
        deck = Deck(
            cards=[],
            format=request.format,
            archetype=request.archetype,
            colors=request.colors,
        )
        
        # Determine target deck size based on format
        target_size = self._get_target_deck_size(request.format, request.deck_size)
        
        # Determine land count based on archetype
        land_count = self._get_land_count(request.archetype, target_size)

        logger.info(f"Target deck size: {target_size}, Land count: {land_count}, Spell slots: {target_size - land_count}")
        
        # STEP 1: Add lands first
        if request.colors:
            lands_per_color = land_count // len(request.colors)
            remainder = land_count % len(request.colors)
            
            for i, color in enumerate(request.colors):
                land_name = self._get_basic_land_name(color)
                quantity = lands_per_color + (1 if i < remainder else 0)
                
                deck.cards.append(DeckCard(
                    card=MTGCard(
                        id=land_name.lower(),
                        name=land_name,
                        type_line="Basic Land",
                        types=["Land"],
                        cmc=0.0
                    ),
                    quantity=quantity
                ))
        
        # STEP 2: Add spell cards from LLM's plan
        spell_slots = target_size - land_count
        cards_added = 0
        
        for i, selection in enumerate(plan.card_selections):
            if cards_added >= spell_slots:
                logger.info(f"Reached spell slot limit ({spell_slots}), stopping card additions")
                break
                
            # CardSelection is now a proper model with attributes
            card_name = selection.card_name
            quantity = selection.quantity
            
            if not card_name:
                logger.warning(f"Selection {i} missing card_name: {selection}")
                continue
            
            # Don't exceed remaining slots
            quantity = min(quantity, spell_slots - cards_added)
            
            # Get card from repository
            card = self.card_repo.get_by_name(card_name)
            if card:
                # Skip lands (we already added them)
                if "Land" not in card.types:
                    # logger.info(f"Adding {quantity}x {card_name}")
                    deck.cards.append(DeckCard(card=card, quantity=quantity))
                    cards_added += quantity
            else:
                logger.warning(f"Card '{card_name}' not found in repository")
        
        # STEP 3: Fill remaining slots if needed
        if cards_added < spell_slots:
            remaining = spell_slots - cards_added
            logger.warning(f"Only {cards_added}/{spell_slots} spell slots filled by LLM")
            logger.info(f"Filling {remaining} remaining slots with basic creatures/spells")
            self._add_filler_cards(deck, remaining, request)
        
        # Validate card quantities based on format rules
        deck = self._validate_legendary_quantities(deck, request.format)

        deck = self._validate_legendary_quantities(deck, request.format)

        deck.calculate_totals()
        logger.info(f"Deck built: {deck.total_cards} cards (target: {target_size})")

        # Final validation
        if deck.total_cards != target_size:
            logger.error(f"Deck size mismatch! Got {deck.total_cards}, expected {target_size}")

        return deck
    
    def _get_target_deck_size(self, format: str, requested_size: int) -> int:
        """Get target deck size based on format."""
        if requested_size > 0:
            return requested_size
        
        # Format-specific defaults
        format_lower = format.lower()
        if "commander" in format_lower or "edh" in format_lower:
            return 100
        elif "brawl" in format_lower:
            return 60  # Brawl is 60 cards
        else:
            # Standard, Modern, Pioneer, Legacy, Vintage, etc.
            return 60
    
    def _get_land_count(self, archetype: str, deck_size: int) -> int:
        """Get recommended land count based on archetype and deck size."""
        archetype_lower = archetype.lower()
        
        # For 60-card formats
        if deck_size == 60:
            if "aggro" in archetype_lower:
                return 22
            elif "control" in archetype_lower:
                return 26
            elif "combo" in archetype_lower:
                return 23
            else:  # Midrange or unknown
                return 24
        
        # For Commander (100 cards)
        elif deck_size == 100:
            return 37
        
        # Default: ~40% lands
        return int(deck_size * 0.4)
    
    async def _execute_refinement_plan(
        self,
        deck: Deck,
        plan: RefinementPlan,
        request: DeckBuildRequest
    ) -> Deck:
        """Execute the LLM's refinement plan."""
        logger.info(f"Executing refinement plan: {plan.analysis[:100]}... Actions: {len(plan.actions)}")
        
        for action in plan.actions:
            # logger.info(f"Action: {action.type} {action.quantity}x {action.card_name}")
            
            if action.type == "remove":
                deck = self._remove_card(deck, action.card_name, action.quantity)
            elif action.type == "add":
                deck = self._add_card(deck, action.card_name, action.quantity)
        
        deck.calculate_totals()

        # POST-REFINEMENT SIZE CORRECTION
        target_size = FormatRules.get_deck_size(request.format)

        if deck.total_cards < target_size:
            shortage = target_size - deck.total_cards
            logger.warning(f"Deck is {shortage} cards short. Adding filler creatures...")
            self._add_filler_cards(deck, shortage, request)
        
        elif deck.total_cards > target_size:
            excess = deck.total_cards - target_size
            logger.warning(f"Deck has {excess} excess cards. Trimming...")
            
            # Remove excess cards (prioritize 1-ofs and 2-ofs)
            deck.cards.sort(key=lambda dc: dc.quantity)  # Sort by quantity ascending
            
            for dc in deck.cards:
                if excess <= 0:
                    break
                if "Land" not in dc.card.types:  # Don't trim lands
                    to_remove = min(dc.quantity, excess)
                    dc.quantity -= to_remove
                    excess -= to_remove
                    logger.info(f"Trimming: Removing {to_remove}x {dc.card.name}")
            
            # Remove cards with 0 quantity
            deck.cards = [dc for dc in deck.cards if dc.quantity > 0]
        
        # Validate card quantities based on format rules before returning
        deck = self._validate_legendary_quantities(deck, request.format)

        deck = self._validate_legendary_quantities(deck, request.format)

        deck.calculate_totals()
        logger.info(f"Final deck size after correction: {deck.total_cards}")

        return deck
    
    def _remove_card(self, deck: Deck, card_name: str, quantity: int) -> Deck:
        """Remove card from deck."""
        new_cards = []
        removed_count = 0
        
        for deck_card in deck.cards:
            if deck_card.card.name.lower() == card_name.lower():
                if removed_count < quantity:
                    # Calculate how many we can remove from this stack
                    to_remove = min(deck_card.quantity, quantity - removed_count)
                    remaining = deck_card.quantity - to_remove
                    
                    if remaining > 0:
                        deck_card.quantity = remaining
                        new_cards.append(deck_card)
                    
                    removed_count += to_remove
                else:
                    # Already removed enough, keep this stack
                    new_cards.append(deck_card)
            else:
                new_cards.append(deck_card)
        
        deck.cards = new_cards
        return deck
    
    def _add_card(self, deck: Deck, card_name: str, quantity: int) -> Deck:
        """Add card to deck."""
        for deck_card in deck.cards:
            if deck_card.card.name.lower() == card_name.lower():
                deck_card.quantity += quantity
                return deck
        
        card = self.card_repo.get_by_name(card_name)
        if card:
            deck.cards.append(DeckCard(card=card, quantity=quantity))
        
        return deck
    
    def _fallback_build(self, request: DeckBuildRequest) -> Deck:
        """Fallback to simple deck construction."""
        # Simple implementation - just add basic lands
        deck = Deck(
            cards=[],
            format=request.format,
            archetype=request.archetype,
            colors=request.colors,
        )
        
        # Add basic lands (simplified)
        if request.colors:
            # Default to 60 if not specified
            target_size = request.deck_size if request.deck_size > 0 else 60
            
            for color in request.colors:
                land_name = self._get_basic_land_name(color)
                deck.cards.append(DeckCard(
                    card=MTGCard(
                        id=land_name.lower(),
                        name=land_name,
                        type_line="Basic Land",
                        types=["Land"],
                        cmc=0.0
                    ),
                    quantity=target_size // len(request.colors)
                ))
        
        deck.calculate_totals()
        return deck
    
    def _add_filler_cards(self, deck: Deck, needed: int, request: DeckBuildRequest) -> None:
        """
        Add filler cards to reach target deck size.
        
        Searches for low-cost creatures and adds them to the deck,
        respecting format copy limits and checking for existing cards.
        Falls back to adding lands if not enough creatures are available.
        """
        if not request.colors or needed <= 0:
            return
        
        copy_limit = FormatRules.get_copy_limit(request.format)
        
        # Search for basic creatures in the deck's colors
        filters = CardSearchFilters(
            colors=request.colors,
            types=["Creature"],
            cmc_max=3.0,
            format_legal=request.format,
            limit=30
        )
        filler_cards = self.card_repo.search(filters)
        
        # Add cards until we reach target
        for filler_card in filler_cards:
            if needed <= 0:
                break
                
            # Check if card already exists in deck
            existing = next((dc for dc in deck.cards if dc.card.name == filler_card.name), None)
            
            if existing:
                # Increase quantity (respecting copy limit)
                qty = min(copy_limit - existing.quantity, needed)
                if qty > 0:
                    existing.quantity += qty
                    needed -= qty
                    logger.info(f"Filler: Increasing {filler_card.name} by {qty}")
            else:
                # Add new card (respecting copy limit)
                qty = min(copy_limit, needed)
                deck.cards.append(DeckCard(card=filler_card, quantity=qty))
                needed -= qty
                logger.info(f"Filler: Adding {qty}x {filler_card.name}")
        
        # Fallback: add lands if still needed
        if needed > 0:
            logger.info(f"Still {needed} cards needed. Adding lands...")
            land_card = next((dc for dc in deck.cards if "Land" in dc.card.types), None)
            if land_card:
                land_card.quantity += needed
            else:
                # No lands in deck yet - add basic land for first color
                land_name = self._get_basic_land_name(request.colors[0])
                deck.cards.append(DeckCard(
                    card=MTGCard(
                        id=land_name.lower(),
                        name=land_name,
                        type_line="Basic Land",
                        types=["Land"],
                        cmc=0.0
                    ),
                    quantity=needed
                ))
    
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

    def _validate_legendary_quantities(self, deck: Deck, format_name: Optional[str] = None) -> Deck:
        """
        Validate and enforce card quantity constraints based on format rules.

        For non-singleton formats (Standard, Modern, etc.):
        - Legendary cards: max 2-3 copies (1 on battlefield, 2-3 for redundancy)
        - Non-legendary cards: max 4 copies (standard limit)

        For singleton formats (Commander):
        - All non-land cards: exactly 1 copy (singleton rule)
        - Basic lands: can have any number

        Args:
            deck: Deck to validate
            format_name: Format name (defaults to "Standard" if not provided)

        Returns:
            Deck with corrected quantities
        """
        if not format_name:
            format_name = "Standard"

        is_singleton = FormatRules.is_singleton(format_name)

        for deck_card in deck.cards:
            card = deck_card.card
            is_legendary = "Legendary" in card.type_line
            is_basic_land = "Land" in card.types and card.type_line.startswith("Basic")

            if is_singleton:
                # Commander/singleton rule: 1 copy max for non-lands
                if not is_basic_land and deck_card.quantity > 1:
                    logger.info(f"Commander singleton: '{card.name}' had {deck_card.quantity} copies, capping at 1")
                    deck_card.quantity = 1
            else:
                # Standard copy limits (basic lands are exempt)
                if is_basic_land:
                    # Basic lands can have unlimited copies
                    continue
                
                copy_limit = FormatRules.get_copy_limit(format_name)
                legendary_max = FormatRules.get_legendary_max(format_name)

                if is_legendary and deck_card.quantity > legendary_max:
                    logger.info(f"Legendary card '{card.name}' had {deck_card.quantity} copies, capping at {legendary_max}")
                    deck_card.quantity = legendary_max
                elif deck_card.quantity > copy_limit:
                    logger.info(f"Non-legendary card '{card.name}' had {deck_card.quantity} copies, capping at {copy_limit}")
                    deck_card.quantity = copy_limit

        return deck
