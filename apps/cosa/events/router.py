from __future__ import annotations

from typing import Any, Optional
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
    scheduledTaskId: Optional[str] = None
    reason: Optional[str] = None


async def handle_event(deps: Any, raw_body: dict, signature: str) -> IntakeResult:
    if not deps.local_auth.verify(signature, raw_body):
        raise Unauthenticated("invalid local signature")

    env = validate_envelope(raw_body)

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
