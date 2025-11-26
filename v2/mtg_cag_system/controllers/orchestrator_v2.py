"""
Refactored Agent Orchestrator (v2)

This version uses:
1. Typed request/response objects (Pydantic models)
2. Interface dependencies (IAgent, ICache)
3. Cleaner routing logic
4. Better separation of concerns

Changes from v1:
- Uses SchedulingRequest/Response instead of Dict
- Uses IAgent interface for all agents
- Cleaner deck building integration
- Typed throughout
"""

from typing import Dict, Any, Optional
from ..interfaces.agent import IAgent
from ..interfaces.cache import ICache
from ..models.query import UserQuery, QueryType
from ..models.response import FusedResponse, AgentResponse
from ..models.agent import ReasoningChain, ReasoningStep, AgentType
from ..models.requests import (
    SchedulingRequest,
    KnowledgeRequest,
    ReasoningRequest,
    AnalysisRequest
)
from ..models.responses import (
    SchedulingResponse,
    KnowledgeResponse,
    ReasoningResponse,
    AnalysisResponse
)
from ..services.deck_builder_service_v2 import DeckBuilderServiceV2
from datetime import datetime


class AgentOrchestratorV2:
    """
    Refactored orchestrator using typed requests and interface dependencies.

    Coordinates multiple agents to process user queries with full type safety.
    """

    def __init__(
        self,
        scheduling_agent: IAgent,
        knowledge_agent: IAgent,
        symbolic_agent: IAgent,
        cache: ICache,
        deck_builder: Optional[DeckBuilderServiceV2] = None
    ):
        """
        Initialize orchestrator with agent dependencies.

        Args:
            scheduling_agent: Agent for query classification (implements IAgent)
            knowledge_agent: Agent for card lookups (implements IAgent)
            symbolic_agent: Agent for validation/reasoning (implements IAgent)
            cache: Cache for query results (implements ICache)
            deck_builder: Optional deck building service
        """
        self.scheduling_agent = scheduling_agent
        self.knowledge_agent = knowledge_agent
        self.symbolic_agent = symbolic_agent
        self.cache = cache
        self.deck_builder = deck_builder

    async def process_query(self, query: UserQuery) -> FusedResponse:
        """
        Process user query through agent pipeline with typed requests.

        Args:
            query: UserQuery with query_text and context

        Returns:
            FusedResponse with answer, confidence, and reasoning chain
        """
        reasoning_chain = ReasoningChain(query_id=query.query_id)
        agent_responses: Dict[str, AgentResponse] = {}

        try:
            # Step 1: Schedule (classify query and extract requirements)
            schedule_request = SchedulingRequest(
                query_text=query.query_text,
                session_id=query.session_id,
                user_context=query.context
            )

            schedule_response = await self.scheduling_agent.process(schedule_request)
            agent_responses["scheduling"] = schedule_response

            # Parse scheduling response
            scheduling_data = SchedulingResponse(**schedule_response.data)

            reasoning_chain.add_step(ReasoningStep(
                agent_type=AgentType.SCHEDULING,
                action="classify_query",
                input_data=schedule_request.model_dump(),
                output_data=scheduling_data.model_dump(),
                confidence=schedule_response.confidence
            ))

            # Step 2: Route based on query type
            query_type = scheduling_data.query_type

            if query_type == QueryType.DECK_BUILDING:
                # Deck building path
                answer, confidence = await self._handle_deck_building(
                    query=query,
                    scheduling_data=scheduling_data,
                    reasoning_chain=reasoning_chain,
                    agent_responses=agent_responses
                )

            elif query_type in [QueryType.CARD_SEARCH, QueryType.CARD_INTERACTION]:
                # Card lookup path
                answer, confidence = await self._handle_card_lookup(
                    query=query,
                    scheduling_data=scheduling_data,
                    reasoning_chain=reasoning_chain,
                    agent_responses=agent_responses
                )

            else:
                # Fallback: treat as card search
                answer, confidence = await self._handle_card_lookup(
                    query=query,
                    scheduling_data=scheduling_data,
                    reasoning_chain=reasoning_chain,
                    agent_responses=agent_responses
                )

            # Build fused response
            return FusedResponse(
                query_id=query.query_id,
                session_id=query.session_id,
                answer=answer,
                confidence=confidence,
                sources=self._extract_sources(agent_responses),
                agent_contributions=agent_responses,
                reasoning_chain=[step.model_dump() for step in reasoning_chain.steps],
                metadata={
                    "query_type": query_type.value if isinstance(query_type, QueryType) else query_type,
                    "processing_time": datetime.now().isoformat()
                },
                timestamp=datetime.now()
            )

        except Exception as e:
            # Error handling
            return FusedResponse(
                query_id=query.query_id,
                session_id=query.session_id,
                answer=f"Error processing query: {str(e)}",
                confidence=0.0,
                sources=[],
                agent_contributions=agent_responses,
                reasoning_chain=[step.model_dump() for step in reasoning_chain.steps],
                metadata={"error": str(e)},
                timestamp=datetime.now()
            )

    async def _handle_deck_building(
        self,
        query: UserQuery,
        scheduling_data: SchedulingResponse,
        reasoning_chain: ReasoningChain,
        agent_responses: Dict[str, AgentResponse]
    ) -> tuple[str, float]:
        """
        Handle deck building queries.

        Args:
            query: User query
            scheduling_data: Parsed scheduling response
            reasoning_chain: Reasoning chain to update
            agent_responses: Agent responses dict to update

        Returns:
            Tuple of (answer text, confidence)
        """
        if not self.deck_builder:
            return "Deck building service not available", 0.0

        # Extract requirements
        requirements = scheduling_data.extracted_requirements
        colors = requirements.get("colors", [])
        archetype = requirements.get("strategy", "midrange")
        deck_format = requirements.get("format", "Standard")

        # Build deck
        deck_result = await self.deck_builder.build_deck(
            colors=colors,
            archetype=archetype,
            deck_format=deck_format
        )

        # Create response
        agent_responses["deck_builder"] = AgentResponse(
            agent_type="deck_builder",
            success=deck_result["is_valid"],
            data=deck_result,
            confidence=0.9 if deck_result["is_valid"] else 0.6,
            reasoning_trace=[
                "Extracted deck requirements",
                "Fetched matching cards",
                "Analyzed deck quality",
                "Validated deck composition"
            ]
        )

        reasoning_chain.add_step(ReasoningStep(
            agent_type=AgentType.KNOWLEDGE_FETCH,
            action="build_deck",
            input_data={"colors": colors, "archetype": archetype, "format": deck_format},
            output_data={"deck_size": deck_result["deck_size"]},
            confidence=0.9
        ))

        # Format answer
        deck_list = "\n".join([f"  {card.name}" for card in deck_result["deck"][:10]])
        answer = f"Built a {archetype} {deck_format} deck:\n{deck_list}\n... ({deck_result['deck_size']} cards total)"

        return answer, 0.9

    async def _handle_card_lookup(
        self,
        query: UserQuery,
        scheduling_data: SchedulingResponse,
        reasoning_chain: ReasoningChain,
        agent_responses: Dict[str, AgentResponse]
    ) -> tuple[str, float]:
        """
        Handle card lookup queries.

        Args:
            query: User query
            scheduling_data: Parsed scheduling response
            reasoning_chain: Reasoning chain to update
            agent_responses: Agent responses dict to update

        Returns:
            Tuple of (answer text, confidence)
        """
        # Create knowledge request
        knowledge_request = KnowledgeRequest(
            query_text=query.query_text,
            fuzzy_search=True
        )

        # Process with knowledge agent
        knowledge_response = await self.knowledge_agent.process(knowledge_request)
        agent_responses["knowledge"] = knowledge_response

        # Parse response
        knowledge_data = KnowledgeResponse(**knowledge_response.data)

        reasoning_chain.add_step(ReasoningStep(
            agent_type=AgentType.KNOWLEDGE_FETCH,
            action="lookup_cards",
            input_data=knowledge_request.model_dump(),
            output_data={
                "cards_found": len(knowledge_data.cards),
                "cache_hit_rate": knowledge_data.cache_hit_rate
            },
            confidence=knowledge_response.confidence
        ))

        # Format answer
        if knowledge_data.answer:
            answer = knowledge_data.answer
        elif knowledge_data.cards:
            card_list = "\n".join([
                f"  {card.name} - {card.type_line} ({card.mana_cost or 'N/A'})"
                for card in knowledge_data.cards[:5]
            ])
            answer = f"Found {len(knowledge_data.cards)} cards:\n{card_list}"
        else:
            answer = f"No cards found for: {query.query_text}"

        return answer, knowledge_response.confidence

    def _extract_sources(self, agent_responses: Dict[str, AgentResponse]) -> list[str]:
        """Extract source citations from agent responses."""
        sources = []
        for agent_type, response in agent_responses.items():
            if response.success:
                sources.append(f"{agent_type}_agent")
        return sources
