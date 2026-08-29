from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from apps.cosa.events import inbox
from apps.cosa.events.contracts import validate_envelope

CONSUMER = "agentos.event_intake"


class Unauthenticated(Exception):
    pass


class PermissionDenied(Exception):
    pass


class IntakeResult(BaseModel):
    outcome: str
    scheduledTaskId: str | None = None
    reason: str | None = None


async def handle_event(deps: Any, raw_body: bytes, signature: str) -> IntakeResult:
    # Verify HMAC trên đúng bytes body trước khi parse — không tin nội dung
    # chưa xác thực, và tránh lệch chữ ký do re-serialize.
    if not deps.local_auth.verify(signature, raw_body):
        raise Unauthenticated("invalid local signature")

    try:
        parsed = json.loads(raw_body)
    except (ValueError, TypeError) as e:
        raise ValueError("event body is not valid JSON") from e

    env = validate_envelope(parsed)

    if deps.caller_workspace_id is not None and env.workspaceId != deps.caller_workspace_id:
        raise PermissionDenied("cross-workspace envelope")

    inbox_store = getattr(deps, "inbox_store", inbox)

    async with deps.db.begin() as conn:
        state = await inbox_store.record(
            conn,
            workspace_id=env.workspaceId,
            event_id=env.eventId,
            consumer_name=CONSUMER,
            event_type=env.eventType,
            correlation_id=env.correlationId,
            outcome="pending",
            aggregate_type=env.aggregateType,
            aggregate_id=env.aggregateId,
        )
        if state == "duplicate":
            return IntakeResult(outcome="duplicate")

        decision = await deps.trigger_policy.resolve(
            workspace_id=env.workspaceId,
            event_type=env.eventType,
            aggregate={"type": env.aggregateType, "id": env.aggregateId},
        )
        if decision.outcome != "accepted":
            await inbox_store.set_outcome(
                conn,
                env.workspaceId,
                env.eventId,
                CONSUMER,
                decision.outcome,
            )
            return IntakeResult(outcome=decision.outcome, reason=decision.reason)

        task_id = await deps.execution_plane.schedule_reference_task(decision.rule, env)
        await inbox_store.set_outcome(
            conn,
            env.workspaceId,
            env.eventId,
            CONSUMER,
            "accepted",
            task_id,
        )

    return IntakeResult(outcome="accepted", scheduledTaskId=task_id)
