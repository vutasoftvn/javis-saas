from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.contracts.run import RunStatus
from agent_core.governance.contracts import ExecutionMode
from agent_core.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)

__all__ = [
    "RunRepository",
    "InMemoryRunRepository",
    "PostgresRunRepository",
]


@runtime_checkable
class RunRepository(Protocol):
    """Protocol cho Durable Run Substrate Repository theo Master Guide §11."""

    # 1. Runs
    async def create_run(self, run: RunRecord) -> RunRecord: ...
    async def get_run(self, run_id: str) -> Optional[RunRecord]: ...
    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Optional[Any] = None,
        error_details: Optional[dict[str, Any]] = None,
    ) -> Optional[RunRecord]: ...

    # 2. Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord: ...
    async def get_latest_checkpoint(self, run_id: str) -> Optional[RunCheckpointRecord]: ...
    async def get_checkpoint(self, checkpoint_ref: str) -> Optional[RunCheckpointRecord]: ...
    async def list_checkpoints(self, run_id: str) -> list[RunCheckpointRecord]: ...

    # 3. Events
    async def append_event(self, event: RunEventRecord) -> RunEventRecord: ...
    async def list_events(self, run_id: str, after_seq: Optional[int] = None) -> list[RunEventRecord]: ...

    # 4. Tool Calls (Exact Invocation Ledger)
    async def save_tool_call(self, tool_call: RunToolCallRecord) -> RunToolCallRecord: ...
    async def get_tool_call(self, tool_call_id: str) -> Optional[RunToolCallRecord]: ...
    async def get_tool_call_by_idempotency(self, run_id: str, idempotency_key: str) -> Optional[RunToolCallRecord]: ...
    async def list_tool_calls(self, run_id: str) -> list[RunToolCallRecord]: ...

    # 5. Approvals
    async def create_approval(self, approval: RunApprovalRecord) -> RunApprovalRecord: ...
    async def get_approval(self, approval_id: str) -> Optional[RunApprovalRecord]: ...
    async def get_approval_by_tool_call(self, tool_call_id: str) -> Optional[RunApprovalRecord]: ...
    async def get_approval_by_checkpoint(self, checkpoint_ref: str) -> Optional[RunApprovalRecord]: ...
    async def decide_approval(
        self,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: Optional[str] = None,
        evidence: Optional[dict[str, Any]] = None,
    ) -> Optional[RunApprovalRecord]: ...
    async def list_pending_approvals(self, workspace_id: Optional[str] = None) -> list[RunApprovalRecord]: ...


class InMemoryRunRepository:
    """In-memory implementation of RunRepository for isolated unit tests and fast local dev."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._checkpoints: dict[str, RunCheckpointRecord] = {}  # checkpoint_ref -> record
        self._run_checkpoints: dict[str, list[str]] = {}  # run_id -> [checkpoint_ref]
        self._events: dict[str, list[RunEventRecord]] = {}  # run_id -> [events]
        self._tool_calls: dict[str, RunToolCallRecord] = {}  # tool_call_id -> record
        self._approvals: dict[str, RunApprovalRecord] = {}  # approval_id -> record

    # Runs
    async def create_run(self, run: RunRecord) -> RunRecord:
        self._runs[run.run_id] = run.model_copy(deep=True)
        return run

    async def get_run(self, run_id: str) -> Optional[RunRecord]:
        r = self._runs.get(run_id)
        return r.model_copy(deep=True) if r else None

    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Optional[Any] = None,
        error_details: Optional[dict[str, Any]] = None,
    ) -> Optional[RunRecord]:
        r = self._runs.get(run_id)
        if not r:
            return None
        r.status = status
        r.updated_at = datetime.now(timezone.utc)
        if final_output is not None:
            r.final_output = final_output
        if error_details is not None:
            r.error_details = error_details
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            r.completed_at = datetime.now(timezone.utc)
        return r.model_copy(deep=True)

    # Checkpoints
    async def save_checkpoint(self, checkpoint: RunCheckpointRecord) -> RunCheckpointRecord:
        self._checkpoints[checkpoint.checkpoint_ref] = checkpoint.model_copy(deep=True)
        seq_list = self._run_checkpoints.setdefault(checkpoint.run_id, [])
        if checkpoint.checkpoint_ref not in seq_list:
            seq_list.append(checkpoint.checkpoint_ref)
        return checkpoint

    async def get_latest_checkpoint(self, run_id: str) -> Optional[RunCheckpointRecord]:
        seq_list = self._run_checkpoints.get(run_id, [])
        if not seq_list:
            return None
        last_ref = seq_list[-1]
        return self._checkpoints[last_ref].model_copy(deep=True)

    async def get_checkpoint(self, checkpoint_ref: str) -> Optional[RunCheckpointRecord]:
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

    async def list_events(self, run_id: str, after_seq: Optional[int] = None) -> list[RunEventRecord]:
        ev_list = self._events.get(run_id, [])
        if after_seq is not None:
            return [e.model_copy(deep=True) for e in ev_list if (e.sequence_no or 0) > after_seq]
        return [e.model_copy(deep=True) for e in ev_list]

    # Tool Calls
    async def save_tool_call(self, tool_call: RunToolCallRecord) -> RunToolCallRecord:
        self._tool_calls[tool_call.tool_call_id] = tool_call.model_copy(deep=True)
        return tool_call

    async def get_tool_call(self, tool_call_id: str) -> Optional[RunToolCallRecord]:
        tc = self._tool_calls.get(tool_call_id)
        return tc.model_copy(deep=True) if tc else None

    async def get_tool_call_by_idempotency(self, run_id: str, idempotency_key: str) -> Optional[RunToolCallRecord]:
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

    async def get_approval(self, approval_id: str) -> Optional[RunApprovalRecord]:
        a = self._approvals.get(approval_id)
        return a.model_copy(deep=True) if a else None

    async def get_approval_by_tool_call(self, tool_call_id: str) -> Optional[RunApprovalRecord]:
        for a in self._approvals.values():
            if a.tool_call_id == tool_call_id:
                return a.model_copy(deep=True)
        return None

    async def get_approval_by_checkpoint(self, checkpoint_ref: str) -> Optional[RunApprovalRecord]:
        for a in self._approvals.values():
            if a.checkpoint_ref == checkpoint_ref:
                return a.model_copy(deep=True)
        return None

    async def decide_approval(
        self,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: Optional[str] = None,
        evidence: Optional[dict[str, Any]] = None,
    ) -> Optional[RunApprovalRecord]:
        a = self._approvals.get(approval_id)
        if not a:
            return None
        a.status = "approved" if approved else "denied"
        a.reviewer = reviewer
        a.decided_at = datetime.now(timezone.utc)
        if reason:
            a.reason = reason
        if evidence:
            a.evidence = evidence
        return a.model_copy(deep=True)

    async def list_pending_approvals(self, workspace_id: Optional[str] = None) -> list[RunApprovalRecord]:
        res = []
        for a in self._approvals.values():
            if a.status == "pending":
                if workspace_id is not None:
                    run = self._runs.get(a.run_id)
                    if not run or run.workspace_id != workspace_id:
                        continue
                res.append(a.model_copy(deep=True))
        return res


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
                        run_id, tenant_id, company_id, workspace_id, conversation_id, session_ref,
                        principal, root_executable_id, root_executable_kind, root_executable_version,
                        root_definition_hash, status, execution_mode, correlation_id, idempotency_key,
                        input_payload, model_policy, final_output, usage, error_details, created_at, updated_at
                    ) VALUES (
                        :run_id, :tenant_id, :company_id, :workspace_id, :conversation_id, :session_ref,
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
                    "tenant_id": run.tenant_id,
                    "company_id": run.company_id,
                    "workspace_id": run.workspace_id,
                    "conversation_id": run.conversation_id,
                    "session_ref": run.session_ref,
                    "principal": run.principal,
                    "root_executable_id": run.root_executable_id,
                    "root_executable_kind": run.root_executable_kind,
                    "root_executable_version": run.root_executable_version,
                    "root_definition_hash": run.root_definition_hash,
                    "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                    "execution_mode": run.execution_mode.value if hasattr(run.execution_mode, "value") else str(run.execution_mode),
                    "correlation_id": run.correlation_id,
                    "idempotency_key": run.idempotency_key,
                    "input_payload": json.dumps(run.input_payload),
                    "model_policy": json.dumps(run.model_policy),
                    "final_output": json.dumps(run.final_output) if run.final_output is not None else None,
                    "usage": json.dumps(run.usage),
                    "error_details": json.dumps(run.error_details) if run.error_details is not None else None,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at,
                },
            )
            await session.commit()
        return run

    async def get_run(self, run_id: str) -> Optional[RunRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT run_id, tenant_id, company_id, workspace_id, conversation_id, session_ref,
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

    async def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        final_output: Optional[Any] = None,
        error_details: Optional[dict[str, Any]] = None,
    ) -> Optional[RunRecord]:
        now = datetime.now(timezone.utc)
        completed_at = now if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED) else None
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
                    "error_details": json.dumps(error_details) if error_details is not None else None,
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

    async def get_latest_checkpoint(self, run_id: str) -> Optional[RunCheckpointRecord]:
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

    async def get_checkpoint(self, checkpoint_ref: str) -> Optional[RunCheckpointRecord]:
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

    async def list_events(self, run_id: str, after_seq: Optional[int] = None) -> list[RunEventRecord]:
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
                    "output_payload": json.dumps(tool_call.output_payload) if tool_call.output_payload is not None else None,
                    "error_message": tool_call.error_message,
                    "execution_target_snapshot": json.dumps(tool_call.execution_target_snapshot),
                    "governance_state": json.dumps(tool_call.governance_state),
                    "created_at": tool_call.created_at,
                    "completed_at": tool_call.completed_at,
                },
            )
            await session.commit()
        return tool_call

    async def get_tool_call(self, tool_call_id: str) -> Optional[RunToolCallRecord]:
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

    async def get_tool_call_by_idempotency(self, run_id: str, idempotency_key: str) -> Optional[RunToolCallRecord]:
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
                    "evidence": json.dumps(approval.evidence) if approval.evidence is not None else None,
                    "created_at": approval.created_at,
                    "decided_at": approval.decided_at,
                    "expires_at": approval.expires_at,
                },
            )
            await session.commit()
        return approval

    async def get_approval(self, approval_id: str) -> Optional[RunApprovalRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT approval_id, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, reviewer, reason, evidence,
                           created_at, decided_at, expires_at
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

    async def get_approval_by_tool_call(self, tool_call_id: str) -> Optional[RunApprovalRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT approval_id, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, reviewer, reason, evidence,
                           created_at, decided_at, expires_at
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

    async def get_approval_by_checkpoint(self, checkpoint_ref: str) -> Optional[RunApprovalRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT approval_id, run_id, tool_call_id, checkpoint_ref, status,
                           requirement, requester, action, subject, reviewer, reason, evidence,
                           created_at, decided_at, expires_at
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
        reason: Optional[str] = None,
        evidence: Optional[dict[str, Any]] = None,
    ) -> Optional[RunApprovalRecord]:
        status = "approved" if approved else "denied"
        now = datetime.now(timezone.utc)

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent_core.approvals
                    SET status = :status,
                        reviewer = :reviewer,
                        reason = COALESCE(:reason, reason),
                        evidence = COALESCE(:evidence, evidence),
                        decided_at = :decided_at
                    WHERE approval_id = :approval_id
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
            await session.commit()
        return await self.get_approval(approval_id)

    async def list_pending_approvals(self, workspace_id: Optional[str] = None) -> list[RunApprovalRecord]:
        query = """
            SELECT a.approval_id, a.run_id, a.tool_call_id, a.checkpoint_ref, a.status,
                   a.requirement, a.requester, a.action, a.subject, a.reviewer, a.reason, a.evidence,
                   a.created_at, a.decided_at, a.expires_at
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
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
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
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            expires_at=row["expires_at"],
        )
