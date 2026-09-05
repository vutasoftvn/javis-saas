from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.events.event_run_contract import (
    EventRunEnvelope,
    adapt_event_task_payload,
    build_event_run_envelope,
)
from apps.cosa.events.execution_plane_client import LocalExecutionPlaneScheduleClient
from apps.cosa.worker.main import dispatch_one_task
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


class _FakeSpec:
    def __init__(
        self,
        id: str = "cosa.agents.customer_support_autopilot",
        version: str = "1.2.0",
        definition_hash: str = "hash_autopilot_123",
    ) -> None:
        self.id = id
        self.version = version
        self.definition_hash = definition_hash


class _FakeRule:
    def __init__(
        self,
        rule_id: str = "rule_test_01",
        spec: _FakeSpec | None = None,
        mode: str = "proposal",
        enabled: bool = True,
    ) -> None:
        self.rule_id = rule_id
        self.agent_spec = spec or _FakeSpec()
        self.mode = mode
        self.enabled = enabled


class _FakeEnvelope:
    def __init__(
        self,
        event_id: str = "evt_001",
        workspace_id: str = "ws_test",
        aggregate_type: str = "engagement.thread",
        aggregate_id: str = "th_999",
        correlation_id: str = "corr_001",
    ) -> None:
        self.eventId = event_id
        self.workspaceId = workspace_id
        self.aggregateType = aggregate_type
        self.aggregateId = aggregate_id
        self.correlationId = correlation_id


def _build_plane(scheduler: RunScheduler | None = None) -> Any:
    return build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        scheduler=scheduler or RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


@pytest.mark.asyncio
async def test_producer_to_worker_dispatch_contract_success():
    """Producer schedule_reference_task -> worker dispatch_one_task thành công với EventRunEnvelope."""
    scheduler = RunScheduler()
    plane = _build_plane(scheduler=scheduler)

    # Bridge HttpControlPlaneSchedulerClient to in-memory RunScheduler
    async def fake_schedule(target_spec_id, target_spec_kind, coalescing_key, input_payload):
        return await scheduler.schedule(
            target_spec_id=target_spec_id,
            target_spec_kind=target_spec_kind,
            coalescing_key=coalescing_key,
            input_payload=input_payload,
        )

    client = LocalExecutionPlaneScheduleClient(base_url="http://control-plane.internal")
    client._sched.schedule = fake_schedule  # type: ignore

    rule = _FakeRule(
        rule_id="rule_autopilot_1",
        spec=_FakeSpec(id="cosa.agents.customer_support_autopilot"),
    )
    env = _FakeEnvelope(
        event_id="evt_alpha",
        workspace_id="ws_main",
        aggregate_type="engagement.thread",
        aggregate_id="thread_42",
    )

    task_id = await client.schedule_reference_task(rule, env)
    assert task_id

    # Poll from scheduler and dispatch via worker
    tasks = await scheduler.poll_due_tasks()
    assert len(tasks) == 1
    task = tasks[0]

    # Verify task.input_payload has schema_version 1 and task_type run
    payload = task.input_payload
    assert payload.get("schema_version") == 1
    assert payload.get("task_type") == "run"
    assert payload.get("run_id")
    assert payload.get("trigger_rule_id") == "rule_autopilot_1"
    assert payload.get("agent_profile") == "customer_support_autopilot"

    # Worker dispatch should execute without error
    with patch("apps.cosa.worker.main.execute_run_task", new_callable=AsyncMock) as mock_exec:
        await dispatch_one_task(plane, task)
        mock_exec.assert_called_once()
        call_payload = mock_exec.call_args[0][2]
        assert call_payload["run_id"] == payload["run_id"]
        assert call_payload["thread_ref"] == {"thread_id": "thread_42"}


@pytest.mark.asyncio
async def test_duplicate_event_same_rule_coalesces_single_run():
    """Duplicate event + same rule -> cùng coalescing_key, chỉ sinh 1 run."""
    scheduler = RunScheduler()
    client = LocalExecutionPlaneScheduleClient(base_url="http://control-plane.internal")

    async def fake_schedule(target_spec_id, target_spec_kind, coalescing_key, input_payload):
        return await scheduler.schedule(
            target_spec_id=target_spec_id,
            target_spec_kind=target_spec_kind,
            coalescing_key=coalescing_key,
            input_payload=input_payload,
        )

    client._sched.schedule = fake_schedule  # type: ignore

    rule = _FakeRule(rule_id="rule_1")
    env = _FakeEnvelope(event_id="evt_same", workspace_id="ws_1")

    task_id_1 = await client.schedule_reference_task(rule, env)
    task_id_2 = await client.schedule_reference_task(rule, env)

    # In scheduler, coalescing ensures exactly 1 task
    tasks = await scheduler.poll_due_tasks()
    assert len(tasks) == 1
    assert task_id_1 == task_id_2


@pytest.mark.asyncio
async def test_same_event_two_rules_schedule_two_distinct_runs():
    """Cùng 1 event nhưng 2 rule khác nhau -> 2 coalescing_key khác nhau, sinh 2 task riêng."""
    scheduler = RunScheduler()
    client = LocalExecutionPlaneScheduleClient(base_url="http://control-plane.internal")

    async def fake_schedule(target_spec_id, target_spec_kind, coalescing_key, input_payload):
        return await scheduler.schedule(
            target_spec_id=target_spec_id,
            target_spec_kind=target_spec_kind,
            coalescing_key=coalescing_key,
            input_payload=input_payload,
        )

    client._sched.schedule = fake_schedule  # type: ignore

    rule_1 = _FakeRule(rule_id="rule_copilot", spec=_FakeSpec(id="cosa.agents.customer_support"))
    rule_2 = _FakeRule(rule_id="rule_autopilot", spec=_FakeSpec(id="cosa.agents.customer_support_autopilot"))
    env = _FakeEnvelope(event_id="evt_shared", workspace_id="ws_1")

    task_id_1 = await client.schedule_reference_task(rule_1, env)
    task_id_2 = await client.schedule_reference_task(rule_2, env)

    assert task_id_1 != task_id_2

    tasks = await scheduler.poll_due_tasks()
    assert len(tasks) == 2
    task_keys = {t.coalescing_key for t in tasks}
    assert f"evt:ws_1:evt_shared:rule_copilot" in task_keys
    assert f"evt:ws_1:evt_shared:rule_autopilot" in task_keys


@pytest.mark.asyncio
async def test_unsupported_profile_rejected_no_side_effects():
    """Unsupported agent profile bị từ chối sạch sẽ, không fallback, không side effect."""
    scheduler = RunScheduler()
    plane = _build_plane(scheduler=scheduler)

    # Payload with unsupported profile
    raw_payload = {
        "schema_version": 1,
        "task_type": "run",
        "run_id": "run_unsupported_001",
        "workspace_id": "ws_1",
        "event_id": "evt_1",
        "trigger_rule_id": "rule_unknown",
        "agent_profile": "unsupported_profile_x",
        "agent_spec_id": "cosa.agents.unsupported",
        "agent_spec_version": "1.0.0",
        "agent_spec_hash": "hash_xyz",
        "aggregate_type": "item",
        "aggregate_id": "item_1",
        "correlation_id": "corr_1",
    }
    await scheduler.schedule(
        target_spec_id="cosa.agents.unsupported",
        input_payload=raw_payload,
    )

    tasks = await scheduler.poll_due_tasks()
    assert len(tasks) == 1
    task = tasks[0]

    with patch("apps.cosa.worker.main.execute_run_task", new_callable=AsyncMock) as mock_exec:
        await dispatch_one_task(plane, task)
        # Should NOT execute run task
        mock_exec.assert_not_called()

    # Task is completed with failure, not stuck in processing
    remaining = await scheduler.poll_due_tasks()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_legacy_envelope_adapter_and_quarantine():
    """Legacy envelope được adapt nếu đủ thông tin; thiếu workspace hoặc profile thì bị quarantine."""
    # 1. Valid legacy envelope with customer_support_autopilot
    valid_legacy = {
        "kind": "event_trigger",
        "workspace_id": "ws_legacy",
        "event_id": "evt_legacy",
        "correlation_id": "corr_legacy",
        "trigger_rule_id": "rule_leg_1",
        "agent_spec": {
            "id": "cosa.agents.customer_support_autopilot",
            "version": "1.2.0",
            "definition_hash": "hash_leg",
        },
        "aggregate_ref": {"type": "engagement.thread", "id": "th_legacy"},
        "mode": "proposal",
    }
    adapted, reason = adapt_event_task_payload(valid_legacy)
    assert reason is None
    assert adapted is not None
    assert adapted["task_type"] == "run"
    assert adapted["run_id"].startswith("run_")
    assert adapted["agent_profile"] == "customer_support_autopilot"
    assert adapted["thread_ref"] == {"thread_id": "th_legacy"}

    # 2. Missing workspace_id -> quarantined
    no_ws = dict(valid_legacy)
    del no_ws["workspace_id"]
    adapted_no_ws, reason_no_ws = adapt_event_task_payload(no_ws)
    assert adapted_no_ws is None
    assert "quarantined" in reason_no_ws

    # 3. Unmapped spec ID -> rejected
    unmapped = dict(valid_legacy)
    unmapped["agent_spec"] = {"id": "cosa.agents.alien", "version": "1.0.0", "definition_hash": "h"}
    adapted_unmapped, reason_unmapped = adapt_event_task_payload(unmapped)
    assert adapted_unmapped is None
    assert "unsupported agent profile" in reason_unmapped
