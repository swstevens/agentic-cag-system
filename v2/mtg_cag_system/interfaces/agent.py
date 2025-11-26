"""
Agent interface - defines the contract all agents must follow.
"""

from abc import ABC, abstractmethod
from typing import Any
from ..models.agent import AgentState
from ..models.response import AgentResponse


class IAgent(ABC):
    """
    Interface for all agents in the system.

    Follows Interface Segregation Principle - agents only expose
    what clients need to interact with them.
    """

    @abstractmethod
    async def process(self, request: Any) -> AgentResponse:
        """
        Process a request and return a response.

        Args:
            request: Agent-specific request object (typed per agent)

        Returns:
            AgentResponse containing results, confidence, and reasoning trace
        """
        pass

    @abstractmethod
    def get_state(self) -> AgentState:
        """
        Get the current state of the agent.

        Returns:
            AgentState with current status, task, and metrics
        """
        pass

    @abstractmethod
    def update_state(self, status: str, task: str = None):
        """
        Update the agent's current state.

        Args:
            status: New status (idle, processing, completed, error)
            task: Optional task description
        """
        pass
