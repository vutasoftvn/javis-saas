from __future__ import annotations

import logging
import os
import re
from typing import Any
import httpx

from agent_core.contracts.run import RunRequest, RunStatus, RunResult
from apps.cosa.agents.registry_loader import load_registered_agent_spec
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.events.trigger_policy import EventTriggerRule

logger = logging.getLogger(__name__)

__all__ = ["run_customer_support_autopilot", "resume_customer_support_autopilot"]

FORBIDDEN_AUTOPILOT_CAP_RE = re.compile(
    r"(billing\.|finance\.|\.opportunity\.|\.lead\.write)"
)


async def _resolve_trigger_rule(plane: CosaAgentPlane, rule_id: str) -> EventTriggerRule | None:
    # 1. Check in plane rules dict (mock / test setup)
    if hasattr(plane, "rules") and isinstance(plane.rules, dict) and rule_id in plane.rules:
        return plane.rules[rule_id]

    # 2. Check in event_intake_deps
    deps = getattr(plane, "event_intake_deps", None)
    if deps and hasattr(deps, "trigger_policy") and hasattr(deps.trigger_policy, "rule_store"):
        try:
            return await deps.trigger_policy.rule_store.get(rule_id)
        except Exception:
            return None

    return None


async def run_customer_support_autopilot(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> dict[str, Any]:
    run_id = payload["run_id"]
    workspace_id = payload["workspace_id"]
    trigger_rule_id = payload.get("trigger_rule_id")
    correlation_id = payload.get("correlation_id", "")
    stream_repo = getattr(plane, "run_stream_event_repository", None) or getattr(plane, "stream_event_repository", None)

    # 1. Kill-switch guard: re-check trigger rule
    if trigger_rule_id:
        rule = await _resolve_trigger_rule(plane, trigger_rule_id)
        if rule and not rule.enabled:
            logger.warning("Autopilot run %s cancelled because trigger rule %s is disabled", run_id, trigger_rule_id)
            if stream_repo:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=payload.get("conversation_id", ""),
                    event_type="run.cancelled",
                    payload={"reason": "trigger_rule_disabled"},
                    correlation_id=correlation_id,
                )
            return {"status": "cancelled", "reason": "trigger_rule_disabled"}

    # 2. Defense-in-depth: Assert capability refs in spec
    spec = COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC
    if getattr(plane, "spec_registry", None):
        fetched, spec_reason = await load_registered_agent_spec(
            plane.spec_registry, COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.id, version="1.0.0"
        )
        if fetched is not None:
            spec = fetched
        elif spec_reason == "agent_spec_content_invalid":
            logger.warning(
                "Registered autopilot spec %s invalid, falling back to in-code spec (reason=%s)",
                COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.id,
                spec_reason,
            )

    for cap in spec.capability_refs:
        if FORBIDDEN_AUTOPILOT_CAP_RE.search(cap):
            logger.error("Spec %s contains forbidden capability: %s", spec.id, cap)
            if stream_repo:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=payload.get("conversation_id", ""),
                    event_type="run.failed",
                    payload={"error": f"forbidden capability in autopilot spec: {cap}"},
                    correlation_id=correlation_id,
                )
            return {"status": "failed", "reason": f"forbidden_capability_{cap}"}

    # 3. Assemble read context
    thread_ref = payload.get("thread_ref", {})
    thread_id = thread_ref.get("thread_id")
    contact_id = thread_ref.get("contact_id")

    req = RunRequest(
        run_id=run_id,
        principal=payload.get("principal") or f"system:autopilot:{workspace_id}",
        root_executable_ref=spec.to_pinned_identity(),
        input={
            "thread_id": thread_id,
            "contact_id": contact_id,
            "intent": payload.get("intent", "faq"),
            "trigger_rule_id": trigger_rule_id,
        },
        workspace_id=workspace_id,
        conversation_id=payload.get("conversation_id", f"conv_ap_{run_id}"),
        metadata={
            "trigger_rule_id": trigger_rule_id,
            "thread_id": thread_id,
        },
    )

    # 4. Run kernel
    run_result = await plane.kernel.run(req, spec)

    if run_result.status == RunStatus.WAITING_APPROVAL:
        return {
            "status": "waiting_approval",
            "waits": run_result.interruptions_waits,
        }

    if run_result.status == RunStatus.COMPLETED:
        return {"status": "completed", "output": run_result.final_output}

    return {"status": "failed", "errors": run_result.errors}


async def resume_customer_support_autopilot(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> dict[str, Any]:
    run_id = payload["run_id"]
    workspace_id = payload["workspace_id"]
    trigger_rule_id = payload.get("trigger_rule_id")
    thread_id = payload.get("thread_id")
    correlation_id = payload.get("correlation_id", "")
    stream_repo = getattr(plane, "run_stream_event_repository", None) or getattr(plane, "stream_event_repository", None)

    # 1. Kill-switch check
    if trigger_rule_id:
        rule = await _resolve_trigger_rule(plane, trigger_rule_id)
        if rule and not rule.enabled:
            logger.warning("Autopilot resume %s cancelled because rule %s is disabled", run_id, trigger_rule_id)
            if stream_repo:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=payload.get("conversation_id", ""),
                    event_type="run.cancelled",
                    payload={"reason": "trigger_rule_disabled"},
                    correlation_id=correlation_id,
                )
            return {"status": "cancelled", "reason": "trigger_rule_disabled"}

    # 2. Check thread drift / human takeover
    if thread_id:
        try:
            thread_data = await plane.company_client.get(
                f"/commercial/engagement/threads/{thread_id}",
                headers={"X-Workspace-Id": workspace_id},
            )
            thread_info = thread_data.get("thread") or thread_data
            if thread_info.get("activeMode") == "human_assigned":
                logger.info("Autopilot resume %s aborted: thread %s was taken over by human", run_id, thread_id)
                if stream_repo:
                    await stream_mgr.emit(
                        stream_repo,
                        run_id=run_id,
                        conversation_id=payload.get("conversation_id", ""),
                        event_type="run.cancelled",
                        payload={"reason": "thread_taken_over"},
                        correlation_id=correlation_id,
                    )
                return {"status": "cancelled", "reason": "thread_taken_over"}
        except Exception as exc:
            logger.warning("Failed to verify thread activeMode for %s: %s", thread_id, exc)

    # 3. Execute approved message send
    body = payload.get("body", "")
    tool_call_id = payload.get("tool_call_id") or f"call_ap_{run_id}"

    res = await plane.company_client.post(
        f"/commercial/engagement/threads/{thread_id}/messages",
        json={
            "body": body,
            "idempotencyKey": tool_call_id,
            "templateRef": payload.get("template_ref"),
        },
        headers={"X-Workspace-Id": workspace_id},
    )

    message_id = str(res.get("messageId") or res.get("id") or "")
    return {
        "status": "completed",
        "message_id": message_id,
        "delivery_state": res.get("deliveryState", "queued"),
    }
