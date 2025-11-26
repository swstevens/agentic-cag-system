"""
LLM-based deck analyzer using DeckAnalyzerAgent.

This is an Adapter Pattern implementation that wraps DeckAnalyzerAgent
to implement the IAnalyzer interface.
"""

from typing import List
from ..interfaces.analyzer import IAnalyzer, AnalysisContext
from ..models.card import MTGCard
from ..models.deck_analysis import DeckAnalysisResult
from ..models.requests import AnalysisRequest, DeckArchetype
from ..agents.deck_analyzer_agent import DeckAnalyzerAgent


class LLMDeckAnalyzer(IAnalyzer):
    """
    LLM-based deck analyzer implementation.

    Uses DeckAnalyzerAgent (Pydantic AI) for context-aware, intelligent analysis.
    This replaces rule-based decision trees with LLM reasoning.

    Adapter Pattern: Wraps DeckAnalyzerAgent to implement IAnalyzer interface.
    """

    def __init__(self, model_name: str = "openai:gpt-4", api_key: str = None):
        """
        Initialize LLM analyzer.

        Args:
            model_name: Model to use (e.g., "openai:gpt-4", "anthropic:claude-3-5-sonnet")
            api_key: Optional API key (defaults to environment variable)
        """
        self.agent = DeckAnalyzerAgent(model_name=model_name, api_key=api_key)

    async def analyze(
        self,
        cards: List[MTGCard],
        context: AnalysisContext
    ) -> DeckAnalysisResult:
        """
        Analyze a deck using LLM-based reasoning.

        Args:
            cards: List of cards in the deck
            context: Analysis context (archetype, format, target size, etc.)

        Returns:
            DeckAnalysisResult with comprehensive structured analysis
        """
        # Map archetype string to DeckArchetype enum
        archetype_mapping = {
            "aggro": DeckArchetype.AGGRO,
            "control": DeckArchetype.CONTROL,
            "midrange": DeckArchetype.MIDRANGE,
            "combo": DeckArchetype.COMBO,
            "tempo": DeckArchetype.TEMPO,
            "ramp": DeckArchetype.RAMP,
        }

        archetype_enum = archetype_mapping.get(
            context.archetype.lower(),
            DeckArchetype.MIDRANGE  # Default
        )

        # Create typed request
        request = AnalysisRequest(
            cards=cards,
            archetype=archetype_enum,
            format=context.format,
            deck_size=context.target_deck_size,
            context=context.metadata
        )

        # Process with agent
        agent_response = await self.agent.process(request.model_dump())

        # Extract DeckAnalysisResult from response
        if not agent_response.success:
            raise RuntimeError(f"Analysis failed: {agent_response.error}")

        # The agent response data contains the DeckAnalysisResult
        # We need to reconstruct it from the dict
        from ..models.deck_analysis import DeckAnalysisResult
        analysis_result = DeckAnalysisResult(**agent_response.data['analysis'])

        return analysis_result

    def get_agent_state(self):
        """Get the underlying agent's state for debugging/monitoring"""
        return self.agent.get_state()
