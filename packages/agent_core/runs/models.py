from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.contracts.run import RunStatus
from agent_core.governance.contracts import ExecutionMode

__all__ = [
    "RunRecord",
    "RunCheckpointRecord",
    "RunEventRecord",
    "RunToolCallRecord",
    "RunApprovalRecord",
]


class RunRecord(BaseModel):
    """Bản ghi thực thể Run trong agent_core.runs theo Master Guide §11.2."""

    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:16]}")
    tenant_id: Optional[str] = None
    company_id: Optional[str] = None
    workspace_id: Optional[str] = None
    conversation_id: Optional[str] = None
    session_ref: Optional[str] = None
    principal: str
    root_executable_id: str
    root_executable_kind: str = "agent"
    root_executable_version: str = "1.0.0"
    root_definition_hash: Optional[str] = None
    status: RunStatus = RunStatus.PENDING
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    model_policy: dict[str, Any] = Field(default_factory=dict)
    final_output: Optional[Any] = None
    usage: dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class RunCheckpointRecord(BaseModel):
    """Bản ghi checkpoint tuần tự trong agent_core.run_checkpoints theo Master Guide §11.3."""

    checkpoint_ref: str = Field(default_factory=lambda: f"ckpt_{uuid.uuid4().hex[:16]}")
    run_id: str
    sequence_no: int
    step_name: Optional[str] = None
    state_kind: str = "workflow"
    serialized_state: dict[str, Any] = Field(default_factory=dict)
    manifest_snapshot: dict[str, Any] = Field(default_factory=dict)
    resume_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunEventRecord(BaseModel):
    """Bản ghi event tác vụ append-only trong agent_core.run_events theo Master Guide §11.4."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    run_id: str
    sequence_no: Optional[int] = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunToolCallRecord(BaseModel):
    """Bản ghi exact invocation ledger trong agent_core.run_tool_calls theo Master Guide §11.5."""

    tool_call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:16]}")
    run_id: str
    checkpoint_ref: Optional[str] = None
    capability_id: str
    payload_hash: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    idempotency_key: Optional[str] = None
    result_hash: Optional[str] = None
    output_payload: Optional[Any] = None
    error_message: Optional[str] = None
    execution_target_snapshot: dict[str, Any] = Field(default_factory=dict)
    governance_state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class RunApprovalRecord(BaseModel):
    """Bản ghi human approval bind trong agent_core.approvals theo Master Guide §11.6."""

    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:16]}")
    run_id: str
    tool_call_id: str
    checkpoint_ref: str
    status: str = "pending"
    requirement: dict[str, Any] = Field(default_factory=dict)
    requester: Optional[str] = None
    action: Optional[str] = None
    subject: Optional[str] = None
    reviewer: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
