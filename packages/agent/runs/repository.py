from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from agent.workflows.manifest import GovernedWorkflowRunManifest

from sqlalchemy import text

from agent.contracts.run import RunStatus
from agent.governance.contracts import ExecutionMode
from agent.persistence import BasePostgresRepository
from agent.runs.models import (
    ApprovalActionOutboxRecord,
    ApprovalEventRecord,
    IdempotencyClaimRecord,
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
    WorkforceRunAttribution,
)

ALLOW_LISTED_CHANGE_ACTIONS = {"promote_skill_candidate"}

# Task 11 — `ApprovalGateStep` (packages/agent/workflows/approval_step.py) uses
# an arbitrary, workflow-author-defined `action` string (`WorkflowStepSpec.action`),
# so gating the outbox enqueue by exact `action` value (as `ALLOW_LISTED_CHANGE_ACTIONS`
# does) can never work for governed workflow gates. `subject_kind == "workflow_gate"`
# is the one thing every `ApprovalGateStep` approval has in common (hardcoded in
# `ApprovalSubject(kind="workflow_gate", ...)`), so it's allow-listed by kind instead.
WORKFLOW_GATE_SUBJECT_KIND = "workflow_gate"

__all__ = [
    "ALLOW_LISTED_CHANGE_ACTIONS",
    "WORKFLOW_GATE_SUBJECT_KIND",
    "InMemoryRunRepository",
    "PostgresRunRepository",
    "RunRepository",
]


@runtime_checkable
class RunRepository(Protocol):
    """Protocol cho Durable Run Substrate Repository theo Master Guide §11."""

    # 1. Runs
    async def create_run(self, run: RunRecord) -> RunRecord: ...
    async def get_run(self, run_id: str) -> RunRecord | None: ...
    async def get_scoped_run(self, run_id: str, workspace_id: str) -> RunRecord | None: ...
    async def list_runs(self, workspace_id: str, limit: int = 50) -> list[RunRecord]: ...
    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None: ...
    async def transition_run_status(
        self,
        run_id: str,
        *,
        from_statuses: set[RunStatus],
        to_status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None: ...
    async def cancel_run(self, run_id: str, *, reason: str) -> RunRecord | None: ...
    async def attach_workforce_attribution(
        self, run_id: str, attribution: WorkforceRunAttribution
    ) -> RunRecord | None: ...

    # 2. Checkpoints & Manifests
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord: ...
    async def get_latest_checkpoint(self, run_id: str) -> RunCheckpointRecord | None: ...
    async def save_automation_manifest(
        self, run_id: str, manifest_hash: str, manifest_json: dict[str, Any]
    ) -> dict[str, Any]: ...
    async def get_automation_manifest(self, run_id: str) -> dict[str, Any] | None: ...
    async def create_workflow_manifest(
        self, manifest: GovernedWorkflowRunManifest
    ) -> GovernedWorkflowRunManifest: ...
    async def get_workflow_manifest(
        self, run_id: str
    ) -> GovernedWorkflowRunManifest | None: ...
    async def get_checkpoint(self, checkpoint_ref: str) -> RunCheckpointRecord | None: ...
    async def list_checkpoints(self, run_id: str) -> list[RunCheckpointRecord]: ...

    # 3. Events
    async def append_event(self, event: RunEventRecord) -> RunEventRecord: ...
    async def list_events(
        self, run_id: str, after_seq: int | None = None
    ) -> list[RunEventRecord]: ...

    # 4. Tool Calls (Exact Invocation Ledger)
    async def save_tool_call(self, tool_call: RunToolCallRecord) -> RunToolCallRecord: ...
    async def get_tool_call(self, tool_call_id: str) -> RunToolCallRecord | None: ...
    async def get_tool_call_by_idempotency(
        self, run_id: str, idempotency_key: str
    ) -> RunToolCallRecord | None: ...
    async def list_tool_calls(self, run_id: str) -> list[RunToolCallRecord]: ...

    # 5. Approvals
    async def create_approval(self, approval: RunApprovalRecord) -> RunApprovalRecord: ...
    async def get_approval(self, approval_id: str) -> RunApprovalRecord | None: ...
    async def get_scoped_approval(
        self, approval_id: str, workspace_id: str
    ) -> RunApprovalRecord | None: ...
    async def get_approval_by_tool_call(self, tool_call_id: str) -> RunApprovalRecord | None: ...
    async def get_approval_by_checkpoint(self, checkpoint_ref: str) -> RunApprovalRecord | None: ...
    async def decide_approval(
        self,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> RunApprovalRecord | None: ...
    async def list_pending_approvals(
        self,
        workspace_id: str | None = None,
    ) -> list[RunApprovalRecord]: ...
    async def create_or_get_pending_change_approval(
        self, approval: RunApprovalRecord
    ) -> tuple[RunApprovalRecord, bool]: ...
    async def append_approval_event(
        self,
        *,
        approval_id: str,
        workspace_id: str,
        event_type: str,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ApprovalEventRecord: ...
    async def decide_change_approval_and_enqueue(
        self,
        *,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> RunApprovalRecord | None: ...
    async def claim_approval_actions(
        self,
        *,
        limit: int,
        worker_id: str,
        now: datetime,
    ) -> list[ApprovalActionOutboxRecord]: ...
    async def mark_approval_action_delivered(
        self,
        *,
        approval_id: str,
        worker_id: str,
    ) -> bool: ...

    # 6. Atomic idempotency claims (Blueprint V2 §20)
    async def claim_idempotency(
        self, claim: IdempotencyClaimRecord
    ) -> tuple[bool, IdempotencyClaimRecord]: ...
    async def complete_idempotency_claim(
        self, claim_id: str, *, result_payload: Any, result_hash: str
    ) -> IdempotencyClaimRecord | None: ...
    async def fail_idempotency_claim(
        self, claim_id: str, *, error_message: str
    ) -> IdempotencyClaimRecord | None: ...
    async def retry_idempotency_claim(self, claim_id: str) -> IdempotencyClaimRecord | None: ...


class InMemoryRunRepository:
    """In-memory implementation of RunRepository for isolated unit tests and fast local dev."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._checkpoints: dict[str, RunCheckpointRecord] = {}  # checkpoint_ref -> record
        self._run_checkpoints: dict[str, list[str]] = {}  # run_id -> [checkpoint_ref]
        self._events: dict[str, list[RunEventRecord]] = {}  # run_id -> [events]
        self._tool_calls: dict[str, RunToolCallRecord] = {}  # tool_call_id -> record
        self._approvals: dict[str, RunApprovalRecord] = {}  # approval_id -> record
        self._approval_events: list[ApprovalEventRecord] = []
        self._approval_outbox: dict[str, ApprovalActionOutboxRecord] = {}  # approval_id -> record
        self._idempotency_claims: dict[str, IdempotencyClaimRecord] = {}  # claim_id -> record
        self._idempotency_index: dict[tuple[str, str, str, str], str] = {}  # scope key -> claim_id
        self._automation_manifests: dict[str, dict[str, Any]] = {}  # run_id -> {hash, json}

    # Runs
    async def create_run(self, run: RunRecord) -> RunRecord:
        self._runs[run.run_id] = run.model_copy(deep=True)
        return run

    async def get_run(self, run_id: str) -> RunRecord | None:
        r = self._runs.get(run_id)
        return r.model_copy(deep=True) if r else None

    async def get_scoped_run(self, run_id: str, workspace_id: str) -> RunRecord | None:
        """Scoped run lookup: return the run only if workspace_id matches."""
        r = self._runs.get(run_id)
        if r and r.workspace_id == workspace_id:
            return r.model_copy(deep=True)
        return None

    async def attach_workforce_attribution(
        self, run_id: str, attribution: WorkforceRunAttribution
    ) -> RunRecord | None:
        r = self._runs.get(run_id)
        if r is None:
            return None
        r.workforce_attribution = attribution
        r.updated_at = datetime.now(UTC)
        return r.model_copy(deep=True)

    async def list_runs(self, workspace_id: str, limit: int = 50) -> list[RunRecord]:
        return [
            r.model_copy(deep=True)
            for r in sorted(self._runs.values(), key=lambda x: x.created_at, reverse=True)
            if r.workspace_id == workspace_id
        ][:limit]

    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        r = self._runs.get(run_id)
        if not r:
            return None
        r.status = status
        r.updated_at = datetime.now(UTC)
        if final_output is not None:
            r.final_output = final_output
        if error_details is not None:
            r.error_details = error_details
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            r.completed_at = datetime.now(UTC)
        return r.model_copy(deep=True)

    async def transition_run_status(
        self,
        run_id: str,
        *,
        from_statuses: set[RunStatus],
        to_status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        """CAS atomic transition: chỉ succeed nếu status hiện tại nằm trong
        `from_statuses` — chặn việc một hoàn tất/fail muộn ghi đè lên một
        CANCELLED đã persist trước đó (race cancel-vs-complete). An toàn
        concurrent trong 1 process vì check-then-mutate không có `await` ở
        giữa (không có điểm preempt coroutine)."""
        r = self._runs.get(run_id)
        if not r or r.status not in from_statuses:
            return None
        r.status = to_status
        r.updated_at = datetime.now(UTC)
        if final_output is not None:
            r.final_output = final_output
        if error_details is not None:
            r.error_details = error_details
        if to_status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            r.completed_at = datetime.now(UTC)
        return r.model_copy(deep=True)

    async def cancel_run(self, run_id: str, *, reason: str) -> RunRecord | None:
        """Cancel idempotent: CANCELLED nằm trong `from_statuses` nên
        CANCELLED -> CANCELLED cũng là một CAS hợp lệ (ghi đè cùng giá trị,
        vô hại) — cách đơn giản nhất để cancel hai lần liên tiếp đều trả về
        record CANCELLED thay vì None/lỗi. COMPLETED/FAILED (terminal khác)
        KHÔNG nằm trong from_statuses — cancel một run đã xong việc là no-op,
        trả về record terminal hiện tại của nó (không phải None)."""
        result = await self.transition_run_status(
            run_id,
            from_statuses={
                RunStatus.PENDING,
                RunStatus.RUNNING,
                RunStatus.WAITING_APPROVAL,
                RunStatus.WAITING_INPUT,
                RunStatus.CANCELLED,
            },
            to_status=RunStatus.CANCELLED,
            error_details={"reason": reason},
        )
        if result is not None:
            return result
        # Run đã terminal ở COMPLETED/FAILED — no-op, trả về trạng thái thật.
        return await self.get_run(run_id)

    # Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord:
        self._checkpoints[checkpoint.checkpoint_ref] = checkpoint.model_copy(deep=True)
        seq_list = self._run_checkpoints.setdefault(checkpoint.run_id, [])
        if checkpoint.checkpoint_ref not in seq_list:
            seq_list.append(checkpoint.checkpoint_ref)
        return checkpoint

    async def save_automation_manifest(
        self, run_id: str, manifest_hash: str, manifest_json: dict[str, Any]
    ) -> dict[str, Any]:
        existing = self._automation_manifests.get(run_id)
        if existing is not None:
            if existing["manifest_hash"] != manifest_hash:
                raise ValueError(
                    f"run {run_id} already has a different automation manifest "
                    f"({existing['manifest_hash']} != {manifest_hash})"
                )
            return dict(existing)
        record = {
            "run_id": run_id,
            "manifest_hash": manifest_hash,
            "manifest_json": dict(manifest_json),
        }
        self._automation_manifests[run_id] = record
        return dict(record)

    async def get_automation_manifest(self, run_id: str) -> dict[str, Any] | None:
        rec = self._automation_manifests.get(run_id)
        return dict(rec) if rec else None

    async def create_workflow_manifest(
        self, manifest: GovernedWorkflowRunManifest
    ) -> GovernedWorkflowRunManifest:
        if not hasattr(self, "_workflow_manifest_repo"):
            from agent.workflows.manifest import InMemoryWorkflowManifestRepository
            self._workflow_manifest_repo = InMemoryWorkflowManifestRepository()
        return await self._workflow_manifest_repo.create_manifest(manifest)

    async def get_workflow_manifest(
        self, run_id: str
    ) -> GovernedWorkflowRunManifest | None:
        if not hasattr(self, "_workflow_manifest_repo"):
            from agent.workflows.manifest import InMemoryWorkflowManifestRepository
            self._workflow_manifest_repo = InMemoryWorkflowManifestRepository()
        return await self._workflow_manifest_repo.get_manifest(run_id)

    async def get_latest_checkpoint(self, run_id: str) -> RunCheckpointRecord | None:
        seq_list = self._run_checkpoints.get(run_id, [])
        if not seq_list:
            return None
        last_ref = seq_list[-1]
        return self._checkpoints[last_ref].model_copy(deep=True)

    async def get_checkpoint(self, checkpoint_ref: str) -> RunCheckpointRecord | None:
        c = self._checkpoints.get(checkpoint_ref)
        return c.model_copy(deep=True) if c else None

    async def list_checkpoints(self, run_id: str) -> list[RunCheckpointRecord]:
        seq_list = self._run_checkpoints.get(run_id, [])
        return [self._checkpoints[ref].model_copy(deep=True) for ref in seq_list]

    # Events
    async def append_event(self, event: RunEventRecord) -> RunEventRecord:
        ev_list = self._events.setdefault(event.run_id, [])
        event.sequence_no = len(ev_list) + 1
        ev_list.append(event.model_copy(deep=True))
        return event

    async def list_events(self, run_id: str, after_seq: int | None = None) -> list[RunEventRecord]:
        ev_list = self._events.get(run_id, [])
        if after_seq is not None:
            return [e.model_copy(deep=True) for e in ev_list if (e.sequence_no or 0) > after_seq]
        return [e.model_copy(deep=True) for e in ev_list]

    # Tool Calls
    async def save_tool_call(self, tool_call: RunToolCallRecord) -> RunToolCallRecord:
        self._tool_calls[tool_call.tool_call_id] = tool_call.model_copy(deep=True)
        return tool_call

    async def get_tool_call(self, tool_call_id: str) -> RunToolCallRecord | None:
        tc = self._tool_calls.get(tool_call_id)
        return tc.model_copy(deep=True) if tc else None

    async def get_tool_call_by_idempotency(
        self, run_id: str, idempotency_key: str
    ) -> RunToolCallRecord | None:
        for tc in self._tool_calls.values():
            if tc.run_id == run_id and tc.idempotency_key == idempotency_key:
                return tc.model_copy(deep=True)
        return None

    async def list_tool_calls(self, run_id: str) -> list[RunToolCallRecord]:
        return [tc.model_copy(deep=True) for tc in self._tool_calls.values() if tc.run_id == run_id]

    # Approvals
    async def create_approval(self, approval: RunApprovalRecord) -> RunApprovalRecord:
        record = approval.model_copy(deep=True)
        if record.workspace_id is None and record.run_id:
            run = self._runs.get(record.run_id)
            if run:
                record.workspace_id = run.workspace_id
        self._approvals[record.approval_id] = record
        return record.model_copy(deep=True)

    async def get_approval(self, approval_id: str) -> RunApprovalRecord | None:
        a = self._approvals.get(approval_id)
        return a.model_copy(deep=True) if a else None

    async def get_scoped_approval(
        self, approval_id: str, workspace_id: str
    ) -> RunApprovalRecord | None:
        """Scoped approval lookup: check workspace_id directly on approval or via run."""
        a = self._approvals.get(approval_id)
        if not a:
            return None
        if a.workspace_id == workspace_id:
            return a.model_copy(deep=True)
        if a.workspace_id is None and a.run_id:
            run = self._runs.get(a.run_id)
            if run and run.workspace_id == workspace_id:
                return a.model_copy(deep=True)
        return None

    async def get_approval_by_tool_call(self, tool_call_id: str) -> RunApprovalRecord | None:
        for a in self._approvals.values():
            if a.tool_call_id == tool_call_id:
                return a.model_copy(deep=True)
        return None

    async def get_approval_by_checkpoint(self, checkpoint_ref: str) -> RunApprovalRecord | None:
        for a in self._approvals.values():
            if a.checkpoint_ref == checkpoint_ref:
                return a.model_copy(deep=True)
        return None

    async def decide_approval(
        self,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> RunApprovalRecord | None:
        """CAS atomic decision (Blueprint V2 §21) — chỉ succeed nếu status hiện tại
        là 'pending'. An toàn concurrent trong 1 process vì không có `await` nào
        giữa bước kiểm tra status và bước ghi (không có điểm preempt coroutine)."""
        a = self._approvals.get(approval_id)
        if not a or a.status != "pending":
            return None
        a.status = "approved" if approved else "denied"
        a.reviewer = reviewer
        a.decided_at = datetime.now(UTC)
        a.decision_version += 1
        if reason:
            a.reason = reason
        if evidence:
            a.evidence = evidence
        return a.model_copy(deep=True)

    async def list_pending_approvals(
        self,
        workspace_id: str | None = None,
    ) -> list[RunApprovalRecord]:
        """List pending approvals. If workspace_id is provided, filter by that workspace.
        If workspace_id is None, return all pending approvals (system operation)."""
        res = []
        for a in self._approvals.values():
            if a.status == "pending":
                if workspace_id is None:
                    res.append(a.model_copy(deep=True))
                elif a.workspace_id == workspace_id:
                    res.append(a.model_copy(deep=True))
                elif a.workspace_id is None and a.run_id:
                    run = self._runs.get(a.run_id)
                    if run and run.workspace_id == workspace_id:
                        res.append(a.model_copy(deep=True))
        return res

    async def create_or_get_pending_change_approval(
        self, approval: RunApprovalRecord
    ) -> tuple[RunApprovalRecord, bool]:
        """Idempotently create or retrieve a pending CHANGE_REQUEST approval."""
        for existing in self._approvals.values():
            if (
                existing.binding_kind == "CHANGE_REQUEST"
                and existing.status == "pending"
                and existing.workspace_id == approval.workspace_id
                and existing.action == approval.action
                and existing.subject_kind == approval.subject_kind
                and existing.subject_ref == approval.subject_ref
                and existing.subject_hash == approval.subject_hash
            ):
                return existing.model_copy(deep=True), False
        self._approvals[approval.approval_id] = approval.model_copy(deep=True)
        return approval.model_copy(deep=True), True

    async def append_approval_event(
        self,
        *,
        approval_id: str,
        workspace_id: str,
        event_type: str,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ApprovalEventRecord:
        record = ApprovalEventRecord(
            approval_id=approval_id,
            workspace_id=workspace_id,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload or {},
        )
        self._approval_events.append(record.model_copy(deep=True))
        return record

    async def decide_change_approval_and_enqueue(
        self,
        *,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> RunApprovalRecord | None:
        """Atomic decision for change approval: CAS status = 'pending', record event,
        and enqueue into outbox only when approved and action is allow-listed."""
        a = self._approvals.get(approval_id)
        if not a or a.status != "pending":
            return None
        a.status = "approved" if approved else "denied"
        a.reviewer = reviewer
        a.decided_at = datetime.now(UTC)
        a.decision_version += 1
        if reason:
            a.reason = reason
        if evidence:
            a.evidence = evidence

        await self.append_approval_event(
            approval_id=a.approval_id,
            workspace_id=a.workspace_id or "",
            event_type="approval.decided",
            actor_id=reviewer,
            payload={"approved": approved, "reason": reason, "action": a.action},
        )

        if approved and (
            a.action in ALLOW_LISTED_CHANGE_ACTIONS or a.subject_kind == WORKFLOW_GATE_SUBJECT_KIND
        ):
            outbox = ApprovalActionOutboxRecord(
                approval_id=a.approval_id,
                workspace_id=a.workspace_id or "",
                action=a.action or "",
                subject_kind=a.subject_kind,
                subject_ref=a.subject_ref,
                subject_hash=a.subject_hash or "",
                state="pending",
                attempt_count=0,
                next_attempt_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
            self._approval_outbox[a.approval_id] = outbox

        return a.model_copy(deep=True)

    async def claim_approval_actions(
        self,
        *,
        limit: int,
        worker_id: str,
        now: datetime,
    ) -> list[ApprovalActionOutboxRecord]:
        claimed: list[ApprovalActionOutboxRecord] = []
        for outbox in self._approval_outbox.values():
            if len(claimed) >= limit:
                break
            if (outbox.state == "pending" and outbox.next_attempt_at <= now) or (
                outbox.state == "claimed" and outbox.next_attempt_at <= now
            ):
                outbox.state = "claimed"
                outbox.claim_token = worker_id
                outbox.attempt_count += 1
                outbox.next_attempt_at = now + timedelta(seconds=60)
                claimed.append(outbox.model_copy(deep=True))
        return claimed

    async def mark_approval_action_delivered(
        self,
        *,
        approval_id: str,
        worker_id: str,
    ) -> bool:
        outbox = self._approval_outbox.get(approval_id)
        if outbox and outbox.claim_token == worker_id and outbox.state == "claimed":
            outbox.state = "delivered"
            outbox.delivered_at = datetime.now(UTC)
            return True
        return False

    # 6. Atomic idempotency claims
    async def claim_idempotency(
        self, claim: IdempotencyClaimRecord
    ) -> tuple[bool, IdempotencyClaimRecord]:
        """Atomic trong 1 process: không có `await` nào giữa bước kiểm tra
        `_idempotency_index` và bước ghi — không có điểm preempt coroutine ở giữa,
        kể cả khi caller khác đang `await` bên trong handler đang chạy song song."""
        key = (claim.scope_kind, claim.scope_key, claim.capability_id, claim.idempotency_key)
        existing_id = self._idempotency_index.get(key)
        if existing_id is not None:
            existing = self._idempotency_claims[existing_id]
            return False, existing.model_copy(deep=True)

        stored = claim.model_copy(deep=True)
        self._idempotency_claims[stored.claim_id] = stored
        self._idempotency_index[key] = stored.claim_id
        return True, stored.model_copy(deep=True)

    async def complete_idempotency_claim(
        self, claim_id: str, *, result_payload: Any, result_hash: str
    ) -> IdempotencyClaimRecord | None:
        c = self._idempotency_claims.get(claim_id)
        if not c:
            return None
        c.status = "completed"
        c.result_payload = result_payload
        c.result_hash = result_hash
        c.updated_at = datetime.now(UTC)
        return c.model_copy(deep=True)

    async def fail_idempotency_claim(
        self, claim_id: str, *, error_message: str
    ) -> IdempotencyClaimRecord | None:
        c = self._idempotency_claims.get(claim_id)
        if not c:
            return None
        c.status = "failed"
        c.error_message = error_message
        c.updated_at = datetime.now(UTC)
        return c.model_copy(deep=True)

    async def retry_idempotency_claim(self, claim_id: str) -> IdempotencyClaimRecord | None:
        c = self._idempotency_claims.get(claim_id)
        if not c or c.status != "failed":
            return None
        c.status = "running"
        c.error_message = None
        c.updated_at = datetime.now(UTC)
        return c.model_copy(deep=True)


class PostgresRunRepository(BasePostgresRepository):
    """PostgreSQL implementation of RunRepository persisting to agent.* schema.

    Inherits session lifecycle helpers from BasePostgresRepository:
    - _execute() for raw SQL execution
    - _commit() for transaction commit
    - _setup_tenancy() for workspace_id in session config
    - _list_paginated() for paginated queries
    """

    def __init__(self, db_session_factory: Any) -> None:
        super().__init__(db_session_factory)

    # 1. Runs
    async def create_run(self, run: RunRecord) -> RunRecord:
        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.runs (
                        run_id, workspace_id, project_id, conversation_id, session_ref,
                        principal, root_executable_id, root_executable_kind, root_executable_version,
                        root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                        input_payload, model_policy, final_output, usage, error_details, created_at, updated_at,
                        wf_agent_instance_id, wf_assignment_id, wf_work_package_id, wf_work_attempt_id
                    ) VALUES (
                        :run_id, :workspace_id, :project_id, :conversation_id, :session_ref,
                        :principal, :root_executable_id, :root_executable_kind, :root_executable_version,
                        :root_definition_hash, :status, :execution_mode, :correlation_id, :idempotency_key,
                        :input_payload, :model_policy, :final_output, :usage, :error_details, :created_at, :updated_at,
                        :wf_agent_instance_id, :wf_assignment_id, :wf_work_package_id, :wf_work_attempt_id
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at;
                    """
                ),
                {
                    "wf_agent_instance_id": run.workforce_attribution.agent_instance_id
                    if run.workforce_attribution
                    else None,
                    "wf_assignment_id": run.workforce_attribution.assignment_id
                    if run.workforce_attribution
                    else None,
                    "wf_work_package_id": run.workforce_attribution.work_package_id
                    if run.workforce_attribution
                    else None,
                    "wf_work_attempt_id": run.workforce_attribution.work_attempt_id
                    if run.workforce_attribution
                    else None,
                    "run_id": run.run_id,
                    "workspace_id": run.workspace_id,
                    "project_id": run.project_id,
                    "conversation_id": run.conversation_id,
                    "session_ref": run.session_ref,
                    "principal": run.principal,
                    "root_executable_id": run.root_executable_id,
                    "root_executable_kind": run.root_executable_kind,
                    "root_executable_version": run.root_executable_version,
                    "root_definition_hash": run.root_definition_hash,
                    "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                    "execution_mode": run.execution_mode.value
                    if hasattr(run.execution_mode, "value")
                    else str(run.execution_mode),
                    "correlation_id": run.correlation_id,
                    "idempotency_key": run.idempotency_key,
                    "input_payload": json.dumps(run.input_payload),
                    "model_policy": json.dumps(run.model_policy),
                    "final_output": json.dumps(run.final_output)
                    if run.final_output is not None
                    else None,
                    "usage": json.dumps(run.usage),
                    "error_details": json.dumps(run.error_details)
                    if run.error_details is not None
                    else None,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at,
                },
            )
            await self._commit(session)
        return run

    async def get_run(self, run_id: str) -> RunRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT run_id, workspace_id, project_id, conversation_id, session_ref,
                           principal, root_executable_id, root_executable_kind, root_executable_version,
                           root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                           input_payload, model_policy, final_output, usage, error_details, created_at, updated_at, completed_at,
                           wf_agent_instance_id, wf_assignment_id, wf_work_package_id, wf_work_attempt_id
                    FROM agent.runs
                    WHERE run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_run(row)

    async def get_scoped_run(self, run_id: str, workspace_id: str) -> RunRecord | None:
        """Scoped run lookup: enforce workspace_id in the SQL WHERE clause."""
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT run_id, workspace_id, project_id, conversation_id, session_ref,
                           principal, root_executable_id, root_executable_kind, root_executable_version,
                           root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                           input_payload, model_policy, final_output, usage, error_details, created_at, updated_at, completed_at,
                           wf_agent_instance_id, wf_assignment_id, wf_work_package_id, wf_work_attempt_id
                    FROM agent.runs
                    WHERE run_id = :run_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {"run_id": run_id, "workspace_id": workspace_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_run(row)

    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        now = datetime.now(UTC)
        completed_at = (
            now if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED) else None
        )
        status_val = status.value if hasattr(status, "value") else str(status)

        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    UPDATE agent.runs
                    SET status = :status,
                        final_output = COALESCE(:final_output, final_output),
                        error_details = COALESCE(:error_details, error_details),
                        updated_at = :updated_at,
                        completed_at = COALESCE(:completed_at, completed_at)
                    WHERE run_id = :run_id
                    """
                ),
                {
                    "run_id": run_id,
                    "status": status_val,
                    "final_output": json.dumps(final_output) if final_output is not None else None,
                    "error_details": json.dumps(error_details)
                    if error_details is not None
                    else None,
                    "updated_at": now,
                    "completed_at": completed_at,
                },
            )
            await self._commit(session)
        return await self.get_run(run_id)

    async def transition_run_status(
        self,
        run_id: str,
        *,
        from_statuses: set[RunStatus],
        to_status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        """CAS atomic transition qua một UPDATE duy nhất (không SELECT-rồi-UPDATE
        — race thật giữa 2 connection/process khác nhau chỉ đóng được bằng
        WHERE ... AND status = ANY(:from_statuses) trong CÙNG 1 statement).
        Trả None nếu run không tồn tại HOẶC status hiện tại không nằm trong
        from_statuses (vd. đã bị CANCELLED bởi 1 process khác) — caller (kernel)
        phải reload run thật qua get_run() thay vì tin transition đã xảy ra."""
        now = datetime.now(UTC)
        completed_at = (
            now
            if to_status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)
            else None
        )
        to_status_val = to_status.value if hasattr(to_status, "value") else str(to_status)
        from_status_vals = [s.value if hasattr(s, "value") else str(s) for s in from_statuses]

        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.runs
                    SET status = :to_status,
                        final_output = COALESCE(:final_output, final_output),
                        error_details = COALESCE(:error_details, error_details),
                        updated_at = :updated_at,
                        completed_at = COALESCE(:completed_at, completed_at)
                    WHERE run_id = :run_id
                      AND status = ANY(:from_statuses)
                    RETURNING run_id
                    """
                ),
                {
                    "run_id": run_id,
                    "to_status": to_status_val,
                    "from_statuses": from_status_vals,
                    "final_output": json.dumps(final_output) if final_output is not None else None,
                    "error_details": json.dumps(error_details)
                    if error_details is not None
                    else None,
                    "updated_at": now,
                    "completed_at": completed_at,
                },
            )
            updated = res.mappings().first()
            await self._commit(session)

        if not updated:
            return None
        return await self.get_run(run_id)

    async def cancel_run(self, run_id: str, *, reason: str) -> RunRecord | None:
        """Cancel idempotent: CANCELLED nằm trong from_statuses nên gọi lại
        cancel_run trên 1 run đã CANCELLED vẫn CAS thành công (ghi đè cùng
        giá trị, vô hại) thay vì trả None — tránh phải phân biệt race giữa
        "chưa từng cancel" và "đã cancel rồi" bằng 1 SELECT riêng (sẽ mở lại
        đúng race mà transition_run_status cố đóng). COMPLETED/FAILED KHÔNG
        nằm trong from_statuses — cancel một run đã xong việc là no-op, trả
        về record terminal thật của nó qua get_run(), không phải None."""
        result = await self.transition_run_status(
            run_id,
            from_statuses={
                RunStatus.PENDING,
                RunStatus.RUNNING,
                RunStatus.WAITING_APPROVAL,
                RunStatus.WAITING_INPUT,
                RunStatus.CANCELLED,
            },
            to_status=RunStatus.CANCELLED,
            error_details={"reason": reason},
        )
        if result is not None:
            return result
        return await self.get_run(run_id)

    async def attach_workforce_attribution(
        self, run_id: str, attribution: WorkforceRunAttribution
    ) -> RunRecord | None:
        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    UPDATE agent.runs SET
                        wf_agent_instance_id = :emp,
                        wf_assignment_id = :asg,
                        wf_work_package_id = :wp,
                        wf_work_attempt_id = :wa,
                        updated_at = now()
                    WHERE run_id = :run_id
                    """
                ),
                {
                    "emp": attribution.agent_instance_id,
                    "asg": attribution.assignment_id,
                    "wp": attribution.work_package_id,
                    "wa": attribution.work_attempt_id,
                    "run_id": run_id,
                },
            )
            await self._commit(session)
        return await self.get_run(run_id)

    async def list_runs(self, workspace_id: str, limit: int = 50) -> list[RunRecord]:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT run_id, conversation_id, agent_spec_id, agent_spec_version,
                           definition_hash, input_payload, current_checkpoint_ref, status,
                           attempt_count, error_details, final_output, metadata, workspace_id,
                           created_at, updated_at, completed_at
                    FROM agent.runs
                    WHERE workspace_id = :workspace_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"workspace_id": workspace_id, "limit": limit},
            )
            return [self._row_to_run(r) for r in res.mappings().all()]

    # 2. Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord:
        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.run_checkpoints (
                        checkpoint_ref, run_id, project_id, sequence_no, step_name, state_kind,
                        serialized_state, manifest_snapshot, resume_metadata, created_at
                    ) VALUES (
                        :checkpoint_ref, :run_id, :project_id, :sequence_no, :step_name, :state_kind,
                        :serialized_state, :manifest_snapshot, :resume_metadata, :created_at
                    )
                    ON CONFLICT (checkpoint_ref) DO NOTHING;
                    """
                ),
                {
                    "checkpoint_ref": checkpoint.checkpoint_ref,
                    "run_id": checkpoint.run_id,
                    "project_id": checkpoint.project_id,
                    "sequence_no": checkpoint.sequence_no,
                    "step_name": checkpoint.step_name,
                    "state_kind": checkpoint.state_kind,
                    "serialized_state": json.dumps(checkpoint.serialized_state),
                    "manifest_snapshot": json.dumps(checkpoint.manifest_snapshot),
                    "resume_metadata": json.dumps(checkpoint.resume_metadata),
                    "created_at": checkpoint.created_at,
                },
            )
            await self._commit(session)
        return checkpoint

    async def save_automation_manifest(
        self, run_id: str, manifest_hash: str, manifest_json: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.automation_run_manifests (run_id, manifest_hash, manifest_json)
                    VALUES (:run_id, :manifest_hash, CAST(:manifest_json AS jsonb))
                    ON CONFLICT (run_id) DO NOTHING
                    RETURNING run_id;
                    """
                ),
                {
                    "run_id": run_id,
                    "manifest_hash": manifest_hash,
                    "manifest_json": json.dumps(manifest_json),
                },
            )
            inserted = res.first() is not None
            await self._commit(session)
        existing = await self.get_automation_manifest(run_id)
        if existing is None:
            raise RuntimeError(f"automation manifest for run {run_id} vanished after write")
        if not inserted and existing["manifest_hash"] != manifest_hash:
            raise ValueError(
                f"run {run_id} already has a different automation manifest "
                f"({existing['manifest_hash']} != {manifest_hash})"
            )
        return existing

    async def get_automation_manifest(self, run_id: str) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT run_id, manifest_hash, manifest_json
                    FROM agent.automation_run_manifests WHERE run_id = :run_id;
                    """
                ),
                {"run_id": run_id},
            )
            row = res.first()
        if row is None:
            return None
        mj = row.manifest_json
        if isinstance(mj, str):
            mj = json.loads(mj)
        return {"run_id": row.run_id, "manifest_hash": row.manifest_hash, "manifest_json": mj}

    async def create_workflow_manifest(
        self, manifest: GovernedWorkflowRunManifest
    ) -> GovernedWorkflowRunManifest:
        if not hasattr(self, "_workflow_manifest_repo"):
            from agent.workflows.manifest import PostgresWorkflowManifestRepository
            self._workflow_manifest_repo = PostgresWorkflowManifestRepository(self._session_factory)
        return await self._workflow_manifest_repo.create_manifest(manifest)

    async def get_workflow_manifest(
        self, run_id: str
    ) -> GovernedWorkflowRunManifest | None:
        if not hasattr(self, "_workflow_manifest_repo"):
            from agent.workflows.manifest import PostgresWorkflowManifestRepository
            self._workflow_manifest_repo = PostgresWorkflowManifestRepository(self._session_factory)
        return await self._workflow_manifest_repo.get_manifest(run_id)

    async def get_latest_checkpoint(self, run_id: str) -> RunCheckpointRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT checkpoint_ref, run_id, project_id, sequence_no, step_name, state_kind,
                           serialized_state, manifest_snapshot, resume_metadata, created_at
                    FROM agent.run_checkpoints
                    WHERE run_id = :run_id
                    ORDER BY sequence_no DESC
                    LIMIT 1
                    """
                ),
                {"run_id": run_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_checkpoint(row)

    async def get_checkpoint(self, checkpoint_ref: str) -> RunCheckpointRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT checkpoint_ref, run_id, project_id, sequence_no, step_name, state_kind,
                           serialized_state, manifest_snapshot, resume_metadata, created_at
                    FROM agent.run_checkpoints
                    WHERE checkpoint_ref = :checkpoint_ref
                    """
                ),
                {"checkpoint_ref": checkpoint_ref},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_checkpoint(row)

    async def list_checkpoints(self, run_id: str) -> list[RunCheckpointRecord]:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT checkpoint_ref, run_id, project_id, sequence_no, step_name, state_kind,
                           serialized_state, manifest_snapshot, resume_metadata, created_at
                    FROM agent.run_checkpoints
                    WHERE run_id = :run_id
                    ORDER BY sequence_no ASC
                    """
                ),
                {"run_id": run_id},
            )
            return [self._row_to_checkpoint(r) for r in res.mappings().all()]

    # 3. Events
    async def append_event(self, event: RunEventRecord) -> RunEventRecord:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.run_events (
                        event_id, run_id, project_id, event_type, payload, correlation_id, created_at
                    ) VALUES (
                        :event_id, :run_id, :project_id, :event_type, :payload, :correlation_id, :created_at
                    )
                    RETURNING sequence_no;
                    """
                ),
                {
                    "event_id": event.event_id,
                    "run_id": event.run_id,
                    "project_id": event.project_id,
                    "event_type": event.event_type,
                    "payload": json.dumps(event.payload),
                    "correlation_id": event.correlation_id,
                    "created_at": event.created_at,
                },
            )
            seq = res.scalar_one()
            await self._commit(session)
            event.sequence_no = seq
        return event

    async def list_events(self, run_id: str, after_seq: int | None = None) -> list[RunEventRecord]:
        query = """
            SELECT event_id, run_id, project_id, sequence_no, event_type, payload, correlation_id, created_at
            FROM agent.run_events
            WHERE run_id = :run_id
        """
        params: dict[str, Any] = {"run_id": run_id}
        if after_seq is not None:
            query += " AND sequence_no > :after_seq"
            params["after_seq"] = after_seq
        query += " ORDER BY sequence_no ASC"

        async with self._session_factory() as session:
            res = await self._execute(session, text(query), params)
            return [self._row_to_event(r) for r in res.mappings().all()]

    # 4. Tool Calls
    async def save_tool_call(self, tool_call: RunToolCallRecord) -> RunToolCallRecord:
        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.run_tool_calls (
                        tool_call_id, run_id, project_id, checkpoint_ref, capability_id, payload_hash,
                        input_payload, status, idempotency_key, result_hash, output_payload,
                        error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    ) VALUES (
                        :tool_call_id, :run_id, :project_id, :checkpoint_ref, :capability_id, :payload_hash,
                        :input_payload, :status, :idempotency_key, :result_hash, :output_payload,
                        :error_message, :execution_target_snapshot, :governance_state, :created_at, :completed_at
                    )
                    ON CONFLICT (tool_call_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        result_hash = EXCLUDED.result_hash,
                        output_payload = EXCLUDED.output_payload,
                        error_message = EXCLUDED.error_message,
                        governance_state = EXCLUDED.governance_state,
                        completed_at = EXCLUDED.completed_at;
                    """
                ),
                {
                    "tool_call_id": tool_call.tool_call_id,
                    "run_id": tool_call.run_id,
                    "project_id": tool_call.project_id,
                    "checkpoint_ref": tool_call.checkpoint_ref,
                    "capability_id": tool_call.capability_id,
                    "payload_hash": tool_call.payload_hash,
                    "input_payload": json.dumps(tool_call.input_payload),
                    "status": tool_call.status,
                    "idempotency_key": tool_call.idempotency_key,
                    "result_hash": tool_call.result_hash,
                    "output_payload": json.dumps(tool_call.output_payload)
                    if tool_call.output_payload is not None
                    else None,
                    "error_message": tool_call.error_message,
                    "execution_target_snapshot": json.dumps(tool_call.execution_target_snapshot),
                    "governance_state": json.dumps(tool_call.governance_state),
                    "created_at": tool_call.created_at,
                    "completed_at": tool_call.completed_at,
                },
            )
            await self._commit(session)
        return tool_call

    async def get_tool_call(self, tool_call_id: str) -> RunToolCallRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT tool_call_id, run_id, project_id, checkpoint_ref, capability_id, payload_hash,
                           input_payload, status, idempotency_key, result_hash, output_payload,
                           error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    FROM agent.run_tool_calls
                    WHERE tool_call_id = :tool_call_id
                    """
                ),
                {"tool_call_id": tool_call_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_tool_call(row)

    async def get_tool_call_by_idempotency(
        self, run_id: str, idempotency_key: str
    ) -> RunToolCallRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT tool_call_id, run_id, project_id, checkpoint_ref, capability_id, payload_hash,
                           input_payload, status, idempotency_key, result_hash, output_payload,
                           error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    FROM agent.run_tool_calls
                    WHERE run_id = :run_id AND idempotency_key = :idempotency_key
                    """
                ),
                {"run_id": run_id, "idempotency_key": idempotency_key},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_tool_call(row)

    async def list_tool_calls(self, run_id: str) -> list[RunToolCallRecord]:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT tool_call_id, run_id, project_id, checkpoint_ref, capability_id, payload_hash,
                           input_payload, status, idempotency_key, result_hash, output_payload,
                           error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    FROM agent.run_tool_calls
                    WHERE run_id = :run_id
                    ORDER BY created_at ASC
                    """
                ),
                {"run_id": run_id},
            )
            return [self._row_to_tool_call(r) for r in res.mappings().all()]

    # 5. Approvals
    async def create_approval(self, approval: RunApprovalRecord) -> RunApprovalRecord:
        ws_id = approval.workspace_id
        if ws_id is None and approval.run_id:
            run = await self.get_run(approval.run_id)
            if run:
                ws_id = run.workspace_id

        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.approvals (
                        approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                        requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                        reviewer, reason, evidence, manifest_hash, created_at, decided_at, expires_at
                    ) VALUES (
                        :approval_id, :workspace_id, :project_id, :binding_kind, :run_id, :tool_call_id, :checkpoint_ref, :status,
                        :requirement, :requester, :action, :subject, :subject_kind, :subject_ref, :subject_hash,
                        :reviewer, :reason, :evidence, :manifest_hash, :created_at, :decided_at, :expires_at
                    )
                    ON CONFLICT (approval_id) DO NOTHING;
                    """
                ),
                {
                    "approval_id": approval.approval_id,
                    "workspace_id": ws_id,
                    "project_id": approval.project_id,
                    "binding_kind": approval.binding_kind,
                    "run_id": approval.run_id,
                    "tool_call_id": approval.tool_call_id,
                    "checkpoint_ref": approval.checkpoint_ref,
                    "status": approval.status,
                    "requirement": json.dumps(approval.requirement),
                    "requester": approval.requester,
                    "action": approval.action,
                    "subject": approval.subject,
                    "subject_kind": approval.subject_kind,
                    "subject_ref": approval.subject_ref,
                    "subject_hash": approval.subject_hash,
                    "reviewer": approval.reviewer,
                    "reason": approval.reason,
                    "evidence": json.dumps(approval.evidence)
                    if approval.evidence is not None
                    else None,
                    "manifest_hash": approval.manifest_hash,
                    "created_at": approval.created_at,
                    "decided_at": approval.decided_at,
                    "expires_at": approval.expires_at,
                },
            )
            await self._commit(session)
        return approval

    async def get_approval(self, approval_id: str) -> RunApprovalRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                           reviewer, reason, evidence, manifest_hash, decision_version, created_at, decided_at, expires_at
                    FROM agent.approvals
                    WHERE approval_id = :approval_id
                    """
                ),
                {"approval_id": approval_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_approval(row)

    async def get_scoped_approval(
        self, approval_id: str, workspace_id: str
    ) -> RunApprovalRecord | None:
        """Scoped approval lookup: query a.workspace_id directly."""
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT a.approval_id, a.workspace_id, a.project_id, a.binding_kind, a.run_id, a.tool_call_id, a.checkpoint_ref, a.status,
                           a.requirement, a.requester, a.action, a.subject, a.subject_kind, a.subject_ref, a.subject_hash,
                           a.reviewer, a.reason, a.evidence, a.manifest_hash, a.decision_version, a.created_at, a.decided_at, a.expires_at
                    FROM agent.approvals a
                    WHERE a.approval_id = :approval_id
                      AND a.workspace_id = :workspace_id
                    """
                ),
                {"approval_id": approval_id, "workspace_id": workspace_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_approval(row)

    async def get_approval_by_tool_call(self, tool_call_id: str) -> RunApprovalRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                           reviewer, reason, evidence, manifest_hash, decision_version, created_at, decided_at, expires_at
                    FROM agent.approvals
                    WHERE tool_call_id = :tool_call_id
                    """
                ),
                {"tool_call_id": tool_call_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_approval(row)

    async def get_approval_by_checkpoint(self, checkpoint_ref: str) -> RunApprovalRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                           reviewer, reason, evidence, manifest_hash, decision_version, created_at, decided_at, expires_at
                    FROM agent.approvals
                    WHERE checkpoint_ref = :checkpoint_ref
                    """
                ),
                {"checkpoint_ref": checkpoint_ref},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_approval(row)

    async def decide_approval(
        self,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> RunApprovalRecord | None:
        """CAS atomic decision (Blueprint V2 §21) — chỉ succeed nếu status hiện tại
        là 'pending'. Trả None nếu approval không tồn tại HOẶC đã được quyết định
        trước đó (stale/double-decision) — caller (DurableApprovalService) phân biệt
        2 trường hợp này bằng cách load lại approval trước khi gọi."""
        status = "approved" if approved else "denied"
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.approvals
                    SET status = :status,
                        reviewer = :reviewer,
                        reason = COALESCE(:reason, reason),
                        evidence = COALESCE(:evidence, evidence),
                        decided_at = :decided_at,
                        decision_version = decision_version + 1
                    WHERE approval_id = :approval_id
                      AND status = 'pending'
                    RETURNING approval_id
                    """
                ),
                {
                    "approval_id": approval_id,
                    "status": status,
                    "reviewer": reviewer,
                    "reason": reason,
                    "evidence": json.dumps(evidence) if evidence is not None else None,
                    "decided_at": now,
                },
            )
            updated = res.mappings().first()
            await self._commit(session)

        if not updated:
            return None
        return await self.get_approval(approval_id)

    async def list_pending_approvals(
        self,
        workspace_id: str | None = None,
    ) -> list[RunApprovalRecord]:
        """List pending approvals directly querying a.workspace_id."""
        query = """
            SELECT a.approval_id, a.workspace_id, a.project_id, a.binding_kind, a.run_id, a.tool_call_id, a.checkpoint_ref, a.status,
                    a.requirement, a.requester, a.action, a.subject, a.subject_kind, a.subject_ref, a.subject_hash,
                    a.reviewer, a.reason, a.evidence, a.manifest_hash, a.decision_version, a.created_at, a.decided_at, a.expires_at
            FROM agent.approvals a
            WHERE a.status = 'pending'
        """
        params: dict[str, Any] = {}
        if workspace_id is not None:
            query += " AND a.workspace_id = :workspace_id"
            params["workspace_id"] = workspace_id
        query += " ORDER BY a.created_at ASC"

        async with self._session_factory() as session:
            res = await self._execute(session, text(query), params)
            return [self._row_to_approval(r) for r in res.mappings().all()]

    async def create_or_get_pending_change_approval(
        self, approval: RunApprovalRecord
    ) -> tuple[RunApprovalRecord, bool]:
        """Idempotently insert or retrieve a pending CHANGE_REQUEST approval using unique partial index."""
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.approvals (
                        approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                        requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                        reviewer, reason, evidence, manifest_hash, created_at, decided_at, expires_at
                    ) VALUES (
                        :approval_id, :workspace_id, :project_id, :binding_kind, :run_id, :tool_call_id, :checkpoint_ref, :status,
                        :requirement, :requester, :action, :subject, :subject_kind, :subject_ref, :subject_hash,
                        :reviewer, :reason, :evidence, :manifest_hash, :created_at, :decided_at, :expires_at
                    )
                    ON CONFLICT (workspace_id, action, subject_kind, subject_ref, subject_hash)
                    WHERE binding_kind = 'CHANGE_REQUEST' AND status = 'pending'
                    DO NOTHING
                    RETURNING approval_id;
                    """
                ),
                {
                    "approval_id": approval.approval_id,
                    "workspace_id": approval.workspace_id,
                    "project_id": approval.project_id,
                    "binding_kind": approval.binding_kind,
                    "run_id": approval.run_id,
                    "tool_call_id": approval.tool_call_id,
                    "checkpoint_ref": approval.checkpoint_ref,
                    "status": approval.status,
                    "requirement": json.dumps(approval.requirement),
                    "requester": approval.requester,
                    "action": approval.action,
                    "subject": approval.subject,
                    "subject_kind": approval.subject_kind,
                    "subject_ref": approval.subject_ref,
                    "subject_hash": approval.subject_hash,
                    "reviewer": approval.reviewer,
                    "reason": approval.reason,
                    "evidence": json.dumps(approval.evidence) if approval.evidence is not None else None,
                    "manifest_hash": approval.manifest_hash,
                    "created_at": approval.created_at,
                    "decided_at": approval.decided_at,
                    "expires_at": approval.expires_at,
                },
            )
            row = res.mappings().first()
            if row:
                await self._commit(session)
                return approval, True

            # In case of conflict, retrieve existing pending record
            existing_res = await self._execute(
                session,
                text(
                    """
                    SELECT approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                           reviewer, reason, evidence, manifest_hash, decision_version, created_at, decided_at, expires_at
                    FROM agent.approvals
                    WHERE workspace_id = :workspace_id
                      AND action = :action
                      AND subject_kind = :subject_kind
                      AND subject_ref = :subject_ref
                      AND subject_hash = :subject_hash
                      AND binding_kind = 'CHANGE_REQUEST'
                      AND status = 'pending'
                    LIMIT 1;
                    """
                ),
                {
                    "workspace_id": approval.workspace_id,
                    "action": approval.action,
                    "subject_kind": approval.subject_kind,
                    "subject_ref": approval.subject_ref,
                    "subject_hash": approval.subject_hash,
                },
            )
            existing_row = existing_res.mappings().first()
            await self._commit(session)
            if existing_row:
                return self._row_to_approval(existing_row), False
            return approval, True

    async def append_approval_event(
        self,
        *,
        approval_id: str,
        workspace_id: str,
        event_type: str,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ApprovalEventRecord:
        record = ApprovalEventRecord(
            approval_id=approval_id,
            workspace_id=workspace_id,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload or {},
        )
        async with self._session_factory() as session:
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.approval_events (
                        event_id, approval_id, workspace_id, event_type, actor_id, payload, created_at
                    ) VALUES (
                        :event_id, :approval_id, :workspace_id, :event_type, :actor_id, :payload, :created_at
                    );
                    """
                ),
                {
                    "event_id": record.event_id,
                    "approval_id": record.approval_id,
                    "workspace_id": record.workspace_id,
                    "event_type": record.event_type,
                    "actor_id": record.actor_id,
                    "payload": json.dumps(record.payload),
                    "created_at": record.created_at,
                },
            )
            await self._commit(session)
        return record

    async def decide_change_approval_and_enqueue(
        self,
        *,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> RunApprovalRecord | None:
        """Atomic decision for change approval: CAS status = 'pending', record event,
        and enqueue into outbox only when approved and action is allow-listed."""
        status = "approved" if approved else "denied"
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.approvals
                    SET status = :status,
                        reviewer = :reviewer,
                        reason = COALESCE(:reason, reason),
                        evidence = COALESCE(:evidence, evidence),
                        decided_at = :decided_at,
                        decision_version = decision_version + 1
                    WHERE approval_id = :approval_id
                      AND status = 'pending'
                    RETURNING approval_id, workspace_id, project_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status,
                              requirement, requester, action, subject, subject_kind, subject_ref, subject_hash,
                              reviewer, reason, evidence, manifest_hash, decision_version, created_at, decided_at, expires_at;
                    """
                ),
                {
                    "approval_id": approval_id,
                    "status": status,
                    "reviewer": reviewer,
                    "reason": reason,
                    "evidence": json.dumps(evidence) if evidence is not None else None,
                    "decided_at": now,
                },
            )
            row = res.mappings().first()
            if not row:
                return None

            approval = self._row_to_approval(row)

            # Append approval.decided event
            event_id = f"apprevt_{uuid.uuid4().hex[:16]}"
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.approval_events (
                        event_id, approval_id, workspace_id, event_type, actor_id, payload, created_at
                    ) VALUES (
                        :event_id, :approval_id, :workspace_id, :event_type, :actor_id, :payload, :created_at
                    );
                    """
                ),
                {
                    "event_id": event_id,
                    "approval_id": approval.approval_id,
                    "workspace_id": approval.workspace_id or "",
                    "event_type": "approval.decided",
                    "actor_id": reviewer,
                    "payload": json.dumps({"approved": approved, "reason": reason, "action": approval.action}),
                    "created_at": now,
                },
            )

            # Enqueue into outbox only when approved and action/subject_kind is allow-listed
            if approved and (
                approval.action in ALLOW_LISTED_CHANGE_ACTIONS
                or approval.subject_kind == WORKFLOW_GATE_SUBJECT_KIND
            ):
                outbox_id = f"outbox_{uuid.uuid4().hex[:16]}"
                await self._execute(
                    session,
                    text(
                        """
                        INSERT INTO agent.approval_action_outbox (
                            outbox_id, approval_id, workspace_id, action, subject_kind, subject_ref, subject_hash,
                            state, attempt_count, next_attempt_at, created_at
                        ) VALUES (
                            :outbox_id, :approval_id, :workspace_id, :action, :subject_kind, :subject_ref, :subject_hash,
                            'pending', 0, :next_attempt_at, :created_at
                        )
                        ON CONFLICT (approval_id) DO NOTHING;
                        """
                    ),
                    {
                        "outbox_id": outbox_id,
                        "approval_id": approval.approval_id,
                        "workspace_id": approval.workspace_id or "",
                        "action": approval.action or "",
                        "subject_kind": approval.subject_kind,
                        "subject_ref": approval.subject_ref,
                        "subject_hash": approval.subject_hash or "",
                        "next_attempt_at": now,
                        "created_at": now,
                    },
                )

            await self._commit(session)
            return approval

    async def claim_approval_actions(
        self,
        *,
        limit: int,
        worker_id: str,
        now: datetime,
    ) -> list[ApprovalActionOutboxRecord]:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    WITH claimable AS (
                        SELECT outbox_id
                        FROM agent.approval_action_outbox
                        WHERE (state = 'pending' AND next_attempt_at <= :now)
                           OR (state = 'claimed' AND next_attempt_at <= :now)
                        ORDER BY next_attempt_at ASC
                        LIMIT :limit
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE agent.approval_action_outbox o
                    SET state = 'claimed',
                        claim_token = :worker_id,
                        attempt_count = attempt_count + 1,
                        next_attempt_at = :now + interval '60 seconds'
                    FROM claimable c
                    WHERE o.outbox_id = c.outbox_id
                    RETURNING o.outbox_id, o.approval_id, o.workspace_id, o.action,
                              o.subject_kind, o.subject_ref, o.subject_hash,
                              o.state, o.attempt_count, o.next_attempt_at, o.claim_token,
                              o.created_at, o.delivered_at;
                    """
                ),
                {"limit": limit, "worker_id": worker_id, "now": now},
            )
            rows = res.mappings().all()
            await self._commit(session)
            return [self._row_to_approval_outbox(r) for r in rows]

    async def mark_approval_action_delivered(
        self,
        *,
        approval_id: str,
        worker_id: str,
    ) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.approval_action_outbox
                    SET state = 'delivered',
                        delivered_at = :now
                    WHERE approval_id = :approval_id
                      AND claim_token = :worker_id
                      AND state = 'claimed'
                    RETURNING outbox_id;
                    """
                ),
                {"approval_id": approval_id, "worker_id": worker_id, "now": now},
            )
            row = res.mappings().first()
            await self._commit(session)
            return bool(row)

    # 6. Atomic idempotency claims
    async def claim_idempotency(
        self, claim: IdempotencyClaimRecord
    ) -> tuple[bool, IdempotencyClaimRecord]:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.idempotency_claims (
                        claim_id, tenant_id, capability_id, scope_kind, scope_key,
                        idempotency_key, payload_hash, run_id, tool_call_id, status,
                        created_at, updated_at
                    ) VALUES (
                        :claim_id, :tenant_id, :capability_id, :scope_kind, :scope_key,
                        :idempotency_key, :payload_hash, :run_id, :tool_call_id, :status,
                        :created_at, :updated_at
                    )
                    ON CONFLICT (scope_kind, scope_key, capability_id, idempotency_key) DO NOTHING
                    RETURNING claim_id
                    """
                ),
                {
                    "claim_id": claim.claim_id,
                    "tenant_id": claim.tenant_id,
                    "capability_id": claim.capability_id,
                    "scope_kind": claim.scope_kind,
                    "scope_key": claim.scope_key,
                    "idempotency_key": claim.idempotency_key,
                    "payload_hash": claim.payload_hash,
                    "run_id": claim.run_id,
                    "tool_call_id": claim.tool_call_id,
                    "status": claim.status,
                    "created_at": claim.created_at,
                    "updated_at": claim.updated_at,
                },
            )
            inserted = res.mappings().first()
            await self._commit(session)

        if inserted:
            return True, claim

        existing = await self._get_idempotency_claim_by_scope(
            claim.scope_kind, claim.scope_key, claim.capability_id, claim.idempotency_key
        )
        return False, existing or claim

    async def _get_idempotency_claim_by_scope(
        self, scope_kind: str, scope_key: str, capability_id: str, idempotency_key: str
    ) -> IdempotencyClaimRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT claim_id, tenant_id, capability_id, scope_kind, scope_key,
                           idempotency_key, payload_hash, run_id, tool_call_id, status,
                           result_hash, result_payload, error_message, created_at, updated_at
                    FROM agent.idempotency_claims
                    WHERE scope_kind = :scope_kind AND scope_key = :scope_key
                      AND capability_id = :capability_id AND idempotency_key = :idempotency_key
                    """
                ),
                {
                    "scope_kind": scope_kind,
                    "scope_key": scope_key,
                    "capability_id": capability_id,
                    "idempotency_key": idempotency_key,
                },
            )
            row = res.mappings().first()
            return self._row_to_idempotency_claim(row) if row else None

    async def _get_idempotency_claim_by_id(self, claim_id: str) -> IdempotencyClaimRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT claim_id, tenant_id, capability_id, scope_kind, scope_key,
                           idempotency_key, payload_hash, run_id, tool_call_id, status,
                           result_hash, result_payload, error_message, created_at, updated_at
                    FROM agent.idempotency_claims
                    WHERE claim_id = :claim_id
                    """
                ),
                {"claim_id": claim_id},
            )
            row = res.mappings().first()
            return self._row_to_idempotency_claim(row) if row else None

    async def complete_idempotency_claim(
        self, claim_id: str, *, result_payload: Any, result_hash: str
    ) -> IdempotencyClaimRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.idempotency_claims
                    SET status = 'completed', result_payload = :result_payload,
                        result_hash = :result_hash, updated_at = :updated_at
                    WHERE claim_id = :claim_id
                    RETURNING claim_id
                    """
                ),
                {
                    "claim_id": claim_id,
                    "result_payload": json.dumps(result_payload)
                    if result_payload is not None
                    else None,
                    "result_hash": result_hash,
                    "updated_at": now,
                },
            )
            updated = res.mappings().first()
            await self._commit(session)
        if not updated:
            return None
        return await self._get_idempotency_claim_by_id(claim_id)

    async def fail_idempotency_claim(
        self, claim_id: str, *, error_message: str
    ) -> IdempotencyClaimRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.idempotency_claims
                    SET status = 'failed', error_message = :error_message, updated_at = :updated_at
                    WHERE claim_id = :claim_id
                    RETURNING claim_id
                    """
                ),
                {"claim_id": claim_id, "error_message": error_message, "updated_at": now},
            )
            updated = res.mappings().first()
            await self._commit(session)
        if not updated:
            return None
        return await self._get_idempotency_claim_by_id(claim_id)

    async def retry_idempotency_claim(self, claim_id: str) -> IdempotencyClaimRecord | None:
        """CAS: chỉ retry được claim đang ở status 'failed' — tránh 2 worker cùng
        retry 1 claim đã completed hoặc đang running ở nơi khác."""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    UPDATE agent.idempotency_claims
                    SET status = 'running', error_message = NULL, updated_at = :updated_at
                    WHERE claim_id = :claim_id AND status = 'failed'
                    RETURNING claim_id
                    """
                ),
                {"claim_id": claim_id, "updated_at": now},
            )
            updated = res.mappings().first()
            await self._commit(session)
        if not updated:
            return None
        return await self._get_idempotency_claim_by_id(claim_id)

    # Helper converters
    @staticmethod
    def _parse_json(val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    @classmethod
    def _row_to_run(cls, row: Any) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            conversation_id=row["conversation_id"],
            session_ref=row["session_ref"],
            principal=row["principal"],
            root_executable_id=row["root_executable_id"],
            root_executable_kind=row["root_executable_kind"],
            root_executable_version=row["root_executable_version"],
            root_definition_hash=row["root_definition_hash"],
            status=RunStatus(row["status"]),
            execution_mode=ExecutionMode(row["execution_mode"]),
            correlation_id=row["correlation_id"],
            idempotency_key=row["idempotency_key"],
            input_payload=cls._parse_json(row["input_payload"]) or {},
            model_policy=cls._parse_json(row["model_policy"]) or {},
            final_output=cls._parse_json(row["final_output"]),
            usage=cls._parse_json(row["usage"]) or {},
            error_details=cls._parse_json(row["error_details"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            workforce_attribution=cls._row_to_workforce_attribution(row),
        )

    @staticmethod
    def _row_to_workforce_attribution(row: Any) -> WorkforceRunAttribution | None:
        get = row.get if hasattr(row, "get") else lambda k: row[k]
        emp = get("wf_agent_instance_id")
        if not emp:
            return None
        return WorkforceRunAttribution(
            agent_instance_id=str(emp),
            assignment_id=str(get("wf_assignment_id") or ""),
            work_package_id=str(get("wf_work_package_id") or ""),
            work_attempt_id=str(get("wf_work_attempt_id") or ""),
        )

    @classmethod
    def _row_to_checkpoint(cls, row: Any) -> RunCheckpointRecord:
        return RunCheckpointRecord(
            checkpoint_ref=row["checkpoint_ref"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            sequence_no=row["sequence_no"],
            step_name=row["step_name"],
            state_kind=row["state_kind"],
            serialized_state=cls._parse_json(row["serialized_state"]) or {},
            manifest_snapshot=cls._parse_json(row["manifest_snapshot"]) or {},
            resume_metadata=cls._parse_json(row["resume_metadata"]) or {},
            created_at=row["created_at"],
        )

    @classmethod
    def _row_to_event(cls, row: Any) -> RunEventRecord:
        return RunEventRecord(
            event_id=row["event_id"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            sequence_no=row["sequence_no"],
            event_type=row["event_type"],
            payload=cls._parse_json(row["payload"]) or {},
            correlation_id=row["correlation_id"],
            created_at=row["created_at"],
        )

    @classmethod
    def _row_to_tool_call(cls, row: Any) -> RunToolCallRecord:
        return RunToolCallRecord(
            tool_call_id=row["tool_call_id"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            checkpoint_ref=row["checkpoint_ref"],
            capability_id=row["capability_id"],
            payload_hash=row["payload_hash"],
            input_payload=cls._parse_json(row["input_payload"]) or {},
            status=row["status"],
            idempotency_key=row["idempotency_key"],
            result_hash=row["result_hash"],
            output_payload=cls._parse_json(row["output_payload"]),
            error_message=row["error_message"],
            execution_target_snapshot=cls._parse_json(row["execution_target_snapshot"]) or {},
            governance_state=cls._parse_json(row["governance_state"]) or {},
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    @classmethod
    def _row_to_approval(cls, row: Any) -> RunApprovalRecord:
        return RunApprovalRecord(
            approval_id=row["approval_id"],
            workspace_id=row.get("workspace_id"),
            project_id=row.get("project_id"),
            binding_kind=row.get("binding_kind") or "TOOL_CALL",
            run_id=row.get("run_id"),
            tool_call_id=row.get("tool_call_id"),
            checkpoint_ref=row.get("checkpoint_ref"),
            status=row["status"],
            requirement=cls._parse_json(row["requirement"]) or {},
            requester=row.get("requester"),
            action=row.get("action"),
            subject=row.get("subject"),
            subject_kind=row.get("subject_kind"),
            subject_ref=row.get("subject_ref"),
            subject_hash=row.get("subject_hash"),
            reviewer=row.get("reviewer"),
            reason=row.get("reason"),
            evidence=cls._parse_json(row.get("evidence")),
            manifest_hash=row.get("manifest_hash"),
            decision_version=row["decision_version"],
            created_at=row["created_at"],
            decided_at=row.get("decided_at"),
            expires_at=row.get("expires_at"),
        )

    @classmethod
    def _row_to_approval_outbox(cls, row: Any) -> ApprovalActionOutboxRecord:
        return ApprovalActionOutboxRecord(
            outbox_id=row["outbox_id"],
            approval_id=row["approval_id"],
            workspace_id=row["workspace_id"],
            action=row["action"],
            subject_kind=row.get("subject_kind"),
            subject_ref=row.get("subject_ref"),
            subject_hash=row["subject_hash"],
            state=row["state"],
            attempt_count=row["attempt_count"],
            next_attempt_at=row["next_attempt_at"],
            claim_token=row.get("claim_token"),
            created_at=row["created_at"],
            delivered_at=row.get("delivered_at"),
        )

    @classmethod
    def _row_to_idempotency_claim(cls, row: Any) -> IdempotencyClaimRecord:
        return IdempotencyClaimRecord(
            claim_id=row["claim_id"],
            tenant_id=row["tenant_id"],
            capability_id=row["capability_id"],
            scope_kind=row["scope_kind"],
            scope_key=row["scope_key"],
            idempotency_key=row["idempotency_key"],
            payload_hash=row["payload_hash"],
            run_id=row["run_id"],
            tool_call_id=row["tool_call_id"],
            status=row["status"],
            result_hash=row["result_hash"],
            result_payload=cls._parse_json(row["result_payload"]),
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
