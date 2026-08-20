import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.founder_os.outcomes.models import RunStep
from app.workforce.agents.delegation.budget import MissionBudgetService
from app.workforce.agents.delegation.events import append_run_event
from app.workforce.agents.delegation.manager import delegation_provider_manager
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.states import (
    transition_delegation,
    transition_step,
)
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
)
from app.workforce.agents.governance.budget import MissionBudget
from app.workforce.agents.governance.approval_service import ApprovalService
from app.workforce.agents.profiles.registry import agent_profile_registry
from app.workforce.agents.runtime.errors import AgentRuntimeError
from app.workforce.agents.runtime.manager import agent_runtime_manager

logger = logging.getLogger(__name__)

LEASE_SECONDS = 30
LEASE_RENEW_SECONDS = 10
DELEGATION_POLL_SECONDS = 2.0

_TERMINAL = {"denied", "succeeded", "failed", "cancelled"}


class LeaseLost(RuntimeError):
    """Another worker owns the delegation attempt or its lease has expired."""


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _assert_live_lease(job: DelegationJob, lease_token: str) -> None:
    now = datetime.now(timezone.utc)
    if (
        job.lease_token != lease_token
        or job.lease_expires_at is None
        or _utc(job.lease_expires_at) <= now
    ):
        raise LeaseLost(f"Lease lost for delegation job {job.id}")


def claim_due_job(
    db: Session,
    worker_id: str,
    now: datetime,
) -> int | None:
    """Atomically claim one start, poll, or cancellation unit of work."""
    promoted = _promote_approved_jobs(db, now)
    due = or_(
        and_(
            DelegationJob.status.in_(("queued", "retry_scheduled")),
            DelegationJob.available_at <= now,
        ),
        and_(
            DelegationJob.status == "running",
            DelegationJob.provider_handle_jsonb.is_not(None),
            DelegationJob.next_poll_at.is_not(None),
            DelegationJob.next_poll_at <= now,
        ),
        DelegationJob.status == "cancel_requested",
    )
    job = (
        db.query(DelegationJob)
        .filter(
            due,
            or_(
                DelegationJob.lease_expires_at.is_(None),
                DelegationJob.lease_expires_at <= now,
            ),
        )
        .order_by(DelegationJob.available_at, DelegationJob.id)
        .with_for_update(skip_locked=True)
        .first()
    )
    if job is None:
        if promoted:
            db.commit()
        else:
            db.rollback()
        return None

    starting = job.provider_handle_jsonb is None and job.status in {
        "queued",
        "retry_scheduled",
    }
    if job.status == "queued":
        job.status = transition_delegation(job.status, "claimed")
    elif job.status == "retry_scheduled":
        job.status = transition_delegation(
            transition_delegation(job.status, "queued"),
            "claimed",
        )
    if starting:
        job.attempt_count += 1
    job.claimed_by = worker_id
    job.lease_token = uuid.uuid4().hex
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    db.commit()
    return job.id


def _promote_approved_jobs(db: Session, now: datetime) -> int:
    jobs = (
        db.query(DelegationJob)
        .filter(DelegationJob.status == "waiting_approval")
        .order_by(DelegationJob.available_at, DelegationJob.id)
        .limit(20)
        .with_for_update(skip_locked=True)
        .all()
    )
    promoted = 0
    for job in jobs:
        approval = ApprovalService.get_matching_delegation_approval(
            db,
            workspace_id=job.workspace_id,
            run_id=job.parent_agent_run_id,
            step_id=job.run_step_id,
            idempotency_key=job.idempotency_key,
        )
        if approval is None:
            resolved = ApprovalService.get_by_idempotency_key(
                db,
                workspace_id=job.workspace_id,
                idempotency_key=job.idempotency_key,
            )
            if (
                resolved is not None
                and resolved.run_id == job.parent_agent_run_id
                and resolved.capability == "agent.delegate"
                and resolved.resource_type == "run_step"
                and resolved.resource_id == str(job.run_step_id)
                and resolved.status in {"rejected", "expired"}
            ):
                step = (
                    db.query(RunStep)
                    .filter(RunStep.id == job.run_step_id)
                    .with_for_update()
                    .one()
                )
                job.status = transition_delegation(job.status, "denied")
                job.error_code = f"DELEGATION_APPROVAL_{resolved.status.upper()}"
                job.error_message = f"Delegation approval was {resolved.status}"
                job.completed_at = now
                step.status = transition_step(step.status, "failed")
                append_run_event(
                    db,
                    step.run_id,
                    "step.delegation_denied",
                    {
                        "step_id": str(step.id),
                        "delegation_job_id": str(job.id),
                        "approval_id": str(resolved.id),
                        "status": resolved.status,
                    },
                    f"delegation:{job.id}:approval:{resolved.status}",
                )
                promoted += 1
            continue
        step = (
            db.query(RunStep)
            .filter(RunStep.id == job.run_step_id)
            .with_for_update()
            .one()
        )
        job.status = transition_delegation(job.status, "queued")
        step.status = transition_step(step.status, "pending")
        job.available_at = min(_utc(job.available_at), now)
        append_run_event(
            db,
            step.run_id,
            "step.approval_resolved",
            {
                "step_id": str(step.id),
                "delegation_job_id": str(job.id),
                "approval_id": str(approval.id),
                "status": "approved",
            },
            f"delegation:{job.id}:approval:approved",
        )
        promoted += 1
    db.flush()
    return promoted


def persist_provider_handle(
    db: Session,
    job_id: int,
    lease_token: str,
    handle: DelegationHandle,
    *,
    now: datetime | None = None,
) -> DelegationJob:
    job = db.query(DelegationJob).filter(DelegationJob.id == job_id).with_for_update().first()
    if job is None:
        raise LeaseLost(f"Delegation job {job_id} no longer exists")
    _assert_live_lease(job, lease_token)
    if job.provider_handle_jsonb is not None:
        existing = DelegationHandle.model_validate(job.provider_handle_jsonb)
        if existing != handle:
            raise LeaseLost(f"Delegation job {job_id} already has a different provider handle")
        return job

    if job.status == "claimed":
        job.status = transition_delegation(job.status, "dispatching")
    if job.status == "dispatching":
        job.status = transition_delegation(job.status, "running")
    job.provider_handle_jsonb = handle.model_dump(mode="json")
    job.started_at = job.started_at or (now or datetime.now(timezone.utc))
    job.next_poll_at = now or datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def persist_provider_result(
    db: Session,
    job_id: int,
    lease_token: str,
    result: DelegationResult,
) -> DelegationJob:
    job = db.query(DelegationJob).filter(DelegationJob.id == job_id).with_for_update().first()
    if job is None:
        raise LeaseLost(f"Delegation job {job_id} no longer exists")
    _assert_live_lease(job, lease_token)
    if result.status not in {
        DelegationStatus.SUCCEEDED,
        DelegationStatus.FAILED,
        DelegationStatus.CANCELLED,
    }:
        raise ValueError(f"Cannot persist non-terminal result {result.status.value}")
    return TaskBoardService.complete_job(db, job.workspace_id, job.id, result)


def _persist_nonterminal(
    db: Session,
    job_id: int,
    lease_token: str,
    result: DelegationResult,
) -> None:
    job = db.query(DelegationJob).filter(DelegationJob.id == job_id).with_for_update().first()
    if job is None:
        raise LeaseLost(f"Delegation job {job_id} no longer exists")
    _assert_live_lease(job, lease_token)
    if job.status == "dispatching":
        job.status = transition_delegation(job.status, "running")
    job.result_jsonb = result.model_dump(mode="json")
    job.next_poll_at = result.next_poll_at or (
        datetime.now(timezone.utc) + timedelta(seconds=DELEGATION_POLL_SECONDS)
    )
    job.claimed_by = None
    job.lease_token = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    db.commit()


def _clear_lease(job: DelegationJob) -> None:
    job.claimed_by = None
    job.lease_token = None
    job.lease_expires_at = None
    job.heartbeat_at = None


def reconcile_expired_jobs(db: Session, now: datetime) -> int:
    """Recover expired non-terminal leases without replaying known handles."""
    jobs = (
        db.query(DelegationJob)
        .filter(
            DelegationJob.status.notin_(tuple(_TERMINAL)),
            DelegationJob.lease_expires_at.is_not(None),
            DelegationJob.lease_expires_at <= now,
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for job in jobs:
        if job.provider_handle_jsonb is not None:
            if job.status == "claimed":
                job.status = transition_delegation(job.status, "dispatching")
            if job.status == "dispatching":
                job.status = transition_delegation(job.status, "running")
            job.next_poll_at = now
        elif job.status == "cancel_requested":
            job.status = transition_delegation(job.status, "cancelled")
            job.completed_at = now
            _sync_recovered_terminal(db, job, "cancelled", now)
        elif job.attempt_count >= job.max_attempts:
            if job.status in {"claimed", "dispatching", "running"}:
                job.status = transition_delegation(job.status, "failed")
            elif job.status == "retry_scheduled":
                job.status = transition_delegation(job.status, "failed")
            job.error_code = "DELEGATION_MAX_ATTEMPTS"
            job.error_message = "Delegation lease expired after maximum attempts"
            job.completed_at = now
            _sync_recovered_terminal(db, job, "failed", now)
        else:
            if job.status in {"claimed", "dispatching", "running"}:
                job.status = transition_delegation(job.status, "retry_scheduled")
            if job.status == "retry_scheduled":
                job.status = transition_delegation(job.status, "queued")
            job.available_at = now
        _clear_lease(job)
    db.commit()
    return len(jobs)


def _sync_recovered_terminal(
    db: Session,
    job: DelegationJob,
    terminal_status: str,
    now: datetime,
) -> None:
    step = (
        db.query(RunStep)
        .filter(RunStep.id == job.run_step_id)
        .with_for_update()
        .one()
    )
    target_step = "cancelled" if terminal_status == "cancelled" else "failed"
    if step.status not in {"completed", "failed", "cancelled", "skipped"}:
        step.status = transition_step(step.status, target_step)
    if job.child_agent_run_id is not None:
        child = (
            db.query(AgentRun)
            .filter(
                AgentRun.id == job.child_agent_run_id,
                AgentRun.workspace_id == job.workspace_id,
            )
            .first()
        )
        if child is not None:
            child.status = terminal_status
            child.finished_at = now
    job.reserved_steps = 0
    job.reserved_tool_calls = 0
    job.reserved_cost_usd = 0
    append_run_event(
        db,
        step.run_id,
        f"step.delegation_{terminal_status}",
        {
            "step_id": str(step.id),
            "delegation_job_id": str(job.id),
            "error_code": job.error_code,
            "recovered": True,
        },
        f"delegation:{job.id}:terminal:{terminal_status}",
    )


def _renew_lease(
    session_factory: Callable[[], Session],
    job_id: int,
    worker_id: str,
    lease_token: str,
) -> None:
    db = session_factory()
    try:
        now = datetime.now(timezone.utc)
        updated = (
            db.query(DelegationJob)
            .filter(
                DelegationJob.id == job_id,
                DelegationJob.claimed_by == worker_id,
                DelegationJob.lease_token == lease_token,
                DelegationJob.status.notin_(tuple(_TERMINAL)),
            )
            .update(
                {
                    DelegationJob.heartbeat_at: now,
                    DelegationJob.lease_expires_at: now + timedelta(seconds=LEASE_SECONDS),
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            db.rollback()
            raise LeaseLost(f"Lease lost for delegation job {job_id}")
        db.commit()
    finally:
        db.close()


async def _await_with_heartbeat(
    awaitable,
    *,
    session_factory: Callable[[], Session],
    job_id: int,
    worker_id: str,
    lease_token: str,
):
    task = asyncio.create_task(awaitable)
    while True:
        done, _pending = await asyncio.wait(
            {task},
            timeout=LEASE_RENEW_SECONDS,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if task in done:
            return task.result()
        await asyncio.to_thread(
            _renew_lease,
            session_factory,
            job_id,
            worker_id,
            lease_token,
        )


async def _prepare_request(
    db: Session,
    job: DelegationJob,
) -> DelegationRequest:
    step = db.query(RunStep).filter(RunStep.id == job.run_step_id).with_for_update().one()
    parent = (
        db.query(AgentRun)
        .filter(
            AgentRun.id == job.parent_agent_run_id,
            AgentRun.workspace_id == job.workspace_id,
        )
        .one()
    )
    root = (
        db.query(AgentRun)
        .filter(
            AgentRun.id == job.root_agent_run_id,
            AgentRun.workspace_id == job.workspace_id,
        )
        .one()
    )
    profile = await agent_profile_registry.get_profile(job.profile_id)
    if profile is None:
        raise RuntimeError(f"Agent profile '{job.profile_id}' is no longer registered")

    if job.child_agent_run_id is None:
        budget = MissionBudget.model_validate(root.budget_jsonb or {})
        context = dict(step.inputs_jsonb or {})
        MissionBudgetService.reserve(
            db,
            root.id,
            job.id,
            steps=int(context.get("reserved_steps", 1)),
            tool_calls=int(context.get("reserved_tool_calls", 0)),
            cost_usd=context.get("reserved_cost_usd", 0),
            budget=budget,
        )
        child = AgentRun(
            id=generate_snowflake_id(),
            workspace_id=job.workspace_id,
            company_id=parent.company_id,
            user_id=parent.user_id,
            parent_run_id=parent.id,
            outcome_run_id=step.run_id,
            agent_key=profile.id,
            runtime=job.runtime_name or "pending",
            status="running",
            permission_profile=profile.permission_profile,
            metadata_jsonb={"root_agent_run_id": root.id, "delegation_job_id": job.id},
            started_at=datetime.now(timezone.utc),
        )
        db.add(child)
        db.flush()
        job.child_agent_run_id = child.id
        step.delegated_run_id = child.id
        if step.status != "running":
            step.status = transition_step(step.status, "running")
    if job.status == "claimed":
        job.status = transition_delegation(job.status, "dispatching")

    context = dict(step.inputs_jsonb or {})
    context.setdefault("user_id", parent.user_id)
    context.setdefault("company_id", parent.company_id or job.workspace_id)
    request = DelegationRequest(
        workspace_id=job.workspace_id,
        outcome_run_id=step.run_id,
        run_step_id=step.id,
        root_agent_run_id=root.id,
        parent_agent_run_id=parent.id,
        profile_id=profile.id,
        provider_name=job.provider_name,
        runtime_name=job.runtime_name,
        task=str(context.get("task") or step.expected_output or step.type),
        permission_profile=profile.permission_profile,
        context=context,
    )
    db.commit()
    return request


def _schedule_failure(
    db: Session,
    job_id: int,
    lease_token: str,
    error: Exception,
) -> DelegationJob | None:
    job = db.query(DelegationJob).filter(DelegationJob.id == job_id).with_for_update().first()
    if job is None:
        return None
    _assert_live_lease(job, lease_token)
    retryable = isinstance(error, AgentRuntimeError) and error.retryable
    if retryable and job.attempt_count < job.max_attempts:
        if job.status in {"claimed", "dispatching", "running"}:
            job.status = transition_delegation(job.status, "retry_scheduled")
        job.available_at = datetime.now(timezone.utc) + timedelta(
            seconds=min(60, 2 ** max(job.attempt_count, 1))
        )
        job.error_code = error.code
        job.error_message = str(error)
        _clear_lease(job)
        db.commit()
        return None
    result = DelegationResult(
        status=DelegationStatus.FAILED,
        retryable=False,
        error_code=(error.code if isinstance(error, AgentRuntimeError) else "DELEGATION_PROVIDER_ERROR"),
        error_message=str(error),
    )
    return persist_provider_result(db, job.id, lease_token, result)


async def process_delegation_job(
    job_id: int,
    worker_id: str,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """Process one claimed job without holding a transaction across provider I/O."""
    db = session_factory()
    lease_token: str | None = None
    try:
        job = db.query(DelegationJob).filter(DelegationJob.id == job_id).first()
        if job is None or job.claimed_by != worker_id or job.lease_token is None:
            raise LeaseLost(f"Worker '{worker_id}' does not own delegation job {job_id}")
        lease_token = job.lease_token
        _assert_live_lease(job, lease_token)
        provider = delegation_provider_manager.get(job.provider_name)
        idempotency_key = job.idempotency_key
        cancel_requested = job.status == "cancel_requested"
        handle = (
            DelegationHandle.model_validate(job.provider_handle_jsonb)
            if job.provider_handle_jsonb is not None
            else None
        )

        if cancel_requested and handle is None:
            completed = persist_provider_result(
                db,
                job.id,
                lease_token,
                DelegationResult(status=DelegationStatus.CANCELLED),
            )
            from app.workforce.agents.orchestration.continuation import (
                maybe_resume_mission,
            )

            step = db.query(RunStep).filter(RunStep.id == completed.run_step_id).one()
            await maybe_resume_mission(db, step.run_id)
            return

        if handle is None:
            request = await _prepare_request(db, job)
            db.close()
            handle = await _await_with_heartbeat(
                provider.delegate(request, idempotency_key),
                session_factory=session_factory,
                job_id=job_id,
                worker_id=worker_id,
                lease_token=lease_token,
            )
            db = session_factory()
            persisted = persist_provider_handle(db, job_id, lease_token, handle)
            cancel_requested = persisted.status == "cancel_requested"

        if cancel_requested:
            await provider.cancel(handle)
            result = DelegationResult(status=DelegationStatus.CANCELLED)
        else:
            result = await provider.poll(handle)

        db.close()
        db = session_factory()
        if result.status in {
            DelegationStatus.SUCCEEDED,
            DelegationStatus.FAILED,
            DelegationStatus.CANCELLED,
        }:
            completed = persist_provider_result(db, job_id, lease_token, result)
            from app.workforce.agents.orchestration.continuation import (
                maybe_resume_mission,
            )

            step = db.query(RunStep).filter(RunStep.id == completed.run_step_id).one()
            await maybe_resume_mission(db, step.run_id)
        else:
            _persist_nonterminal(db, job_id, lease_token, result)
    except Exception as exc:
        if isinstance(exc, LeaseLost):
            raise
        if lease_token is None:
            raise
        try:
            db.rollback()
            completed = _schedule_failure(db, job_id, lease_token, exc)
            if completed is not None:
                from app.workforce.agents.orchestration.continuation import (
                    maybe_resume_mission,
                )

                step = db.query(RunStep).filter(
                    RunStep.id == completed.run_step_id
                ).one()
                await maybe_resume_mission(db, step.run_id)
        except LeaseLost:
            logger.warning("Lease lost while recording failure for delegation job %s", job_id)
    finally:
        db.close()


async def delegation_loop() -> None:
    await agent_runtime_manager.start()
    await delegation_provider_manager.start()
    worker_id = f"delegation-{uuid.uuid4().hex[:12]}"
    while True:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            reconcile_expired_jobs(db, now)
            job_id = claim_due_job(db, worker_id, now)
        except Exception:
            logger.exception("Delegation worker claim/recovery failure")
            db.rollback()
            job_id = None
        finally:
            db.close()
        if job_id is None:
            await asyncio.sleep(DELEGATION_POLL_SECONDS)
            continue
        try:
            await process_delegation_job(job_id, worker_id)
        except LeaseLost:
            logger.warning("Delegation lease lost for job %s", job_id)
        except Exception:
            logger.exception("Delegation job %s failed unexpectedly", job_id)
