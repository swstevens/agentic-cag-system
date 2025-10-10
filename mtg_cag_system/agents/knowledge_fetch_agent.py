from typing import Dict, Any, Optional
import os
from pydantic_ai import Agent
from .base_agent import BaseAgent
from ..models.agent import AgentType
from ..models.response import AgentResponse
from ..services.knowledge_service import KnowledgeService


class KnowledgeFetchAgent(BaseAgent):
    """Agent for fetching knowledge from CAG system"""

    def __init__(self, knowledge_service: KnowledgeService, model_name: str = "openai:gpt-4", api_key: Optional[str] = None):
        super().__init__(AgentType.KNOWLEDGE_FETCH, model_name)
        self.knowledge_service = knowledge_service

        # Set API key in environment if provided
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        # Pydantic AI agent for interpreting card data
        self._pydantic_agent = Agent(
            model_name,
            system_prompt="""You are a knowledge retrieval agent for MTG cards.
            You have access to preloaded card data in your context.
            Extract and present relevant card information clearly and accurately.
            Focus on card interactions, synergies, and deck-building advice."""
        )

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Fetch relevant knowledge from CAG"""
        self.update_state("processing", "Fetching knowledge")

        query = input_data.get("query", "")
        filters = input_data.get("filters", {})

        try:
            # Get cards from knowledge service (CAG approach - preloaded)
            relevant_cards = self.knowledge_service.search_cards(query, filters)

            # Get full context
            context = self.knowledge_service.get_context_for_query(query)

            # Use Pydantic AI agent to interpret and respond
            result = await self._pydantic_agent.run(
                f"Query: {query}\n\n"
                f"Preloaded Context Available: {len(context)} characters\n"
                f"Found {len(relevant_cards)} relevant cards\n\n"
                f"Provide a helpful response based on the preloaded card knowledge."
            )

            self.update_state("completed")

            # Extract answer from result
            answer_text = str(result.data) if hasattr(result, 'data') else str(result)

            return AgentResponse(
                agent_type=self.agent_type.value,
                success=True,
                data={
                    "cards": [c.dict() for c in relevant_cards],
                    "answer": answer_text,
                    "context_size": len(context)
                },
                confidence=0.85,
                reasoning_trace=[f"Found {len(relevant_cards)} cards", "Used CAG preloaded context"]
            )

        except Exception as e:
            self.update_state("error")
            return AgentResponse(
                agent_type=self.agent_type.value,
                success=False,
                data={},
                confidence=0.0,
                error=str(e)
            )
