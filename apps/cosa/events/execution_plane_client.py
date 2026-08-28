"""LocalExecutionPlaneScheduleClient — schedule một agent run tại LOCAL
execution plane khi một trigger rule khớp. Payload là REFERENCE-ONLY
(workspace/event/correlation id + spec pin + aggregate ref) — không nhân bản
raw business payload lên scheduler (ADR-LOCAL-FIRST-001).
"""

from __future__ import annotations

from typing import Any

from agent_core.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient

__all__ = ["LocalExecutionPlaneScheduleClient"]


class LocalExecutionPlaneScheduleClient:
    def __init__(self, base_url: str, service_token: str | None = None, client: Any = None) -> None:
        self._sched = HttpControlPlaneSchedulerClient(
            base_url=base_url, service_token=service_token, client=client
        )

        agent_profile = (
            "customer_support_autopilot"
            if rule.agent_spec.id == "cosa.agents.customer_support_autopilot"
            else "customer_support"
            if rule.agent_spec.id == "cosa.agents.customer_support"
            else None
        )

        input_payload = {
            "kind": "event_trigger",
            "workspace_id": env.workspaceId,
            "event_id": env.eventId,
            "correlation_id": env.correlationId,
            "trigger_rule_id": rule.rule_id,
            "agent_spec": {
                "id": rule.agent_spec.id,
                "version": rule.agent_spec.version,
                "definition_hash": rule.agent_spec.definition_hash,
            },
            "aggregate_ref": {"type": env.aggregateType, "id": env.aggregateId},
            "mode": rule.mode,
        }
        if agent_profile:
            input_payload["agent_profile"] = agent_profile
        if env.aggregateType in ("engagement.thread", "engagement_thread", "thread"):
            input_payload["thread_ref"] = {"thread_id": env.aggregateId}

        record = await self._sched.schedule(
            target_spec_id=rule.agent_spec.id,
            target_spec_kind="agent",
            coalescing_key=f"evt:{env.workspaceId}:{env.eventId}",
            input_payload=input_payload,
        )
        return record.task_id

    async def aclose(self) -> None:
        await self._sched.aclose()
