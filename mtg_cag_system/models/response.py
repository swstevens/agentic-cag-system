from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class AgentResponse(BaseModel):
    """Response from an individual agent"""
    agent_type: str
    success: bool
    data: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_trace: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class FusedResponse(BaseModel):
    """Final response after result fusion"""
    query_id: str
    session_id: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    agent_contributions: Dict[str, AgentResponse] = Field(default_factory=dict)
    reasoning_chain: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
