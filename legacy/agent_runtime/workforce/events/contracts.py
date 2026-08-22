from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class BaseEvent(BaseModel):
    event_id: str
    event_type: str = Field(..., description="e.g. RunCreated, ToolRequested")
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(..., description="Run ID")
    causation_id: str = Field(..., description="Parent Node or Step ID")
    scope_id: str = Field(..., description="Snapshot ID of ExecutionScope")
    actor_id: str = Field(..., description="Agent or System Actor")

class ToolRequestedEvent(BaseEvent):
    event_type: str = "ToolRequested"
    tool_name: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class RunCreatedEvent(BaseEvent):
    event_type: str = "RunCreated"
    payload: Dict[str, Any] = Field(default_factory=dict)

class NodeStartedEvent(BaseEvent):
    event_type: str = "NodeStarted"

class NodeCompletedEvent(BaseEvent):
    event_type: str = "NodeCompleted"
