from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AgentRunStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TERMINAL_STATUSES = frozenset(
    {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED}
)

_ALLOWED_TRANSITIONS: dict[AgentRunStatus, frozenset[AgentRunStatus]] = {
    AgentRunStatus.CREATED: frozenset({AgentRunStatus.RUNNING, AgentRunStatus.CANCELLED}),
    AgentRunStatus.RUNNING: frozenset(
        {
            AgentRunStatus.WAITING_APPROVAL,
            AgentRunStatus.PAUSED,
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }
    ),
    AgentRunStatus.WAITING_APPROVAL: frozenset(
        {AgentRunStatus.RUNNING, AgentRunStatus.PAUSED, AgentRunStatus.CANCELLED, AgentRunStatus.FAILED}
    ),
    AgentRunStatus.PAUSED: frozenset(
        {AgentRunStatus.RUNNING, AgentRunStatus.WAITING_APPROVAL, AgentRunStatus.CANCELLED, AgentRunStatus.FAILED}
    ),
    AgentRunStatus.COMPLETED: frozenset(),
    AgentRunStatus.FAILED: frozenset(),
    AgentRunStatus.CANCELLED: frozenset(),
}


class InvalidAgentRunTransition(Exception):
    def __init__(self, current: AgentRunStatus, target: AgentRunStatus) -> None:
        super().__init__(f"Cannot transition AgentRun from {current.value} to {target.value}")
        self.current = current
        self.target = target


class AgentRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_key: str
    status: AgentRunStatus = AgentRunStatus.CREATED
    goal: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: dict[str, Any] | None = None
    error: str | None = None

    def transition(self, target: AgentRunStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidAgentRunTransition(self.status, target)
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES


from agentos.core.policy import PermissionLevel


class TaskContext(BaseModel):
    goal: str
    agent_key: str
    workspace_id: str
    role: str = "user"
    agent_permission_level: PermissionLevel = PermissionLevel.L1_SUGGEST
    company_id: str | None = None
    user_id: str | None = None
    workforce_member_id: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    run_id: str
    status: AgentRunStatus
    output: str | None = None
    tool_calls_made: int = 0
    error: str | None = None
    approval_id: str | None = None
