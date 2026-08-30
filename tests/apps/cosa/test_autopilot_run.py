from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent.contracts.run import RunResult, RunStatus
from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.governance.contracts import PinnedSpecIdentity
from agent.runs.repository import InMemoryRunRepository

from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC
from apps.cosa.events.trigger_policy import EventTriggerRule
from apps.cosa.worker.autopilot_run import (
    resume_customer_support_autopilot,
    run_customer_support_autopilot,
)


class MockEventStreamManager:
    def __init__(self):
        self.emitted = []

    async def emit(self, repo, run_id, conversation_id, event_type, payload, correlation_id=""):
        self.emitted.append({
            "run_id": run_id,
            "event_type": event_type,
            "payload": payload,
        })


class MockPlane:
    def __init__(self, run_repo=None):
        self.run_repository = run_repo or InMemoryRunRepository()
        self.stream_event_repository = MagicMock()
        self.run_stream_event_repository = self.stream_event_repository
        self.kernel = AsyncMock()
        self.company_client = AsyncMock()
        self.spec_registry = None
        self.rules = {}

    def set_rule(self, rule: EventTriggerRule):
        self.rules[rule.rule_id] = rule


@pytest.mark.asyncio
async def test_autopilot_fails_closed_when_registered_spec_content_is_invalid():
    """Simulates registry corruption/drift via a field with no default (`id`) so
    this stays a genuine invalid-content test regardless of which other fields
    later become optional — see the autopilot-copilot-initial-input-unblock plan."""
    plane = MockPlane()
    plane.spec_registry = MagicMock()
    plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(
            content=COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.model_dump(
                mode="json", exclude={"id"}
            )
        )
    )
    plane.kernel.run.return_value = RunResult(
        run_id="run_ap_stale_spec_1",
        status=RunStatus.COMPLETED,
        final_output={"unreachable": True},
    )

    result = await run_customer_support_autopilot(
        plane,
        MockEventStreamManager(),
        {
            "run_id": "run_ap_stale_spec_1",
            "workspace_id": "ws_1",
            "agent_profile": "customer_support_autopilot",
            "thread_ref": {"thread_id": "th_1"},
        },
    )

    assert result == {"status": "failed", "reason": "agent_spec_content_invalid"}
    plane.kernel.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_autopilot_kill_switch_guard_cancels_run_if_rule_disabled():
    plane = MockPlane()
    stream_mgr = MockEventStreamManager()

    disabled_rule = EventTriggerRule(
        rule_id="rule_autopilot_1",
        workspace_id="ws_1",
        event_type="engagement.message.received.v1",
        agent_spec=PinnedSpecIdentity(
            spec_id="cosa.agents.customer_support_autopilot",
            spec_version="1.1.0",
            spec_kind="agent",
            definition_hash="hash_1",
        ),
        mode="write",
        max_runs_per_aggregate_per_day=10,
        required_capabilities=("engagement.message.send",),
        enabled=False,  # RULE IS DISABLED
    )
    plane.set_rule(disabled_rule)

    payload = {
        "run_id": "run_ap_kill_1",
        "workspace_id": "ws_1",
        "trigger_rule_id": "rule_autopilot_1",
        "agent_profile": "customer_support_autopilot",
        "thread_ref": {"thread_id": "th_101"},
    }

    res = await run_customer_support_autopilot(plane, stream_mgr, payload)
    assert res["status"] == "cancelled"
    assert res["reason"] == "trigger_rule_disabled"

    # Kernel is NOT called
    plane.kernel.run.assert_not_called()

    # Stream emitted run.cancelled
    event_types = [e["event_type"] for e in stream_mgr.emitted]
    assert "run.cancelled" in event_types


@pytest.mark.asyncio
async def test_autopilot_suspends_when_approval_required():
    plane = MockPlane()
    stream_mgr = MockEventStreamManager()

    enabled_rule = EventTriggerRule(
        rule_id="rule_autopilot_2",
        workspace_id="ws_2",
        event_type="engagement.message.received.v1",
        agent_spec=PinnedSpecIdentity(
            spec_id="cosa.agents.customer_support_autopilot",
            spec_version="1.1.0",
            spec_kind="agent",
            definition_hash="hash_2",
        ),
        mode="write",
        max_runs_per_aggregate_per_day=10,
        required_capabilities=("engagement.message.send",),
        enabled=True,
    )
    plane.set_rule(enabled_rule)

    # Mock kernel returning WAITING_APPROVAL
    plane.kernel.run.return_value = RunResult(
        run_id="run_ap_appr_1",
        status=RunStatus.WAITING_APPROVAL,
        interruptions_waits=[
            WaitDescriptor(
                kind=WaitKind.APPROVAL,
                reason="Approval required for sending message",
                related_ref="appr_send_1",
                checkpoint_ref="ckpt_send_1",
            )
        ],
    )

    payload = {
        "run_id": "run_ap_appr_1",
        "workspace_id": "ws_2",
        "trigger_rule_id": "rule_autopilot_2",
        "agent_profile": "customer_support_autopilot",
        "thread_ref": {"thread_id": "th_202"},
    }

    res = await run_customer_support_autopilot(plane, stream_mgr, payload)
    assert res["status"] == "waiting_approval"

    # 0 Company message sent
    plane.company_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_autopilot_resume_rechecks_rule_and_active_mode_before_send():
    plane = MockPlane()
    stream_mgr = MockEventStreamManager()

    enabled_rule = EventTriggerRule(
        rule_id="rule_autopilot_3",
        workspace_id="ws_3",
        event_type="engagement.message.received.v1",
        agent_spec=PinnedSpecIdentity(
            spec_id="cosa.agents.customer_support_autopilot",
            spec_version="1.1.0",
            spec_kind="agent",
            definition_hash="hash_3",
        ),
        mode="write",
        max_runs_per_aggregate_per_day=10,
        required_capabilities=("engagement.message.send",),
        enabled=True,
    )
    plane.set_rule(enabled_rule)

    # 1. Test resume when thread was taken over by human (activeMode == "human_assigned")
    plane.company_client.get.return_value = {
        "thread": {"id": "th_303", "activeMode": "human_assigned", "status": "open"}
    }

    payload = {
        "run_id": "run_ap_resume_1",
        "workspace_id": "ws_3",
        "trigger_rule_id": "rule_autopilot_3",
        "checkpoint_ref": "ckpt_send_3",
        "thread_id": "th_303",
        "tool_call_id": "call_send_3",
        "body": "Phản hồi đã duyệt",
    }

    res1 = await resume_customer_support_autopilot(plane, stream_mgr, payload)
    assert res1["status"] == "cancelled"
    assert res1["reason"] == "thread_taken_over"
    plane.company_client.post.assert_not_called()

    # 2. Test resume happy path (activeMode == "unassigned" or "team_queue")
    plane.company_client.get.return_value = {
        "thread": {"id": "th_303", "activeMode": "team_queue", "status": "open"}
    }
    plane.company_client.post.return_value = {
        "messageId": "msg_auto_303",
        "deliveryState": "queued",
    }

    res2 = await resume_customer_support_autopilot(plane, stream_mgr, payload)
    assert res2["status"] == "completed"
    assert res2["message_id"] == "msg_auto_303"
    plane.company_client.post.assert_called_once()
