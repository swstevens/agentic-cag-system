from typing import Dict, Any, List, Optional
import json
import os
from pydantic_ai import Agent
from .base_agent import BaseAgent
from ..models.agent import AgentType
from ..models.response import AgentResponse


class SchedulingAgent(BaseAgent):
    """Agent responsible for planning and scheduling multi-step workflows"""

    def __init__(self, model_name: str = "openai:gpt-4", api_key: Optional[str] = None):
        super().__init__(AgentType.SCHEDULING, model_name)

        # Set API key in environment if provided
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        # Create Pydantic AI agent
        self._pydantic_agent = Agent(
            model_name,
            system_prompt="""You are a scheduling agent for an MTG deck-building assistant.
            Your role is to:
            1. Break down complex queries into steps
            2. Coordinate between knowledge fetch and reasoning agents
            3. Maintain conversation flow
            4. Plan multi-step deck building processes

            Always provide structured, step-by-step plans."""
        )

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process query and create execution plan"""
        self.update_state("processing", "Creating execution plan")

        query = input_data.get("query", "")
        context = input_data.get("context", {})

        try:
            # Use Pydantic AI agent to analyze and plan
            result = await self._pydantic_agent.run(
                f"Query: {query}\nContext: {json.dumps(context)}\n\n"
                f"Create a step-by-step plan to answer this query about MTG deck building."
            )

            # Parse plan into structured steps
            # pydantic-ai returns a RunResult object, access the data via .data attribute
            plan_text = str(result.data) if hasattr(result, 'data') else str(result)
            plan = self._parse_plan(plan_text)

            self.update_state("completed")

            return AgentResponse(
                agent_type=self.agent_type.value,
                success=True,
                data={"plan": plan, "requires_knowledge": True},
                confidence=0.9,
                reasoning_trace=[f"Created {len(plan)} step plan"]
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

    def _parse_plan(self, plan_text: str) -> List[Dict[str, str]]:
        """Parse plan text into structured steps"""
        # Simple parsing - in production would be more sophisticated
        steps = []
        for i, line in enumerate(plan_text.split('\n')):
            if line.strip():
                steps.append({
                    "step_number": i + 1,
                    "action": line.strip(),
                    "status": "pending"
                })
        return steps
