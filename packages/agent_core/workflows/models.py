from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class WorkflowStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TERMINAL_STATUSES = frozenset({WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED})

_ALLOWED_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.PENDING: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.RUNNING: frozenset(
        {
            WorkflowStatus.WAITING_APPROVAL,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.WAITING_APPROVAL: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
    ),
    WorkflowStatus.COMPLETED: frozenset(),
    WorkflowStatus.FAILED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
}


class InvalidWorkflowTransition(Exception):
    def __init__(self, current: WorkflowStatus, target: WorkflowStatus) -> None:
        super().__init__(f"Cannot transition Workflow from {current.value} to {target.value}")
        self.current = current
        self.target = target


class StepStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    FAILED = "FAILED"


class StepOutcome(BaseModel):
    status: StepStatus
    updates: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    approval_id: str | None = None


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    completed_steps: list[str] = Field(default_factory=list)
    checkpoints: dict[str, Any] = Field(default_factory=dict)
    step_outcomes: dict[str, StepOutcome] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    pending_approval_id: str | None = None
    failed_step_name: str | None = None
    had_approval_gate: bool = False
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def transition(self, target: WorkflowStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidWorkflowTransition(self.status, target)
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES
