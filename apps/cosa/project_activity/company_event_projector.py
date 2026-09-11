"""Consume signed Company business events and project them into Project Activity Feed.

Transforms Company outbox events (task.created, decision.recorded, evidence.linked,
risk.raised/resolved) into durable ProjectActivityEventRecord entries with:
- idempotent append using Company eventId as dedup key
- redacted summary (reference-only, no secrets/PII)
- project_id validation and isolation
- source reference tracking
"""

from __future__ import annotations

import logging
from typing import Any

from agent.project_activity.models import ProjectActivityEventRecord
from agent.project_activity.repository import ProjectActivityRepository

__all__ = ["consume_company_event"]

logger = logging.getLogger(__name__)

# Map Company event types to Activity Feed event kinds
COMPANY_EVENT_TO_ACTIVITY_KIND = {
    "operations.task.created.v1": "task.created",
    "operations.task.completed.v1": "task.completed",
    "operations.work_package.created.v1": "work_package.created",
    "operations.decision.recorded.v1": "decision.recorded",
    "operations.evidence.linked.v1": "evidence.linked",
    "operations.risk.raised.v1": "risk.raised",
    "operations.risk.resolved.v1": "risk.resolved",
}

# Allowed keys in payload for redacted summary (reference-only, safe fields)
ALLOWED_SUMMARY_KEYS = {
    "task_id",
    "taskId",
    "project_id",
    "projectId",
    "decision_id",
    "decisionId",
    "evidence_ref",
    "evidenceRef",
    "risk_id",
    "riskId",
    "title",
    "status",
}


def _build_redacted_summary(payload: dict) -> dict:
    """Extract only safe, reference-only fields from payload for Activity Feed summary."""
    redacted = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in ALLOWED_SUMMARY_KEYS and isinstance(value, (str, int, bool, type(None))):
                redacted[key] = value
    return redacted


async def consume_company_event(
    repo: ProjectActivityRepository,
    envelope: dict[str, Any],
) -> dict[str, str | None]:
    """Consume a signed Company business event and project into Activity Feed.

    Args:
        repo: ProjectActivityRepository for persisting the projection
        envelope: Validated BusinessEventEnvelope from Company outbox

    Returns:
        {
            "outcome": "accepted" | "duplicate" | "rejected",
            "reason": optional error reason
        }
    """
    event_type = envelope.get("eventType", "")

    # Only consume project-scoped Hub-visible event types
    if event_type not in COMPANY_EVENT_TO_ACTIVITY_KIND:
        return {"outcome": "rejected", "reason": f"unknown event type: {event_type}"}

    workspace_id = envelope.get("workspaceId", "")
    project_id = envelope.get("projectId")
    event_id = envelope.get("eventId", "")

    # Require projectId for Hub-visible events
    if not project_id:
        return {
            "outcome": "rejected",
            "reason": f"project-scoped event {event_type} missing projectId",
        }

    if not workspace_id or not event_id:
        return {"outcome": "rejected", "reason": "missing workspace or event ID"}

    # Validate payload project_id matches envelope (if present)
    payload = envelope.get("payload", {}) or {}
    if isinstance(payload, dict):
        payload_project_id = payload.get("project_id")
        if payload_project_id and payload_project_id != project_id:
            return {
                "outcome": "rejected",
                "reason": f"payload project_id mismatch: {payload_project_id} vs {project_id}",
            }

    # Extract actor info
    actor = envelope.get("actor") or {}
    actor_kind = actor.get("kind", "system")
    actor_id = actor.get("id", "")

    # Build the Activity Feed event
    correlation_id = envelope.get("correlationId", "")
    aggregate_id = envelope.get("aggregateId", "")
    occurred_at = envelope.get("occurredAt")

    # Idempotency key: company event ID + event type + source aggregate version
    # Using Company eventId as the base for dedup
    idempotency_key = f"company:{event_id}:{event_type}:1"

    activity_event = ProjectActivityEventRecord(
        event_id=event_id,
        workspace_id=workspace_id,
        project_id=project_id,
        idempotency_key=idempotency_key,
        kind=COMPANY_EVENT_TO_ACTIVITY_KIND[event_type],
        phase="business",
        status=payload.get("status", "pending") if isinstance(payload, dict) else "pending",
        actor_kind=actor_kind,
        actor_id=actor_id,
        correlation_id=correlation_id,
        source_type="company_event",
        source_id=aggregate_id,
        source_version="1",
        classification=envelope.get("classification", "internal"),
        summary=_build_redacted_summary(payload),
    )

    # Append idempotently to Activity Feed
    try:
        recorded = await repo.append_if_absent(activity_event)

        # Idempotent delivery check — if project_sequence was None before, it's a new event
        if recorded.project_sequence == activity_event.project_sequence:
            # First time seeing this idempotency key
            logger.info(
                "projected company event to activity feed",
                extra={
                    "event_id": event_id,
                    "workspace_id": workspace_id,
                    "project_id": project_id,
                    "event_type": event_type,
                    "project_sequence": recorded.project_sequence,
                },
            )
            return {"outcome": "accepted"}
        else:
            # Duplicate delivery — sequence was already assigned by previous attempt
            logger.info(
                "duplicate company event delivery",
                extra={
                    "event_id": event_id,
                    "project_sequence": recorded.project_sequence,
                },
            )
            return {"outcome": "duplicate"}
    except Exception as e:
        logger.exception("failed to project company event", extra={"event_id": event_id})
        return {"outcome": "rejected", "reason": f"projection error: {str(e)}"}
