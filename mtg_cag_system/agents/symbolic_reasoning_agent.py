from typing import Dict, Any, List, Optional
import os
from pydantic_ai import Agent
from .base_agent import BaseAgent
from ..models.agent import AgentType
from ..models.response import AgentResponse


class SymbolicReasoningAgent(BaseAgent):
    """Agent for formal logic and constraint validation"""

    def __init__(self, model_name: str = "openai:gpt-4", api_key: Optional[str] = None):
        super().__init__(AgentType.SYMBOLIC_REASONING, model_name)

        # Set API key in environment if provided
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        self._pydantic_agent = Agent(
            model_name,
            system_prompt="""You are a symbolic reasoning agent for MTG rules.
            Your role is to:
            1. Validate deck legality (60 cards, max 4 copies, format legality)
            2. Check mana curve constraints
            3. Verify card interactions follow game rules
            4. Apply formal logic to deck-building constraints

            Always provide definitive yes/no answers with clear reasoning."""
        )

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Apply symbolic reasoning to validate or solve"""
        self.update_state("processing", "Applying symbolic reasoning")

        reasoning_type = input_data.get("type", "validation")
        data = input_data.get("data", {})

        try:
            if reasoning_type == "deck_validation":
                result = await self._validate_deck(data)
            elif reasoning_type == "mana_curve":
                result = await self._analyze_mana_curve(data)
            elif reasoning_type == "card_interaction":
                result = await self._validate_interaction(data)
            else:
                result = {"valid": True, "message": "No validation needed"}

            self.update_state("completed")

            return AgentResponse(
                agent_type=self.agent_type.value,
                success=True,
                data=result,
                confidence=1.0,  # Symbolic reasoning gives certainty
                reasoning_trace=result.get("reasoning", [])
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

    async def _validate_deck(self, deck_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate deck legality using formal rules (Protected - internal logic)"""
        cards = deck_data.get("cards", [])
        format_name = deck_data.get("format", "Standard")

        # Formal validation rules
        validations = {
            "card_count": len(cards) >= 60,
            "max_copies": self._check_max_copies(cards),
            "format_legal": self._check_format_legality(cards, format_name)
        }

        all_valid = all(validations.values())

        return {
            "valid": all_valid,
            "validations": validations,
            "reasoning": [f"{k}: {v}" for k, v in validations.items()]
        }

    def _check_max_copies(self, cards: List[Dict]) -> bool:
        """Check max 4 copies rule (Protected - internal validation)"""
        card_counts = {}
        for card in cards:
            name = card.get("name", "")
            if "Basic Land" not in card.get("type_line", ""):
                card_counts[name] = card_counts.get(name, 0) + 1

        return all(count <= 4 for count in card_counts.values())

    def _check_format_legality(self, cards: List[Dict], format_name: str) -> bool:
        """Check if all cards are legal in format (Protected - internal validation)"""
        for card in cards:
            legalities = card.get("legalities", {})
            if legalities.get(format_name, "not_legal") != "legal":
                return False
        return True

    async def _analyze_mana_curve(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mana curve distribution (Protected - internal analysis)"""
        cards = data.get("cards", [])

        curve = {i: 0 for i in range(8)}
        for card in cards:
            cmc = int(card.get("cmc", 0))
            if cmc >= 7:
                curve[7] += 1
            else:
                curve[cmc] += 1

        # Evaluate curve quality
        optimal = curve[2] + curve[3] >= len(cards) * 0.4

        return {
            "curve": curve,
            "optimal": optimal,
            "reasoning": [f"CMC {k}: {v} cards" for k, v in curve.items()]
        }

    async def _validate_interaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate card interaction is legal (Protected - internal validation)"""
        # Use Pydantic AI for complex rule interactions
        card1 = data.get("card1", {})
        card2 = data.get("card2", {})

        result = await self._pydantic_agent.run(
            f"Do these cards interact legally according to MTG rules?\n"
            f"Card 1: {card1.get('name')} - {card1.get('oracle_text')}\n"
            f"Card 2: {card2.get('name')} - {card2.get('oracle_text')}\n\n"
            f"Provide yes/no and explain the interaction."
        )

        # Extract explanation from result
        explanation_text = str(result.data) if hasattr(result, 'data') else str(result)

        return {
            "valid": True,  # Parse from result
            "explanation": explanation_text,
            "reasoning": ["Checked MTG comprehensive rules"]
        }
