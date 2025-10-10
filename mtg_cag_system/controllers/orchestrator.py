from typing import Dict, Any
from ..agents.scheduling_agent import SchedulingAgent
from ..agents.knowledge_fetch_agent import KnowledgeFetchAgent
from ..agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from ..services.cache_service import MultiTierCache
from ..models.query import UserQuery
from ..models.response import FusedResponse, AgentResponse
from ..models.agent import ReasoningChain, ReasoningStep, AgentType


class AgentOrchestrator:
    """Orchestrates multiple agents to answer queries"""

    def __init__(
        self,
        scheduling_agent: SchedulingAgent,
        knowledge_agent: KnowledgeFetchAgent,
        symbolic_agent: SymbolicReasoningAgent,
        cache: MultiTierCache
    ):
        self.scheduling_agent = scheduling_agent
        self.knowledge_agent = knowledge_agent
        self.symbolic_agent = symbolic_agent
        self.cache = cache

    async def process_query(self, query: UserQuery) -> FusedResponse:
        """Process query through agent pipeline"""
        reasoning_chain = ReasoningChain(query_id=query.query_id)
        agent_responses = {}

        try:
            # Step 1: Scheduling agent creates plan
            schedule_input = {
                "query": query.query_text,
                "context": query.context
            }
            schedule_response = await self.scheduling_agent.process(schedule_input)
            agent_responses["scheduling"] = schedule_response

            reasoning_chain.add_step(ReasoningStep(
                agent_type=AgentType.SCHEDULING,
                action="create_plan",
                input_data=schedule_input,
                output_data=schedule_response.data,
                confidence=schedule_response.confidence
            ))

            # Step 2: Knowledge fetch agent retrieves cards
            knowledge_input = {
                "query": query.query_text,
                "filters": query.context.get("filters", {})
            }
            knowledge_response = await self.knowledge_agent.process(knowledge_input)
            agent_responses["knowledge"] = knowledge_response

            reasoning_chain.add_step(ReasoningStep(
                agent_type=AgentType.KNOWLEDGE_FETCH,
                action="fetch_cards",
                input_data=knowledge_input,
                output_data=knowledge_response.data,
                confidence=knowledge_response.confidence
            ))

            # Step 3: Symbolic reasoning (if needed)
            if query.intent and query.intent.requires_symbolic_reasoning:
                symbolic_input = {
                    "type": "deck_validation",
                    "data": knowledge_response.data
                }
                symbolic_response = await self.symbolic_agent.process(symbolic_input)
                agent_responses["symbolic"] = symbolic_response

                reasoning_chain.add_step(ReasoningStep(
                    agent_type=AgentType.SYMBOLIC_REASONING,
                    action="validate",
                    input_data=symbolic_input,
                    output_data=symbolic_response.data,
                    confidence=symbolic_response.confidence
                ))

            # Step 4: Fuse results
            fused_answer = await self._fuse_results(agent_responses, query)

            return FusedResponse(
                query_id=query.query_id,
                session_id=query.session_id,
                answer=fused_answer["answer"],
                confidence=reasoning_chain.total_confidence,
                sources=fused_answer["sources"],
                agent_contributions=agent_responses,
                reasoning_chain=[s.dict() for s in reasoning_chain.steps],
                metadata={"cache_stats": self.cache.get_stats()}
            )

        except Exception as e:
            return FusedResponse(
                query_id=query.query_id,
                session_id=query.session_id,
                answer=f"Error processing query: {str(e)}",
                confidence=0.0,
                sources=[],
                agent_contributions=agent_responses,
                metadata={"error": str(e)}
            )

    async def _fuse_results(
        self,
        agent_responses: Dict[str, AgentResponse],
        query: UserQuery
    ) -> Dict[str, Any]:
        """Fuse responses from multiple agents"""
        # Combine knowledge and validation results
        answer_parts = []
        sources = []

        if "knowledge" in agent_responses and agent_responses["knowledge"].success:
            knowledge_data = agent_responses["knowledge"].data
            answer_parts.append(knowledge_data.get("answer", ""))

            # Add card sources
            cards = knowledge_data.get("cards", [])
            sources.extend([c["name"] for c in cards[:5]])  # Top 5 cards

        if "symbolic" in agent_responses and agent_responses["symbolic"].success:
            symbolic_data = agent_responses["symbolic"].data
            if not symbolic_data.get("valid", True):
                answer_parts.append(
                    f"\nValidation: {symbolic_data.get('reasoning', [])}"
                )

        return {
            "answer": "\n\n".join(answer_parts),
            "sources": sources
        }
