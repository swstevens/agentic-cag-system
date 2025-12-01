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
from ..database.card_repository import CardRepository


# Tool response models
class CardSearchResult(BaseModel):
    """Result from searching cards."""
    cards: List[Dict[str, Any]] = Field(description="List of cards found")
    count: int = Field(description="Number of cards found")


class DeckConstructionPlan(BaseModel):
    """LLM's plan for constructing a deck."""
    strategy: str = Field(description="Overall strategy for deck construction")
    land_count: int = Field(description="Number of lands to include")
    card_selections: List[Dict[str, Any]] = Field(
        description="List of card selections with card_name, quantity, and reasoning"
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
Deck size: {request.deck_size}
Strategy: {request.strategy}

Use the search_cards tool to find appropriate cards. 
- Use semantic_query for high-level concepts (e.g. "synergistic goblin cards", "cheap removal")
- Use standard filters for specific constraints

Build a complete deck with lands and spells that work well together.

Provide a construction plan with your reasoning.
"""
        
        try:
            result = await self.build_agent.run(prompt)
            plan: DeckConstructionPlan = result.output
            
            # Execute the plan
            deck = await self._execute_construction_plan(plan, request)
            return deck
            
        except Exception as e:
            print(f"Agent deck building failed: {e}")
            # Fallback to simple construction
            return self._fallback_build(request)
    
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
        
        prompt += "\nUse search_cards_refine to find better cards (use semantic_query for best results). Provide a refinement plan."
        
        try:
            result = await self.refine_agent.run(prompt)
            plan: RefinementPlan = result.output
            
            # Execute the refinement plan
            deck = await self._execute_refinement_plan(deck, plan, request)
            return deck
            
        except Exception as e:
            print(f"Agent deck refinement failed: {e}")
            # Fallback to simple refinement
            return deck
    
    async def _execute_construction_plan(
        self,
        plan: DeckConstructionPlan,
        request: DeckBuildRequest
    ) -> Deck:
        """Execute the LLM's construction plan."""
        print(f"Executing construction plan: {plan.strategy}")
        print(f"Land count: {plan.land_count}")
        print(f"Card selections: {len(plan.card_selections)} cards")
        
        deck = Deck(
            cards=[],
            format=request.format,
            archetype=request.archetype,
            colors=request.colors,
        )
        
        # Add cards from plan
        for i, selection in enumerate(plan.card_selections):
            card_name = selection.get("card_name")
            quantity = selection.get("quantity", 1)
            
            if not card_name:
                print(f"Warning: Selection {i} missing card_name: {selection}")
                continue
            
            print(f"Adding {quantity}x {card_name}")
            
            # Get card from repository
            card = self.card_repo.get_by_name(card_name)
            if card:
                deck.cards.append(DeckCard(card=card, quantity=quantity))
            else:
                print(f"Warning: Card '{card_name}' not found in repository")
        
        # Add lands based on plan.land_count
        if plan.land_count > 0 and request.colors:
            print(f"Adding {plan.land_count} lands")
            lands_per_color = plan.land_count // len(request.colors)
            remainder = plan.land_count % len(request.colors)
            
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
        
        deck.calculate_totals()
        print(f"Deck built: {deck.total_cards} cards")
        return deck
    
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
        return deck
    
    def _remove_card(self, deck: Deck, card_name: str, quantity: int) -> Deck:
        """Remove card from deck."""
        new_cards = []
        removed_count = 0
        
        for deck_card in deck.cards:
            if deck_card.card.name.lower() == card_name.lower():
                if removed_count < quantity:
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
            land_count = 24
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
                    quantity=land_count // len(request.colors)
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
