from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from apps.cosa.events import inbox
from apps.cosa.events.contracts import validate_envelope
from apps.cosa.events.workforce_employee_contract import (
    WORK_PACKAGE_QUEUED_EVENT,
    adapt_work_package_dispatch,
    is_workforce_dispatch_event,
)

CONSUMER = "agentos.event_intake"

TASK_RESULT_SUBMITTED_EVENT = "operating.task.result_submitted.v1"

# Signed Company→Agent work-package dispatch (Task 3/4) — schedule một run
# workforce dùng chung spec operations. target_spec_id giữ ổn định; employee/
# assignment/skill exact được resolve theo attribution trong payload ở worker.
_WORKFORCE_DISPATCH_SPEC_ID = "cosa.agents.operations"

# WGA — event founder chủ động phát (không phải autopilot), tự schedule task
# tương ứng KHÔNG cần operator provision EventTriggerRule. Map: event_type ->
# (task_type, target_spec_id).
_PLATFORM_SELF_TRIGGER: dict[str, tuple[str, str]] = {
    "operating.weekly_goal.set.v1": ("goal_decomposition", "cosa.agents.operations"),
    "operating.execution_plan.accepted.v1": ("workspace_task_sweep", "cosa.agents.operations"),
}


def _self_trigger_payload(event_type: str, env: object) -> dict:
    payload = getattr(env, "payload", {}) or {}
    actor = getattr(env, "actor", None)
    # `sub` cho mint_company_delegation = Company member/user id đã xác thực —
    # dùng actor.id của envelope (founder user id do services/company set khi phát).
    actor_id = getattr(actor, "id", None) or "0"
    ws = payload.get("workspaceId") or getattr(env, "workspaceId", "")
    corr = getattr(env, "correlationId", "")
    if event_type == "operating.weekly_goal.set.v1":
        return {
            "workspace_id": ws,
            "project_id": payload.get("projectId"),
            "weekly_plan_id": payload.get("weeklyPlanId"),
            "goal_text": payload.get("focus", ""),
            "origin": payload.get("origin", "command_center"),
            "origin_ref": payload.get("originRef"),
            "actor_id": actor_id,
            "correlation_id": corr,
        }
    # workspace_task_sweep
    return {
        "workspace_id": ws,
        "actor_id": actor_id,
        "correlation_id": corr,
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

        # Signed work-package dispatch (Task 3/4). Inbox dedup ở trên đảm bảo
        # 1 signed event -> 1 scheduled attempt; attribution sai -> fail closed.
        if is_workforce_dispatch_event(env.eventType):
            dispatch, error = adapt_work_package_dispatch(
                getattr(env, "payload", {}) or {}, event_type=env.eventType
            )
            if dispatch is None:
                await inbox_store.set_outcome(
                    conn, env.workspaceId, env.eventId, CONSUMER, "rejected"
                )
                return IntakeResult(outcome="rejected", reason=error)

            run_id = f"run_{env.eventId[:16]}" if env.eventId else None
            task_id = await deps.execution_plane.schedule_platform_task(
                target_spec_id=_WORKFORCE_DISPATCH_SPEC_ID,
                task_type="work_package",
                input_payload={
                    "run_id": run_id,
                    "workspace_id": dispatch.workspace_id,
                    "work_package_id": dispatch.work_package_id,
                    "work_attempt_id": dispatch.work_attempt_id,
                    "agent_instance_id": dispatch.agent_instance_id,
                    "assignment_id": dispatch.assignment_id,
                    "signed_assignment_id": dispatch.assignment_id,
                    "effective_priority": dispatch.effective_priority,
                    "expected_capability_refs": list(dispatch.expected_capability_refs),
                    "correlation_id": dispatch.correlation_id,
                    "is_reassignment": dispatch.is_reassignment,
                    "agent_profile": "operations",
                },
                coalescing_key=(
                    f"wp:{dispatch.workspace_id}:{dispatch.work_attempt_id}"
                    if env.eventType == WORK_PACKAGE_QUEUED_EVENT
                    else f"wp-reassign:{dispatch.workspace_id}:{dispatch.work_package_id}"
                ),
            )
            await inbox_store.set_outcome(
                conn, env.workspaceId, env.eventId, CONSUMER, "accepted", task_id
            )
            return IntakeResult(outcome="accepted", scheduledTaskId=task_id)

        # Task 4A — deterministic Outcome Analysis dispatch. Resolve binding
        # exact (không fallback generic operations); MANUAL / missing binding
        # -> KHÔNG schedule tự động.
        if env.eventType == TASK_RESULT_SUBMITTED_EVENT:
            from apps.cosa.workforce_dispatch import resolve_and_schedule_outcome_analysis

            outcome, task_id = await resolve_and_schedule_outcome_analysis(deps, env)
            await inbox_store.set_outcome(
                conn, env.workspaceId, env.eventId, CONSUMER, outcome, task_id
            )
            return IntakeResult(outcome=outcome, scheduledTaskId=task_id)

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
