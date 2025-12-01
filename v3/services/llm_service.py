"""
LLM Service for V3 architecture.

Provides intelligent deck analysis and improvement suggestions
using Pydantic AI and OpenAI.
"""

import os
from typing import Optional, List
from pydantic_ai import Agent
from ..models.deck import Deck, DeckImprovementPlan, CardRemoval, CardSuggestion


class LLMService:
    """
    Service for LLM-based deck analysis.
    
    Uses Pydantic AI to generate structured improvement plans
    based on deck composition and archetype.
    """
    
    def __init__(self, model_name: str = "openai:gpt-4o", api_key: Optional[str] = None):
        """
        Initialize LLM service.
        
        Args:
            model_name: Model to use (default: gpt-4o)
            api_key: Optional API key (defaults to env var)
        """
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
            
        self.agent = Agent(
            model_name,
            output_type=DeckImprovementPlan,
            system_prompt="""You are an expert Magic: The Gathering deck builder.
            
            Your goal is to analyze a given deck and provide a concrete improvement plan.
            You must identify weak cards to remove and suggest better replacements.
            
            Focus on:
            1. Mana curve optimization
            2. Synergy and consistency
            3. Win conditions (finishers)
            4. Interaction/Removal
            
            For each removal, explain WHY it is weak or doesn't fit.
            For each addition, explain WHY it improves the deck.
            
            Be specific with card names.
            """
        )
    
    async def analyze_deck(self, deck: Deck) -> DeckImprovementPlan:
        """
        Analyze deck and generate improvement plan.
        
        Args:
            deck: Deck to analyze
            
        Returns:
            Structured improvement plan
        """
        # Format deck list for the prompt
        deck_list = []
        for deck_card in deck.cards:
            card = deck_card.card
            deck_list.append(
                f"{deck_card.quantity}x {card.name} "
                f"(CMC: {card.cmc}, Type: {card.type_line}, "
                f"Colors: {card.colors})"
            )
            
        prompt = f"""
        Analyze this {deck.format} {deck.archetype} deck:
        
        Colors: {', '.join(deck.colors)}
        
        Decklist:
        {chr(10).join(deck_list)}
        
        Provide a plan to improve this deck's competitiveness.
        Identify at least 2-3 cards to remove and replacements to add.
        """
        
        try:
            result = await self.agent.run(prompt)
            return result.output
        except Exception as e:
            # Fallback for errors (e.g., API issues)
            print(f"LLM Analysis failed: {e}")
            return DeckImprovementPlan(
                removals=[],
                additions=[],
                analysis=f"LLM analysis failed: {str(e)}"
            )

