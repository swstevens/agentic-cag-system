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
        # Public: Agent instances (users may need to access these)
        self.scheduling_agent = scheduling_agent
        self.knowledge_agent = knowledge_agent
        self.symbolic_agent = symbolic_agent

        # Public: Cache service (users may need to access this)
        self.cache = cache

        # Initialize deck builder service
        from ..services.deck_builder_service import DeckBuilderService
        self.deck_builder = DeckBuilderService(
            knowledge_agent=knowledge_agent,
            symbolic_agent=symbolic_agent,
            card_lookup=knowledge_agent.card_lookup  # Use the CardLookupService instance from KnowledgeFetchAgent
        )

        # Initialize synergy lookup service
        from ..services.synergy_lookup_service import SynergyLookupService
        self.synergy_lookup_service = SynergyLookupService(
            vector_store=knowledge_agent.vector_store,
            card_lookup=knowledge_agent.card_lookup
        )

    async def process_query(self, query: UserQuery) -> FusedResponse:
        """Process query through agent pipeline (Public API)"""
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

            # Step 2: Based on scheduling agent's plan, choose appropriate processing path
            query_type = schedule_response.data.get("query_type", "card_info")
            
            if query_type == "deck_building":
                # Use deck builder service for deck building queries
                # Extract format with proper case handling
                format_name = schedule_response.data.get("format", query.context.get("format", "Standard"))
                # Ensure proper case for well-known formats
                format_map = {
                    "standard": "Standard",
                    "modern": "Modern",
                    "legacy": "Legacy",
                    "vintage": "Vintage",
                    "commander": "Commander",
                    "pioneer": "Pioneer"
                }
                format_name = format_map.get(format_name.lower(), format_name)
                
                deck_requirements = {
                    "query": query.query_text,
                    "format": format_name,
                    "colors": schedule_response.data.get("colors", query.context.get("colors", [])),
                    "strategy": schedule_response.data.get("strategy", ""),
                    "budget": query.context.get("budget", None)
                }
                
                deck_response = await self.deck_builder.build_deck(deck_requirements)
                agent_responses["deck_builder"] = AgentResponse(
                    agent_type="deck_builder",
                    success=True,
                    data=deck_response,
                    confidence=0.9,
                    reasoning_trace=[
                        "Analyzed deck requirements",
                        "Generated initial deck list",
                        "Validated deck composition",
                        "Applied deck building best practices"
                    ]
                )
                
                reasoning_chain.add_step(ReasoningStep(
                    agent_type=AgentType.KNOWLEDGE_FETCH,
                    action="build_deck",
                    input_data=deck_requirements,
                    output_data=deck_response,
                    confidence=0.9
                ))
                
            else:
                # Use knowledge fetch agent for card information queries
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
        """Fuse responses from multiple agents (Protected - internal fusion logic)"""
        answer_parts = []
        sources = []

        # Handle deck building responses
        if "deck_builder" in agent_responses and agent_responses["deck_builder"].success:
            deck_data = agent_responses["deck_builder"].data

            # Format deck data for display
            deck_cards = deck_data.get("deck", [])

            # Count cards by name
            card_counts = {}
            for card in deck_cards:
                card_name = card.get("name", "Unknown")
                card_counts[card_name] = card_counts.get(card_name, 0) + 1

            # Format the deck list
            formatted_deck = []
            formatted_deck.append("Main Deck:")
            for card_name, count in sorted(card_counts.items()):
                formatted_deck.append(f"{count}x {card_name}")

            # Add deck summary
            deck_size = deck_data.get("deck_size", len(deck_cards))
            valid = deck_data.get("valid", False)

            answer_parts.append(f"Here's the deck I built ({deck_size} cards, {'Valid' if valid else 'Invalid'}):")
            answer_parts.append("\n".join(formatted_deck))

            # Add validation info
            validation = deck_data.get("validation", {})
            if validation:
                answer_parts.append(f"\nValidation: {validation.get('validations', {})}")

            # Add sources (top 5 unique cards)
            sources.extend(list(card_counts.keys())[:5])

        # Handle regular card knowledge responses
        elif "knowledge" in agent_responses and agent_responses["knowledge"].success:
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
