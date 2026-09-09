"""LocalExecutionPlaneScheduleClient — schedule một agent run tại LOCAL
execution plane khi một trigger rule khớp. Payload là REFERENCE-ONLY
(workspace/event/correlation id + spec pin + aggregate ref) — không nhân bản
raw business payload lên scheduler (ADR-LOCAL-FIRST-001).
"""

from __future__ import annotations

from typing import Any

from agent.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient

from apps.cosa.events.event_run_contract import build_event_run_envelope

__all__ = ["LocalExecutionPlaneScheduleClient"]


class LocalExecutionPlaneScheduleClient:
    def __init__(self, base_url: str, service_token: str | None = None, client: Any = None) -> None:
        self._sched = HttpControlPlaneSchedulerClient(
            base_url=base_url, service_token=service_token, client=client
        )

    async def schedule_reference_task(self, rule: Any, env: Any, run_id: str | None = None) -> str:
        envelope = build_event_run_envelope(rule=rule, env=env, run_id=run_id)
        coalescing_key = f"evt:{env.workspaceId}:{env.eventId}:{rule.rule_id}"

        record = await self._sched.schedule(
            target_spec_id=rule.agent_spec.id,
            target_spec_kind="agent",
            coalescing_key=coalescing_key,
            input_payload=envelope.model_dump(),
        )
        return record.task_id

    async def schedule_platform_task(
        self,
        *,
        target_spec_id: str,
        task_type: str,
        input_payload: dict[str, Any],
        coalescing_key: str | None = None,
    ) -> str:
        """Schedule a first-party WGA task (goal_decomposition / task_execution)
        directly, bypassing the operator-provisioned EventTriggerRule flow.
        These are founder-initiated, not autopilot."""
        payload = {"task_type": task_type, **input_payload}
        record = await self._sched.schedule(
            target_spec_id=target_spec_id,
            target_spec_kind="agent",
            coalescing_key=coalescing_key,
            input_payload=payload,
        )
        return record.task_id

    async def schedule_automation_dispatch(self, env: Any) -> str:
        """COSA Automation MVP (Task 4). `env.payload` is exactly
        AutomationDispatchEnvelopeV1 (reference-only). Returns the task id."""
        envelope = dict(getattr(env, "payload", {}) or {})
        result = await self._sched.schedule_automation_dispatch(envelope)
        return str(result.get("taskId") or "")

    async def aclose(self) -> None:
        await self._sched.aclose()
