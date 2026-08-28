from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.contracts.run import RunStatus
from agent_core.governance.contracts import ExecutionMode
from agent_core.runs.models import (
    IdempotencyClaimRecord,
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)

__all__ = [
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
    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Any | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> RunRecord | None: ...

    # 2. Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord: ...
    async def get_latest_checkpoint(self, run_id: str) -> RunCheckpointRecord | None: ...
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
        self._idempotency_claims: dict[str, IdempotencyClaimRecord] = {}  # claim_id -> record
        self._idempotency_index: dict[tuple[str, str, str, str], str] = {}  # scope key -> claim_id

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

    # Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord:
        self._checkpoints[checkpoint.checkpoint_ref] = checkpoint.model_copy(deep=True)
        seq_list = self._run_checkpoints.setdefault(checkpoint.run_id, [])
        if checkpoint.checkpoint_ref not in seq_list:
            seq_list.append(checkpoint.checkpoint_ref)
        return checkpoint

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
        self._approvals[approval.approval_id] = approval.model_copy(deep=True)
        return approval

    async def get_approval(self, approval_id: str) -> RunApprovalRecord | None:
        a = self._approvals.get(approval_id)
        return a.model_copy(deep=True) if a else None

    async def get_scoped_approval(
        self, approval_id: str, workspace_id: str
    ) -> RunApprovalRecord | None:
        """Scoped approval lookup: return the approval only if its associated run's workspace_id matches."""
        a = self._approvals.get(approval_id)
        if a:
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
                run = self._runs.get(a.run_id)
                if not run:
                    continue
                if workspace_id is not None and run.workspace_id != workspace_id:
                    continue
                res.append(a.model_copy(deep=True))
        return res

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


class PostgresRunRepository:
    """PostgreSQL implementation of RunRepository persisting to agent_core.* schema."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresRunRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    # 1. Runs
    async def create_run(self, run: RunRecord) -> RunRecord:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core.runs (
                        run_id, workspace_id, conversation_id, session_ref,
                        principal, root_executable_id, root_executable_kind, root_executable_version,
                        root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                        input_payload, model_policy, final_output, usage, error_details, created_at, updated_at
                    ) VALUES (
                        :run_id, :workspace_id, :conversation_id, :session_ref,
                        :principal, :root_executable_id, :root_executable_kind, :root_executable_version,
                        :root_definition_hash, :status, :execution_mode, :correlation_id, :idempotency_key,
                        :input_payload, :model_policy, :final_output, :usage, :error_details, :created_at, :updated_at
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at;
                    """
                ),
                {
                    "run_id": run.run_id,
                    "workspace_id": run.workspace_id,
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
            await session.commit()
        return run

    async def get_run(self, run_id: str) -> RunRecord | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT run_id, workspace_id, conversation_id, session_ref,
                           principal, root_executable_id, root_executable_kind, root_executable_version,
                           root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                           input_payload, model_policy, final_output, usage, error_details, created_at, updated_at, completed_at
                    FROM agent_core.runs
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
            res = await session.execute(
                text(
                    """
                    SELECT run_id, workspace_id, conversation_id, session_ref,
                           principal, root_executable_id, root_executable_kind, root_executable_version,
                           root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                           input_payload, model_policy, final_output, usage, error_details, created_at, updated_at, completed_at
                    FROM agent_core.runs
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
            await session.execute(
                text(
                    """
                    UPDATE agent_core.runs
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
            await session.commit()
        return await self.get_run(run_id)

    # 2. Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core.run_checkpoints (
                        checkpoint_ref, run_id, sequence_no, step_name, state_kind,
                        serialized_state, manifest_snapshot, resume_metadata, created_at
                    ) VALUES (
                        :checkpoint_ref, :run_id, :sequence_no, :step_name, :state_kind,
                        :serialized_state, :manifest_snapshot, :resume_metadata, :created_at
                    )
                    ON CONFLICT (checkpoint_ref) DO NOTHING;
                    """
                ),
                {
                    "checkpoint_ref": checkpoint.checkpoint_ref,
                    "run_id": checkpoint.run_id,
                    "sequence_no": checkpoint.sequence_no,
                    "step_name": checkpoint.step_name,
                    "state_kind": checkpoint.state_kind,
                    "serialized_state": json.dumps(checkpoint.serialized_state),
                    "manifest_snapshot": json.dumps(checkpoint.manifest_snapshot),
                    "resume_metadata": json.dumps(checkpoint.resume_metadata),
                    "created_at": checkpoint.created_at,
                },
            )
            await session.commit()
        return checkpoint

    async def get_latest_checkpoint(self, run_id: str) -> RunCheckpointRecord | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT checkpoint_ref, run_id, sequence_no, step_name, state_kind,
                           serialized_state, manifest_snapshot, resume_metadata, created_at
                    FROM agent_core.run_checkpoints
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
            res = await session.execute(
                text(
                    """
                    SELECT checkpoint_ref, run_id, sequence_no, step_name, state_kind,
                           serialized_state, manifest_snapshot, resume_metadata, created_at
                    FROM agent_core.run_checkpoints
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
            res = await session.execute(
                text(
                    """
                    SELECT checkpoint_ref, run_id, sequence_no, step_name, state_kind,
                           serialized_state, manifest_snapshot, resume_metadata, created_at
                    FROM agent_core.run_checkpoints
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
            res = await session.execute(
                text(
                    """
                    INSERT INTO agent_core.run_events (
                        event_id, run_id, event_type, payload, correlation_id, created_at
                    ) VALUES (
                        :event_id, :run_id, :event_type, :payload, :correlation_id, :created_at
                    )
                    RETURNING sequence_no;
                    """
                ),
                {
                    "event_id": event.event_id,
                    "run_id": event.run_id,
                    "event_type": event.event_type,
                    "payload": json.dumps(event.payload),
                    "correlation_id": event.correlation_id,
                    "created_at": event.created_at,
                },
            )
            seq = res.scalar_one()
            await session.commit()
            event.sequence_no = seq
        return event

    async def list_events(self, run_id: str, after_seq: int | None = None) -> list[RunEventRecord]:
        query = """
            SELECT event_id, run_id, sequence_no, event_type, payload, correlation_id, created_at
            FROM agent_core.run_events
            WHERE run_id = :run_id
        """
        params: dict[str, Any] = {"run_id": run_id}
        if after_seq is not None:
            query += " AND sequence_no > :after_seq"
            params["after_seq"] = after_seq
        query += " ORDER BY sequence_no ASC"

        async with self._session_factory() as session:
            res = await session.execute(text(query), params)
            return [self._row_to_event(r) for r in res.mappings().all()]

    # 4. Tool Calls
    async def save_tool_call(self, tool_call: RunToolCallRecord) -> RunToolCallRecord:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core.run_tool_calls (
                        tool_call_id, run_id, checkpoint_ref, capability_id, payload_hash,
                        input_payload, status, idempotency_key, result_hash, output_payload,
                        error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    ) VALUES (
                        :tool_call_id, :run_id, :checkpoint_ref, :capability_id, :payload_hash,
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
            await session.commit()
        return tool_call

    async def get_tool_call(self, tool_call_id: str) -> RunToolCallRecord | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT tool_call_id, run_id, checkpoint_ref, capability_id, payload_hash,
                           input_payload, status, idempotency_key, result_hash, output_payload,
                           error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    FROM agent_core.run_tool_calls
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
            res = await session.execute(
                text(
                    """
                    SELECT tool_call_id, run_id, checkpoint_ref, capability_id, payload_hash,
                           input_payload, status, idempotency_key, result_hash, output_payload,
                           error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    FROM agent_core.run_tool_calls
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
            res = await session.execute(
                text(
                    """
                    SELECT tool_call_id, run_id, checkpoint_ref, capability_id, payload_hash,
                           input_payload, status, idempotency_key, result_hash, output_payload,
                           error_message, execution_target_snapshot, governance_state, created_at, completed_at
                    FROM agent_core.run_tool_calls
                    WHERE run_id = :run_id
                    ORDER BY created_at ASC
                    """
                ),
                {"run_id": run_id},
            )
            return [self._row_to_tool_call(r) for r in res.mappings().all()]

    # 5. Approvals
    async def create_approval(self, approval: RunApprovalRecord) -> RunApprovalRecord:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core.approvals (
                        approval_id, run_id, tool_call_id, checkpoint_ref, status,
                        requirement, requester, action, subject, reviewer, reason, evidence,
                        created_at, decided_at, expires_at
                    ) VALUES (
                        :approval_id, :run_id, :tool_call_id, :checkpoint_ref, :status,
                        :requirement, :requester, :action, :subject, :reviewer, :reason, :evidence,
                        :created_at, :decided_at, :expires_at
                    )
                    ON CONFLICT (approval_id) DO NOTHING;
                    """
                ),
                {
                    "approval_id": approval.approval_id,
                    "run_id": approval.run_id,
                    "tool_call_id": approval.tool_call_id,
                    "checkpoint_ref": approval.checkpoint_ref,
                    "status": approval.status,
                    "requirement": json.dumps(approval.requirement),
                    "requester": approval.requester,
                    "action": approval.action,
                    "subject": approval.subject,
                    "reviewer": approval.reviewer,
                    "reason": approval.reason,
                    "evidence": json.dumps(approval.evidence)
                    if approval.evidence is not None
                    else None,
                    "created_at": approval.created_at,
                    "decided_at": approval.decided_at,
                    "expires_at": approval.expires_at,
                },
            )
            await session.commit()
        return approval

    async def get_approval(self, approval_id: str) -> RunApprovalRecord | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT approval_id, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, reviewer, reason, evidence,
                           decision_version, created_at, decided_at, expires_at
                    FROM agent_core.approvals
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
        """Scoped approval lookup: join with runs and enforce workspace_id in SQL WHERE clause."""
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT a.approval_id, a.run_id, a.tool_call_id, a.checkpoint_ref, a.status,
                           a.requirement, a.requester, a.action, a.subject, a.reviewer, a.reason, a.evidence,
                           a.decision_version, a.created_at, a.decided_at, a.expires_at
                    FROM agent_core.approvals a
                    JOIN agent_core.runs r ON a.run_id = r.run_id
                    WHERE a.approval_id = :approval_id
                      AND r.workspace_id = :workspace_id
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
            res = await session.execute(
                text(
                    """
                    SELECT approval_id, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, reviewer, reason, evidence,
                           decision_version, created_at, decided_at, expires_at
                    FROM agent_core.approvals
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
            res = await session.execute(
                text(
                    """
                    SELECT approval_id, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, reviewer, reason, evidence,
                           decision_version, created_at, decided_at, expires_at
                    FROM agent_core.approvals
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
            res = await session.execute(
                text(
                    """
                    UPDATE agent_core.approvals
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
            await session.commit()

        if not updated:
            return None
        return await self.get_approval(approval_id)

    async def list_pending_approvals(
        self,
        workspace_id: str | None = None,
    ) -> list[RunApprovalRecord]:
        """List pending approvals. If workspace_id is provided, filter by that workspace.
        If workspace_id is None, return all pending approvals (system operation)."""
        query = """
            SELECT a.approval_id, a.run_id, a.tool_call_id, a.checkpoint_ref, a.status,
                   a.requirement, a.requester, a.action, a.subject, a.reviewer, a.reason, a.evidence,
                   a.decision_version, a.created_at, a.decided_at, a.expires_at
            FROM agent_core.approvals a
            JOIN agent_core.runs r ON a.run_id = r.run_id
            WHERE a.status = 'pending'
        """
        params: dict[str, Any] = {}
        if workspace_id is not None:
            query += " AND r.workspace_id = :workspace_id"
            params["workspace_id"] = workspace_id
        query += " ORDER BY a.created_at ASC"

        async with self._session_factory() as session:
            res = await session.execute(text(query), params)
            return [self._row_to_approval(r) for r in res.mappings().all()]

    # 6. Atomic idempotency claims
    async def claim_idempotency(
        self, claim: IdempotencyClaimRecord
    ) -> tuple[bool, IdempotencyClaimRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    INSERT INTO agent_core.idempotency_claims (
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
            await session.commit()

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
            res = await session.execute(
                text(
                    """
                    SELECT claim_id, tenant_id, capability_id, scope_kind, scope_key,
                           idempotency_key, payload_hash, run_id, tool_call_id, status,
                           result_hash, result_payload, error_message, created_at, updated_at
                    FROM agent_core.idempotency_claims
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
            res = await session.execute(
                text(
                    """
                    SELECT claim_id, tenant_id, capability_id, scope_kind, scope_key,
                           idempotency_key, payload_hash, run_id, tool_call_id, status,
                           result_hash, result_payload, error_message, created_at, updated_at
                    FROM agent_core.idempotency_claims
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
            res = await session.execute(
                text(
                    """
                    UPDATE agent_core.idempotency_claims
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
            await session.commit()
        if not updated:
            return None
        return await self._get_idempotency_claim_by_id(claim_id)

    async def fail_idempotency_claim(
        self, claim_id: str, *, error_message: str
    ) -> IdempotencyClaimRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    UPDATE agent_core.idempotency_claims
                    SET status = 'failed', error_message = :error_message, updated_at = :updated_at
                    WHERE claim_id = :claim_id
                    RETURNING claim_id
                    """
                ),
                {"claim_id": claim_id, "error_message": error_message, "updated_at": now},
            )
            updated = res.mappings().first()
            await session.commit()
        if not updated:
            return None
        return await self._get_idempotency_claim_by_id(claim_id)

    async def retry_idempotency_claim(self, claim_id: str) -> IdempotencyClaimRecord | None:
        """CAS: chỉ retry được claim đang ở status 'failed' — tránh 2 worker cùng
        retry 1 claim đã completed hoặc đang running ở nơi khác."""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    UPDATE agent_core.idempotency_claims
                    SET status = 'running', error_message = NULL, updated_at = :updated_at
                    WHERE claim_id = :claim_id AND status = 'failed'
                    RETURNING claim_id
                    """
                ),
                {"claim_id": claim_id, "updated_at": now},
            )
            updated = res.mappings().first()
            await session.commit()
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
        )

    @classmethod
    def _row_to_checkpoint(cls, row: Any) -> RunCheckpointRecord:
        return RunCheckpointRecord(
            checkpoint_ref=row["checkpoint_ref"],
            run_id=row["run_id"],
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
            run_id=row["run_id"],
            tool_call_id=row["tool_call_id"],
            checkpoint_ref=row["checkpoint_ref"],
            status=row["status"],
            requirement=cls._parse_json(row["requirement"]) or {},
            requester=row["requester"],
            action=row["action"],
            subject=row["subject"],
            reviewer=row["reviewer"],
            reason=row["reason"],
            evidence=cls._parse_json(row["evidence"]),
            decision_version=row["decision_version"],
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            expires_at=row["expires_at"],
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
