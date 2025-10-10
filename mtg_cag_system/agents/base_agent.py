from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic_ai import Agent as PydanticAgent
from ..models.agent import AgentType, AgentState
from ..models.response import AgentResponse


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, agent_type: AgentType, model_name: str = "openai:gpt-4"):
        self.agent_type = agent_type
        self.state = AgentState(
            agent_id=f"{agent_type.value}_{datetime.now().timestamp()}",
            agent_type=agent_type
        )
        self.model_name = model_name
        self._pydantic_agent: Optional[PydanticAgent] = None

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process input and return response"""
        pass

    def update_state(self, status: str, task: Optional[str] = None):
        """Update agent state"""
        self.state.status = status
        if task:
            self.state.current_task = task

    def get_state(self) -> AgentState:
        """Get current agent state"""
        return self.state
