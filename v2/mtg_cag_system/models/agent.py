from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    SCHEDULING = "scheduling"
    KNOWLEDGE_FETCH = "knowledge_fetch"
    SYMBOLIC_REASONING = "symbolic_reasoning"


class AgentState(BaseModel):
    """State for an individual agent"""
    agent_id: str
    agent_type: AgentType
    current_task: Optional[str] = None
    status: str = "idle"  # idle, processing, completed, error
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ReasoningStep(BaseModel):
    """Single step in reasoning chain"""
    step_id: str = Field(default_factory=lambda: f"step_{datetime.now().timestamp()}")
    agent_type: AgentType
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    timestamp: datetime = Field(default_factory=datetime.now)


class ReasoningChain(BaseModel):
    """Complete reasoning chain for a query"""
    query_id: str
    steps: List[ReasoningStep] = Field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    total_confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    def add_step(self, step: ReasoningStep):
        self.steps.append(step)
        # Recalculate total confidence
        if self.steps:
            self.total_confidence = sum(s.confidence for s in self.steps) / len(self.steps)
