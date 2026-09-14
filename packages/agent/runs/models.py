from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from agent.workflows.manifest import GovernedWorkflowRunManifest
    from agent.workflows.models import WorkflowRunRecord

from pydantic import BaseModel, Field

from agent.contracts.run import RunStatus
from agent.governance.contracts import ExecutionMode
from agent.ids import uuid7  # LeafId UUIDv7 cho run_id (M2 §3)

__all__ = [
    "ApprovalActionOutboxRecord",
    "ApprovalBindingKind",
    "ApprovalEventRecord",
    "ApprovalSubject",
    "AutomationRunManifestRecord",
    "ComplianceDecisionPayload",
    "GovernedWorkflowRunManifest",
    "GovernedWorkflowRunOutcome",
    "IdempotencyClaimRecord",
    "RunApprovalRecord",
    "RunCheckpointRecord",
    "RunEventRecord",
    "RunRecord",
    "RunToolCallRecord",
    "WorkflowRunRecord",
    "WorkforceRunAttribution",
]


ApprovalBindingKind = Literal["TOOL_CALL", "CHANGE_REQUEST"]


class ApprovalSubject(BaseModel):
    kind: str
    ref: str
    definition_hash: str


class ApprovalEventRecord(BaseModel):
    """Bản ghi audit event cho phê duyệt trong agent.approval_events."""

    event_id: str = Field(default_factory=lambda: f"apprevt_{uuid.uuid4().hex[:16]}")
    approval_id: str
    workspace_id: str
    event_type: str
    actor_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalActionOutboxRecord(BaseModel):
    """Bản ghi action outbox cho thay đổi đã duyệt trong agent.approval_action_outbox."""

    outbox_id: str = Field(default_factory=lambda: f"outbox_{uuid.uuid4().hex[:16]}")
    approval_id: str
    workspace_id: str
    action: str
    subject_kind: str | None = None
    subject_ref: str | None = None
    subject_hash: str
    state: str = "pending"
    attempt_count: int = 0
    next_attempt_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    claim_token: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    delivered_at: datetime | None = None


class WorkforceRunAttribution(BaseModel):
    """Attribution bất biến của một run workforce (Task 4, spec §5.2). Đủ 4
    opaque IDs — resolve exact employee/assignment/work package/attempt. Không
    tái sử dụng cho run non-workforce (khi đó = None)."""

    model_config = {"frozen": True}

    agent_instance_id: str
    assignment_id: str
    work_package_id: str
    work_attempt_id: str


class ComplianceDecisionPayload(BaseModel):
    """Bản ghi structured compliance audit event (Task 9)."""

    run_id: str
    workspace_id: str
    deployment_id: str
    snapshot_hash: str
    policy_snapshot_hash: str
    capability_id: str
    tool_call_id: str
    checkpoint_ref: str
    decision: str
    reason_code: str | None = None
    rule_version_ids: list[str] = Field(default_factory=list)
    evidence_hashes: list[str] = Field(default_factory=list)
    provider_model_ref: str | None = None
    delegation_jti: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        frozen = True


class RunRecord(BaseModel):
    """Bản ghi thực thể Run trong agent.runs theo Master Guide §11.2.

    workspace_id là khóa tenant duy nhất sau Task 7 (2026-08-27).
    """

    run_id: str = Field(default_factory=lambda: f"run_{uuid7().hex}")
    workspace_id: str | None = None
    # Project-scoped Founder Hub (2026-09-11) — nullable; None = pre-existing
    # LEGACY_UNSCOPED run. Không suy diễn từ conversation/workspace, chỉ ghi
    # tường minh khi caller khai báo.
    project_id: str | None = None
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
    # Task 4 — None cho run non-workforce lịch sử.
    workforce_attribution: WorkforceRunAttribution | None = None


class RunCheckpointRecord(BaseModel):
    """Bản ghi checkpoint tuần tự trong agent.run_checkpoints theo Master Guide §11.3."""

    checkpoint_ref: str = Field(default_factory=lambda: f"ckpt_{uuid.uuid4().hex[:16]}")
    run_id: str
    project_id: str | None = None
    sequence_no: int
    step_name: str | None = None
    state_kind: str = "workflow"
    serialized_state: dict[str, Any] = Field(default_factory=dict)
    manifest_snapshot: dict[str, Any] = Field(default_factory=dict)
    resume_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunEventRecord(BaseModel):
    """Bản ghi event tác vụ append-only trong agent.run_events theo Master Guide §11.4."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    run_id: str
    project_id: str | None = None
    sequence_no: int | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunToolCallRecord(BaseModel):
    """Bản ghi exact invocation ledger trong agent.run_tool_calls theo Master Guide §11.5."""

    tool_call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:16]}")
    run_id: str
    project_id: str | None = None
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
    """Bản ghi human approval bind trong agent.approvals theo Master Guide §11.6 và Unified Governance §B.3."""

    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:16]}")
    workspace_id: str | None = None
    project_id: str | None = None
    binding_kind: ApprovalBindingKind = "TOOL_CALL"
    run_id: str | None = None
    tool_call_id: str | None = None
    checkpoint_ref: str | None = None
    status: str = "pending"
    requirement: dict[str, Any] = Field(default_factory=dict)
    requester: str | None = None
    action: str | None = None
    subject: str | None = None
    subject_kind: str | None = None
    subject_ref: str | None = None
    subject_hash: str | None = None
    reviewer: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] | None = None
    # COSA Automation MVP (Task 6) — bind the approval to the exact execution
    # manifest that was in force. An approval is valid only for
    # (run_id, tool_call_id, checkpoint_ref, manifest_hash). NULL for pre-existing
    # / non-automation approvals.
    manifest_hash: str | None = None
    decision_version: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
    expires_at: datetime | None = None


class IdempotencyClaimRecord(BaseModel):
    """Bản ghi atomic idempotency claim trong agent.idempotency_claims theo
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


class AutomationRunManifestRecord(BaseModel):
    """Manifest thực thi bất biến của một automation run curated, pin trước khi
    run vào RUNNING (COSA Automation MVP, spec §4.2). Insert-once theo run_id;
    resume/reclaim nạp lại theo run_id và so `manifest_hash` — không bao giờ
    resolve dependency mới hơn. Lưu trong agent.automation_run_manifests.

    manifest_json chứa: definition revision/hash, effective policy, pinned
    AgentSpec/skill/model policy versions, capability allowlist, approval/evidence
    policy, trigger identity và source refs — KHÔNG chứa nội dung business thô."""

    run_id: str
    manifest_hash: str
    manifest_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GovernedWorkflowRunOutcome(BaseModel):
    """Kết quả một lần dispatch/resume `governed_workflow_run` (Task 11, plan
    2026-09-13-founder-configurable-agent-skill-workflow). `status` phản ánh
    đúng `WorkflowStatus` cuối cùng của DAG run — không suy diễn từ text lỗi
    (CLAUDE.md quy tắc 7)."""

    run_id: str
    status: Literal["completed", "failed", "waiting_approval", "cancelled"]
    error: str | None = None
    pending_approval_id: str | None = None


def __getattr__(name: str) -> Any:
    if name == "GovernedWorkflowRunManifest":
        from agent.workflows.manifest import GovernedWorkflowRunManifest

        return GovernedWorkflowRunManifest
    if name == "WorkflowRunRecord":
        from agent.workflows.models import WorkflowRunRecord

        return WorkflowRunRecord
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
