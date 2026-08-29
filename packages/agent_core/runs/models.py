from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.contracts.run import RunStatus
from agent_core.governance.contracts import ExecutionMode
from agent_core.ids import uuid7  # LeafId UUIDv7 cho run_id (M2 §3)

__all__ = [
    "IdempotencyClaimRecord",
    "RunApprovalRecord",
    "RunCheckpointRecord",
    "RunEventRecord",
    "RunRecord",
    "RunToolCallRecord",
]


class RunRecord(BaseModel):
    """Bản ghi thực thể Run trong agent_core.runs theo Master Guide §11.2.

    workspace_id là khóa tenant duy nhất sau Task 7 (2026-08-27).
    """

    run_id: str = Field(default_factory=lambda: f"run_{uuid7().hex[:16]}")
    workspace_id: str | None = None
    conversation_id: str | None = None
    session_ref: str | None = None
    principal: str
    root_executable_id: str
    root_executable_kind: str = "agent"
    root_executable_version: str = "1.0.0"
    root_definition_hash: str | None = None
    policy_snapshot_ref: str | None = None
    status: RunStatus = RunStatus.PENDING
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
    correlation_id: str | None = None
    idempotency_key: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    model_policy: dict[str, Any] = Field(default_factory=dict)
    final_output: Any | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    error_details: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class RunCheckpointRecord(BaseModel):
    """Bản ghi checkpoint tuần tự trong agent_core.run_checkpoints theo Master Guide §11.3."""

    checkpoint_ref: str = Field(default_factory=lambda: f"ckpt_{uuid.uuid4().hex[:16]}")
    run_id: str
    sequence_no: int
    step_name: str | None = None
    state_kind: str = "workflow"
    serialized_state: dict[str, Any] = Field(default_factory=dict)
    manifest_snapshot: dict[str, Any] = Field(default_factory=dict)
    resume_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunEventRecord(BaseModel):
    """Bản ghi event tác vụ append-only trong agent_core.run_events theo Master Guide §11.4."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    run_id: str
    sequence_no: int | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunToolCallRecord(BaseModel):
    """Bản ghi exact invocation ledger trong agent_core.run_tool_calls theo Master Guide §11.5."""

    tool_call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:16]}")
    run_id: str
    checkpoint_ref: str | None = None
    capability_id: str
    payload_hash: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    idempotency_key: str | None = None
    result_hash: str | None = None
    output_payload: Any | None = None
    error_message: str | None = None
    spec_version: str | None = None
    definition_hash: str | None = None
    policy_snapshot_ref: str | None = None
    execution_target_snapshot: dict[str, Any] = Field(default_factory=dict)
    governance_state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class RunApprovalRecord(BaseModel):
    """Bản ghi human approval bind trong agent_core.approvals theo Master Guide §11.6."""

    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:16]}")
    run_id: str
    tool_call_id: str
    checkpoint_ref: str
    status: str = "pending"
    requirement: dict[str, Any] = Field(default_factory=dict)
    requester: str | None = None
    action: str | None = None
    subject: str | None = None
    reviewer: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] | None = None
    decision_version: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
    expires_at: datetime | None = None


class IdempotencyClaimRecord(BaseModel):
    """Bản ghi atomic idempotency claim trong agent_core.idempotency_claims theo
    Blueprint V2 §20. Tách biệt với RunToolCallRecord (exact invocation ledger):
    claim này là cơ chế "ai được quyền chạy side effect", còn tool_call là ledger
    lưu vết mọi lần gọi. `run_id deduplication và side-effect idempotency là hai
    bài toán khác nhau` (Blueprint V2 §16)."""

    claim_id: str = Field(default_factory=lambda: f"claim_{uuid.uuid4().hex[:16]}")
    tenant_id: str | None = None
    capability_id: str
    scope_kind: str = "RUN"  # RUN, TENANT, WORKSPACE, BUSINESS_ENTITY, GLOBAL
    scope_key: str
    idempotency_key: str
    payload_hash: str
    run_id: str
    tool_call_id: str
    status: str = "running"  # running, completed, failed
    result_hash: str | None = None
    result_payload: Any | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
