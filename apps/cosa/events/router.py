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
from apps.cosa.project_activity.company_event_projector import consume_company_event

CONSUMER = "agentos.event_intake"

TASK_RESULT_SUBMITTED_EVENT = "operating.task.result_submitted.v1"

# Project Activity event types — Company events that project into Founder Activity Feed
PROJECT_ACTIVITY_EVENT_TYPES = frozenset([
    "operations.task.created.v1",
    "operations.task.completed.v1",
    "operations.work_package.created.v1",
    "operations.decision.recorded.v1",
    "operations.evidence.linked.v1",
    "operations.risk.raised.v1",
    "operations.risk.resolved.v1",
])

# COSA Automation MVP (Task 4) — Company outbox event carrying exactly
# AutomationDispatchEnvelopeV1. Reference-only; anything else is quarantined.
AUTOMATION_INVOCATION_REQUESTED_EVENT = "automation.invocation.requested.v1"
_AUTOMATION_ENVELOPE_FIELDS = (
    "schema_version",
    "invocation_id",
    "workspace_id",
    "automation_key",
    "revision",
    "revision_hash",
    "trigger_kind",
    "trigger_identity",
    "correlation_id",
    "requested_at",
)
# Shared across every "curated reference-only dispatch envelope" event type in
# this router (automation invocation, governed workflow run, ...): none of
# them may ever carry raw prompt/credential/business content, only opaque ids.
_REFERENCE_ENVELOPE_FORBIDDEN_KEYS = (
    "input",
    "input_payload",
    "prompt",
    "credential",
    "secret",
    "authorization",
    "connector_grant",
    "document",
)
_AUTOMATION_FORBIDDEN_KEYS = _REFERENCE_ENVELOPE_FORBIDDEN_KEYS


# Task 11 (plan 2026-09-13-founder-configurable-agent-skill-workflow) — signed
# Company event dispatching one governed workflow run (project workflow
# binding fired). Reference-only: workspace/project/binding/manifest-pin ids,
# never raw prompt/credential — same discipline as the automation envelope above.
GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT = "operations.workflow_run.requested.v1"
_GOVERNED_WORKFLOW_ENVELOPE_FIELDS = (
    "workspace_id",
    "project_id",
    "workflow_binding_id",
    "workflow_asset_id",
    "workflow_version",
    "workflow_definition_hash",
    "idempotency_key",
)
_GOVERNED_WORKFLOW_FORBIDDEN_KEYS = _REFERENCE_ENVELOPE_FORBIDDEN_KEYS


def _validate_governed_workflow_payload(payload: dict) -> str | None:
    """Return an error string if the payload is not a clean workflow-run trigger."""
    if not isinstance(payload, dict):
        return "governed workflow payload is not an object"
    for k in _GOVERNED_WORKFLOW_FORBIDDEN_KEYS:
        if k in payload:
            return f"governed workflow payload carries forbidden key '{k}'"
    for k in _GOVERNED_WORKFLOW_ENVELOPE_FIELDS:
        if payload.get(k) in (None, ""):
            return f"governed workflow payload missing '{k}'"
    return None


def _validate_automation_payload(payload: dict) -> str | None:
    """Return an error string if the payload is not a clean dispatch envelope."""
    if not isinstance(payload, dict):
        return "automation payload is not an object"
    for k in _AUTOMATION_FORBIDDEN_KEYS:
        if k in payload:
            return f"automation payload carries forbidden key '{k}'"
    for k in _AUTOMATION_ENVELOPE_FIELDS:
        if payload.get(k) in (None, ""):
            return f"automation payload missing '{k}'"
    if payload.get("schema_version") != 1:
        return "automation payload schema_version must be 1"
    if payload.get("trigger_kind") not in ("manual", "schedule", "business_event"):
        return "automation payload trigger_kind invalid"
    return None


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

    # Founder asset commands need a durable inbox commit before authoring.
    # Their callback can fail after authoring commits; duplicate relay then
    # retries only the persisted callback rather than rerunning the command.
    if env.eventType == "founder.asset.commanded.v1":
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

        from apps.cosa.events.founder_asset_events import (
            dispatch_founder_asset_command,
            replay_founder_asset_callback,
        )

        if state == "duplicate":
            outcome, reason = await replay_founder_asset_callback(
                deps,
                workspace_id=env.workspaceId,
                command_id=(getattr(env, "payload", {}) or {}).get("commandId", ""),
            )
            if outcome != "duplicate":
                async with deps.db.begin() as conn:
                    await inbox_store.set_outcome(
                        conn, env.workspaceId, env.eventId, CONSUMER, outcome, reason
                    )
            return IntakeResult(outcome=outcome, reason=reason)

        outcome, reason = await dispatch_founder_asset_command(deps, env)
        async with deps.db.begin() as conn:
            await inbox_store.set_outcome(
                conn, env.workspaceId, env.eventId, CONSUMER, outcome, reason
            )
        return IntakeResult(outcome=outcome, reason=reason if outcome != "accepted" else None)

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

        # Project Activity projection — consume Company business events (task, decision,
        # evidence, risk) and project into durable Founder Activity Feed (Task 4).
        # Đây là side-effect BỔ SUNG (best-effort), KHÔNG được return sớm/thế
        # chỗ pipeline dispatch gốc bên dưới (EventTriggerRule/self-trigger) —
        # các event type như operations.task.created.v1 đã có consumer khác
        # (schedule_reference_task) từ trước Task 4; return sớm ở đây từng
        # khiến consumer đó không bao giờ chạy nữa (regression phát hiện qua
        # test_local_event_intake.py).
        if env.eventType in PROJECT_ACTIVITY_EVENT_TYPES:
            project_activity_repo = getattr(deps, "project_activity_repository", None)
            if project_activity_repo is not None:
                await consume_company_event(project_activity_repo, parsed)

        # COSA Automation MVP (Task 4) — curated automation dispatch. Validate
        # the envelope BEFORE scheduling; a malformed/leaky payload is
        # quarantined, never routed through the generic EventTriggerRule path
        # and never given a generic profile fallback.
        if env.eventType == AUTOMATION_INVOCATION_REQUESTED_EVENT:
            payload = getattr(env, "payload", {}) or {}
            error = _validate_automation_payload(payload)
            if error is not None:
                await inbox_store.set_outcome(
                    conn, env.workspaceId, env.eventId, CONSUMER, "rejected"
                )
                return IntakeResult(outcome="rejected", reason=error)
            if payload["workspace_id"] != env.workspaceId:
                await inbox_store.set_outcome(
                    conn, env.workspaceId, env.eventId, CONSUMER, "rejected"
                )
                return IntakeResult(outcome="rejected", reason="workspace mismatch")

            task_id = await deps.execution_plane.schedule_automation_dispatch(env)
            await inbox_store.set_outcome(
                conn, env.workspaceId, env.eventId, CONSUMER, "accepted", task_id
            )
            return IntakeResult(outcome="accepted", scheduledTaskId=task_id)

        # Task 11 — governed workflow run trigger. `idempotency_key` yields a
        # deterministic run_id so a retried Company event (same key, new
        # eventId) and this consumer's own inbox dedup (same eventId) both
        # collapse to exactly one scheduled task / one run — never a second
        # execution of the same manifest.
        if env.eventType == GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT:
            payload = getattr(env, "payload", {}) or {}
            error = _validate_governed_workflow_payload(payload)
            if error is not None:
                await inbox_store.set_outcome(
                    conn, env.workspaceId, env.eventId, CONSUMER, "rejected"
                )
                return IntakeResult(outcome="rejected", reason=error)
            if payload["workspace_id"] != env.workspaceId:
                await inbox_store.set_outcome(
                    conn, env.workspaceId, env.eventId, CONSUMER, "rejected"
                )
                return IntakeResult(outcome="rejected", reason="workspace mismatch")

            # Workspace-scoped: `idempotency_key` is Company-generated and not
            # guaranteed globally unique across workspaces, and neither
            # run_id nor manifest lookups are workspace-scoped downstream —
            # without the workspace_id prefix, two different workspaces could
            # collide onto the same run_id/manifest.
            run_id = f"run_wf_{payload['workspace_id']}_{payload['idempotency_key']}"
            task_id = await deps.execution_plane.schedule_platform_task(
                target_spec_id=payload["workflow_asset_id"],
                task_type="governed_workflow_run",
                input_payload={
                    "run_id": run_id,
                    "workspace_id": payload["workspace_id"],
                    "project_id": payload["project_id"],
                    "workflow_binding_id": payload["workflow_binding_id"],
                    "workflow_asset_id": payload["workflow_asset_id"],
                    "workflow_version": payload["workflow_version"],
                    "workflow_definition_hash": payload["workflow_definition_hash"],
                    "project_agent_deployment_id": payload.get("project_agent_deployment_id"),
                    "role_deployment_id": payload.get("role_deployment_id"),
                    "correlation_id": payload.get("correlation_id") or env.correlationId,
                },
                coalescing_key=f"governed_workflow_run:{payload['workspace_id']}:{run_id}",
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
