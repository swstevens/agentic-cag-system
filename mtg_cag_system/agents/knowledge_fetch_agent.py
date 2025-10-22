from typing import Dict, Any, Optional, List
import os
from pydantic_ai import Agent
from .base_agent import BaseAgent
from ..models.agent import AgentType
from ..models.response import AgentResponse
from ..services.card_lookup_service import CardLookupService
from ..models.card import MTGCard


class KnowledgeFetchAgent(BaseAgent):
    """Agent for fetching card data from two-tier card lookup system"""

    def __init__(self, card_lookup_service: CardLookupService, model_name: str = "openai:gpt-4", api_key: Optional[str] = None):
        super().__init__(AgentType.KNOWLEDGE_FETCH, model_name)

        # Public: Card lookup service (users may need to access this)
        self.card_lookup = card_lookup_service

        # Set API key in environment if provided
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        # Protected: Pydantic AI agent ONLY for card name extraction (used internally)
        self._pydantic_agent = Agent(
            model_name,
            system_prompt="""You are a card name extraction agent.
            Extract Magic: The Gathering card names from user queries.
            Be precise and only extract actual card names."""
        )

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Fetch card data using two-tier lookup (Public API)
        
        Returns ONLY MTGCard schema data, no generated text.
        """
        self.update_state("processing", "Fetching cards")

        query = input_data.get("query", "")
        use_fuzzy = input_data.get("use_fuzzy", False)

        try:
            # Step 1: Use LLM to extract card names from the query
            card_names = await self._extract_card_names(query)
            print(f"[Knowledge Agent] Extracted card names: {card_names}")

            # Step 2: Lookup cards using two-tier system
            relevant_cards = []
            lookup_trace = []

            for card_name in card_names:
                # Try exact match first (CAG cache → Database)
                card = self.card_lookup.get_card(card_name)

                if card:
                    relevant_cards.append(card)
                    lookup_trace.append(f"Found '{card_name}' via exact match")
                elif use_fuzzy:
                    # Fallback: fuzzy search
                    fuzzy_results = self.card_lookup.fuzzy_search(card_name, limit=3)
                    if fuzzy_results:
                        relevant_cards.extend(fuzzy_results)
                        lookup_trace.append(f"Found {len(fuzzy_results)} fuzzy matches for '{card_name}'")
                    else:
                        lookup_trace.append(f"No matches found for '{card_name}'")
                else:
                    lookup_trace.append(f"No exact match for '{card_name}'")

            self.update_state("completed")

            # Get lookup statistics
            lookup_stats = self.card_lookup.get_stats()

            # Format a readable answer for the user
            answer_parts = []
            if relevant_cards:
                if len(relevant_cards) == 1:
                    # Single card lookup - show detailed info
                    card = relevant_cards[0]
                    answer_parts.append(f"**{card.name}** {card.mana_cost or ''}")
                    answer_parts.append(f"{card.type_line}")
                    if card.oracle_text:
                        answer_parts.append(f"\n{card.oracle_text}")
                    if card.power and card.toughness:
                        answer_parts.append(f"\n{card.power}/{card.toughness}")
                    answer_parts.append(f"\n*{card.set_code.upper()} - {card.rarity}*")
                else:
                    # Multiple cards - show list with brief info
                    answer_parts.append(f"Found {len(relevant_cards)} card(s):\n")
                    for card in relevant_cards:
                        answer_parts.append(f"• **{card.name}** ({card.mana_cost or 'No cost'}) - {card.type_line}")
            else:
                answer_parts.append(f"No cards found matching: {', '.join(card_names)}")

            formatted_answer = "\n".join(answer_parts)

            # Return ONLY the card data (MTGCard schema)
            return AgentResponse(
                agent_type=self.agent_type.value,
                success=True,
                data={
                    "cards": [c.dict() for c in relevant_cards],
                    "extracted_card_names": card_names,
                    "lookup_stats": lookup_stats,
                    "answer": formatted_answer  # Add formatted answer
                },
                confidence=1.0 if relevant_cards else 0.0,
                reasoning_trace=lookup_trace + [
                    f"Extracted {len(card_names)} card names from query",
                    f"Found {len(relevant_cards)} cards total",
                    f"Tier 1 hits: {lookup_stats['tier1_hits']}",
                    f"Tier 2 hits: {lookup_stats['tier2_hits']}"
                ]
            )

        except Exception as e:
            self.update_state("error")
            import traceback
            traceback.print_exc()
            return AgentResponse(
                agent_type=self.agent_type.value,
                success=False,
                data={},
                confidence=0.0,
                error=str(e)
            )

    async def _extract_card_names(self, query: str) -> List[str]:
        """Use LLM to extract MTG card names from natural language query (Protected - internal helper)"""
        extraction_prompt = f"""Extract all Magic: The Gathering card names from this query.
Return ONLY a comma-separated list of card names, or "NONE" if no card names are mentioned.

Examples:
Query: "Tell me about Lightning Bolt"
Card names: Lightning Bolt

Query: "How do Lightning Bolt and Counterspell interact?"
Card names: Lightning Bolt, Counterspell

Query: "What's a good red aggro deck?"
Card names: NONE

Now extract from this query:
Query: {query}

Card names:"""

        try:
            result = await self._pydantic_agent.run(extraction_prompt)

            # Extract the actual LLM response text
            # pydantic-ai returns result.data which contains the actual string
            if hasattr(result, 'data'):
                response = result.data
            else:
                response = str(result)

            # If response is still an object/wrapper, try to extract the string
            response_str = str(response)

            # Handle AgentRunResult wrapper format: "AgentRunResult(output='...')"
            if "AgentRunResult(output=" in response_str:
                import re
                match = re.search(r"output='([^']*)'", response_str)
                if match:
                    response_str = match.group(1)
                else:
                    # Try with double quotes
                    match = re.search(r'output="([^"]*)"', response_str)
                    if match:
                        response_str = match.group(1)

            # Clean up the response - remove any wrapper text
            response_str = response_str.strip()

            # Remove common prefixes
            for prefix in ["Card names:", "Cards:", "Answer:"]:
                if response_str.startswith(prefix):
                    response_str = response_str[len(prefix):].strip()

            # Parse the response
            if response_str.upper() == "NONE" or not response_str:
                return []

            # Split by comma and clean up
            card_names = [name.strip() for name in response_str.split(',')]
            card_names = [name for name in card_names if name and len(name) > 2]

            return card_names
        except Exception as e:
            # Fallback: try basic keyword extraction
            print(f"Card name extraction failed: {e}")
            return []
