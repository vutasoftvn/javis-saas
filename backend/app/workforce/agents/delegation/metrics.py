from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.workforce.agents.delegation.models import DelegationJob


def delegation_metrics_snapshot(db: Session) -> dict[str, Any]:
    """Return bounded, identifier-free operational metrics for delegation."""
    now = datetime.now(timezone.utc)
    jobs = db.query(DelegationJob).all()
    queued = [job for job in jobs if job.status in {"queued", "retry_scheduled"}]
    queue_ages = [
        max(0.0, (now - _aware(job.available_at)).total_seconds())
        for job in queued
        if job.available_at is not None
    ]
    active = [
        job
        for job in jobs
        if job.status
        not in {"succeeded", "failed", "cancelled", "denied"}
    ]
    terminal_latencies = [
        max(0.0, (_aware(job.completed_at) - _aware(job.started_at)).total_seconds())
        for job in jobs
        if job.completed_at is not None and job.started_at is not None
    ]
    continuation_lag = (
        db.query(RunStep)
        .join(OutcomeRun, OutcomeRun.id == RunStep.run_id)
        .join(Outcome, Outcome.id == OutcomeRun.outcome_id)
        .filter(
            RunStep.status == "completed",
            OutcomeRun.status == "running",
        )
        .all()
    )
    continuation_lag_count = sum(
        1
        for step in continuation_lag
        if isinstance(step.inputs_jsonb, dict)
        and step.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
    )
    return {
        "queue_depth": len(queued),
        "oldest_queue_age_seconds": max(queue_ages, default=0.0),
        "active_jobs": len(active),
        "expired_leases": sum(
            1
            for job in active
            if job.lease_expires_at is not None and _aware(job.lease_expires_at) <= now
        ),
        "retry_attempts": sum(1 for job in jobs if job.attempt_no > 1),
        "dead_letters": sum(1 for job in jobs if job.status == "failed"),
        "approval_waiting": sum(1 for job in jobs if job.status == "waiting_approval"),
        "provider_latency_seconds_avg": (
            sum(terminal_latencies) / len(terminal_latencies)
            if terminal_latencies
            else 0.0
        ),
        "reserved_steps": sum(job.reserved_steps for job in active),
        "reserved_tool_calls": sum(job.reserved_tool_calls for job in active),
        "reserved_cost_usd": str(
            sum((job.reserved_cost_usd for job in active), Decimal("0"))
        ),
        "continuation_lag_count": continuation_lag_count,
    }


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
