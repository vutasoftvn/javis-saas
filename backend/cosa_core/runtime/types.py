from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Normalized request sent to an AgentRuntime implementation."""
    company_id: str
    workspace_id: str
    user_id: str

    agent_key: str
    task: str

    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    objective_id: Optional[str] = None

    context: dict[str, Any] = Field(default_factory=dict)

    model_policy: Optional[str] = None
    permission_profile: str = "read_only"

    parent_run_id: Optional[str] = None
    conversation_id: Optional[str] = None
    timeout_seconds: Optional[int] = 600


class AgentRunResult(BaseModel):
    """Normalized result returned by an AgentRuntime execution."""
    run_id: str
    runtime: str
    runtime_session_id: Optional[str] = None
    agent_key: str

    status: Literal[
        "completed",
        "failed",
        "cancelled",
        "awaiting_approval",
        "partial",
    ]

    output_text: Optional[str] = None
    structured_output: Optional[dict[str, Any]] = None

    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


class AgentEvent(BaseModel):
    """Streamed event emitted during agent runtime execution."""
    event_id: str
    run_id: str
    event_type: str  # e.g. "run_started", "thought", "tool_call_started", "tool_call_completed", "approval_required", "run_completed", "error"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)


class RuntimeHealth(BaseModel):
    """Health check payload for an agent runtime."""
    status: Literal["healthy", "degraded", "unavailable"]
    runtime_name: str
    version: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
