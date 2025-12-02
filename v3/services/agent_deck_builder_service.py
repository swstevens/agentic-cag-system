"""
Agent-based Deck Builder Service for V3 architecture.

Uses LLM reasoning with tool-calling to make intelligent decisions
about deck construction and refinement.
"""

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
        model_name: str = "openai:gpt-4o"
    ):
        """
        Initialize agent deck builder.
        
        Args:
            card_repository: Card repository for data access
            model_name: LLM model to use
        """
        self.card_repo = card_repository
        self.current_request = None  # Store current request for tool access
        
        # Create agent for initial deck building
        self.build_agent = Agent(
            model_name,
            output_type=DeckConstructionPlan,
            system_prompt="""You are an expert Magic: The Gathering deck builder.

Your goal is to construct competitive decks by intelligently selecting cards
that work well together and fit the requested archetype.

You have access to tools to search the card database. Use them strategically:
1. Use 'semantic_query' to find cards by concept, effect, or vibe (e.g., "aggressive goblins", "removal that exiles")
2. Use filters (colors, cmc, types) for hard constraints
3. Look for synergies between cards
4. Ensure proper land ratio and color distribution

For each card selection, provide clear reasoning about WHY it fits the deck.

Archetype guidelines:
- Aggro: Low curve (1-3 CMC), efficient creatures, 22-24 lands
- Midrange: Balanced curve (2-4 CMC), value cards, 24-26 lands  
- Control: Higher curve (2-5 CMC), removal/counters, 26-28 lands
- Combo: Focused on combo pieces, tutors, protection, 22-25 lands
"""
        )
        
        # Create agent for deck refinement
        self.refine_agent = Agent(
            model_name,
            output_type=RefinementPlan,
            system_prompt="""You are an expert Magic: The Gathering deck optimizer.

Your goal is to improve existing decks by identifying weaknesses and
making targeted improvements.

Analyze the current deck and improvement suggestions, then decide:
1. Which cards to remove (and why they're weak)
2. Which cards to add (and why they're better)
3. How to improve mana curve, synergy, or consistency

IMPORTANT RULES:
- LEGENDARY RULE: Legendary cards (marked with is_legendary: true) can only have 1 copy on the battlefield at a time
  - Typically include 2-3 copies in the deck for consistency/redundancy
  - Never recommend more than 3 copies of any legendary card
- Non-legendary cards: Use 3-4 copies for consistency, avoid excessive 1-ofs unless situational

Be specific and strategic. Focus on high-impact changes.
"""
        )
        
        # Register tools
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
        prompt = f"""Build a {request.archetype} deck for {request.format}.

Colors: {', '.join(request.colors)}
Strategy: {request.strategy}

IMPORTANT: 
- You only need to select SPELL cards (creatures, instants, sorceries, etc.)
- Lands will be added automatically (22 for aggro, 24 for midrange, 26 for control)
- Focus on CONSISTENCY: Use 3-4 copies of your best cards
- LEGENDARY RULE: Legendary cards (marked with is_legendary: true) should use 2-3 copies max
- Avoid 1-ofs unless the card is legendary or highly situational

Use the search_cards tool to find appropriate cards. 
- Use semantic_query for high-level concepts (e.g. "synergistic goblin cards", "cheap removal")
- Use standard filters for specific constraints

Build a focused, consistent spell suite with clear synergies.
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
            print(f"Agent deck building failed: {e}")
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

        target_size = request.deck_size if request.deck_size > 0 else 60
        prompt += f"\nIMPORTANT CONSTRAINTS:"
        prompt += f"\n- Current deck size is {deck.total_cards}. Target size is {target_size}."
        prompt += "\n- If current < target, you MUST add more cards than you remove."
        prompt += "\n- If current > target, you MUST remove more cards than you add."
        prompt += "\n- If current == target, you MUST add and remove equal amounts."
        prompt += "\n- For legendary cards (marked with is_legendary: true in search results): max 2-3 copies"
        prompt += "\n- For non-legendary cards: prefer 3-4 copies for consistency"
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
            print(f"Agent deck refinement failed: {e}")
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
        print(f"Executing construction plan: {plan.strategy}")
        
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
        
        print(f"Target deck size: {target_size}")
        print(f"Land count: {land_count}")
        print(f"Spell slots: {target_size - land_count}")
        
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
                print(f"Reached spell slot limit ({spell_slots}), stopping card additions")
                break
                
            # CardSelection is now a proper model with attributes
            card_name = selection.card_name
            quantity = selection.quantity
            
            if not card_name:
                print(f"Warning: Selection {i} missing card_name: {selection}")
                continue
            
            # Don't exceed remaining slots
            quantity = min(quantity, spell_slots - cards_added)
            
            # Get card from repository
            card = self.card_repo.get_by_name(card_name)
            if card:
                # Skip lands (we already added them)
                if "Land" not in card.types:
                    print(f"Adding {quantity}x {card_name}")
                    deck.cards.append(DeckCard(card=card, quantity=quantity))
                    cards_added += quantity
            else:
                print(f"Warning: Card '{card_name}' not found in repository")
        
        # STEP 3: Fill remaining slots if needed
        if cards_added < spell_slots:
            remaining = spell_slots - cards_added
            print(f"Warning: Only {cards_added}/{spell_slots} spell slots filled by LLM")
            print(f"Filling {remaining} remaining slots with basic creatures/spells")
            
            # Try to find some basic cards to fill slots
            # This is a fallback - ideally the LLM should provide enough cards
            if request.colors:
                # Get format-specific copy limit
                copy_limit = FormatRules.get_copy_limit(request.format)

                # Search for basic creatures in the deck's colors
                filters = CardSearchFilters(
                    colors=request.colors,
                    types=["Creature"],
                    cmc_max=3.0,
                    format_legal=request.format,
                    limit=50  # Get more candidates
                )
                filler_cards = self.card_repo.search(filters)

                # Add cards until we fill all remaining slots
                card_index = 0
                while remaining > 0 and card_index < len(filler_cards):
                    filler_card = filler_cards[card_index]
                    # Add copies based on format copy limit
                    qty = min(copy_limit, remaining)
                    deck.cards.append(DeckCard(card=filler_card, quantity=qty))
                    remaining -= qty
                    print(f"Filler: Adding {qty}x {filler_card.name}")
                    card_index += 1
                
                # If still not enough, add more lands
                if remaining > 0:
                    print(f"Warning: Still {remaining} slots unfilled. Adding more lands.")
                    # Add to the first land type
                    if deck.cards and "Land" in deck.cards[0].card.types:
                        deck.cards[0].quantity += remaining
        
        # Validate card quantities based on format rules
        deck = self._validate_legendary_quantities(deck, request.format)

        deck.calculate_totals()
        print(f"Deck built: {deck.total_cards} cards (target: {target_size})")

        # Final validation
        if deck.total_cards != target_size:
            print(f"ERROR: Deck size mismatch! Got {deck.total_cards}, expected {target_size}")

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
        print(f"Executing refinement plan: {plan.analysis[:100]}...")
        print(f"Actions: {len(plan.actions)}")
        
        for action in plan.actions:
            print(f"Action: {action.type} {action.quantity}x {action.card_name} - {action.reasoning[:50]}...")
            
            if action.type == "remove":
                deck = self._remove_card(deck, action.card_name, action.quantity)
            elif action.type == "add":
                deck = self._add_card(deck, action.card_name, action.quantity)
        
        deck.calculate_totals()

        # POST-REFINEMENT SIZE CORRECTION
        target_size = FormatRules.get_deck_size(request.format)

        if deck.total_cards < target_size:
            shortage = target_size - deck.total_cards
            print(f"Warning: Deck is {shortage} cards short. Adding filler creatures...")

            # Get format-specific copy limit
            copy_limit = FormatRules.get_copy_limit(request.format)

            # Search for basic creatures in the deck's colors
            if request.colors:
                filters = CardSearchFilters(
                    colors=request.colors,
                    types=["Creature"],
                    cmc_max=3.0,
                    format_legal=request.format,
                    limit=20
                )
                filler_cards = self.card_repo.search(filters)

                # Add cards until we reach target size
                card_index = 0
                while shortage > 0 and card_index < len(filler_cards):
                    filler_card = filler_cards[card_index]
                    # Check if card is already in deck
                    existing = next((dc for dc in deck.cards if dc.card.name == filler_card.name), None)
                    if existing:
                        # Increase quantity of existing card (respecting copy limit)
                        qty = min(copy_limit - existing.quantity, shortage)
                        if qty > 0:
                            existing.quantity += qty
                            shortage -= qty
                            print(f"Filler: Increasing {filler_card.name} by {qty}")
                    else:
                        # Add new card (respecting copy limit)
                        qty = min(copy_limit, shortage)
                        deck.cards.append(DeckCard(card=filler_card, quantity=qty))
                        shortage -= qty
                        print(f"Filler: Adding {qty}x {filler_card.name}")
                    card_index += 1
                
                # If still short, add more lands
                if shortage > 0:
                    print(f"Still {shortage} cards short. Adding lands...")
                    for dc in deck.cards:
                        if "Land" in dc.card.types:
                            dc.quantity += shortage
                            break
        
        elif deck.total_cards > target_size:
            excess = deck.total_cards - target_size
            print(f"Warning: Deck has {excess} excess cards. Trimming...")
            
            # Remove excess cards (prioritize 1-ofs and 2-ofs)
            deck.cards.sort(key=lambda dc: dc.quantity)  # Sort by quantity ascending
            
            for dc in deck.cards:
                if excess <= 0:
                    break
                if "Land" not in dc.card.types:  # Don't trim lands
                    to_remove = min(dc.quantity, excess)
                    dc.quantity -= to_remove
                    excess -= to_remove
                    print(f"Trimming: Removing {to_remove}x {dc.card.name}")
            
            # Remove cards with 0 quantity
            deck.cards = [dc for dc in deck.cards if dc.quantity > 0]
        
        # Validate card quantities based on format rules before returning
        deck = self._validate_legendary_quantities(deck, request.format)

        deck.calculate_totals()
        print(f"Final deck size after correction: {deck.total_cards}")

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
                    print(f"Commander singleton: '{card.name}' had {deck_card.quantity} copies, capping at 1")
                    deck_card.quantity = 1
            else:
                # Standard copy limits
                copy_limit = FormatRules.get_copy_limit(format_name)
                legendary_max = FormatRules.get_legendary_max(format_name)

                if is_legendary and deck_card.quantity > legendary_max:
                    print(f"Legendary card '{card.name}' had {deck_card.quantity} copies, capping at {legendary_max}")
                    deck_card.quantity = legendary_max
                elif not is_legendary and deck_card.quantity > copy_limit:
                    print(f"Non-legendary card '{card.name}' had {deck_card.quantity} copies, capping at {copy_limit}")
                    deck_card.quantity = copy_limit

        return deck
