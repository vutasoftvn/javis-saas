from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from apps.cosa.events import inbox
from apps.cosa.events.contracts import validate_envelope

CONSUMER = "agentos.event_intake"

# WGA — event founder chủ động phát (không phải autopilot), tự schedule task
# tương ứng KHÔNG cần operator provision EventTriggerRule. Map: event_type ->
# (task_type, target_spec_id).
_PLATFORM_SELF_TRIGGER: dict[str, tuple[str, str]] = {
    "operating.weekly_goal.set.v1": ("goal_decomposition", "cosa.agents.operations"),
    "operating.execution_plan.accepted.v1": ("workspace_task_sweep", "cosa.agents.operations"),
}


def _self_trigger_payload(event_type: str, env: object) -> dict:
    payload = getattr(env, "payload", {}) or {}
    if event_type == "operating.weekly_goal.set.v1":
        return {
            "workspace_id": payload.get("workspaceId") or getattr(env, "workspaceId", ""),
            "project_id": payload.get("projectId"),
            "weekly_plan_id": payload.get("weeklyPlanId"),
            "goal_text": payload.get("focus", ""),
            "origin": payload.get("origin", "command_center"),
            "origin_ref": payload.get("originRef"),
            "correlation_id": getattr(env, "correlationId", ""),
        }
    # workspace_task_sweep
    return {
        "workspace_id": payload.get("workspaceId") or getattr(env, "workspaceId", ""),
        "correlation_id": getattr(env, "correlationId", ""),
    }


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

        self_trigger = _PLATFORM_SELF_TRIGGER.get(env.eventType)
        if self_trigger is not None:
            task_type, target_spec_id = self_trigger
            task_id = await deps.execution_plane.schedule_platform_task(
                target_spec_id=target_spec_id,
                task_type=task_type,
                input_payload=_self_trigger_payload(env.eventType, env),
                coalescing_key=f"wga:{env.workspaceId}:{env.eventType}:{env.aggregateId}",
            )
            await inbox_store.set_outcome(
                conn, env.workspaceId, env.eventId, CONSUMER, "accepted", task_id
            )
            return IntakeResult(outcome="accepted", scheduledTaskId=task_id)

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
