"""Tests cho LocalExecutionPlaneScheduleClient — test lớp REAL, không stub.

Các test này verify rằng LocalExecutionPlaneScheduleClient:
1. Wraps HttpControlPlaneSchedulerClient đúng cách
2. Builds input_payload đúng shape (reference-only, không nhân bản business payload)
3. Gọi schedule() với đúng target_spec_id, coalescing_key, và payload
4. Handles error khi scheduler không available
5. aclose() forward đúng đến wrapped client
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from apps.cosa.events.execution_plane_client import LocalExecutionPlaneScheduleClient
from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity


class _FakeEnvelope:
    """Mock envelope object với các attribute cần thiết."""

    def __init__(
        self,
        workspace_id: str = "ws_test",
        event_id: str = "evt_123",
        correlation_id: str = "corr_456",
        aggregate_type: str = "task",
        aggregate_id: str = "t_789",
    ):
        self.workspaceId = workspace_id
        self.eventId = event_id
        self.correlationId = correlation_id
        self.aggregateType = aggregate_type
        self.aggregateId = aggregate_id


def _create_rule(agent_id: str = "cosa.agents.customer_support") -> EventTriggerRule:
    """Tạo rule test với agent spec đã cho."""
    return EventTriggerRule(
        rule_id="rule_test_1",
        workspace_id="ws_test",
        event_type="operations.task.created.v1",
        agent_spec=PinnedSpecIdentity(
            id=agent_id,
            version="1.0.0",
            definition_hash="hash_abc123",
        ),
        mode="proposal",
        max_runs_per_aggregate_per_day=5,
        required_capabilities=(),
        aggregate_filter=None,
        owner="operator",
        enabled=True,
    )


def _client_with_transport(handler) -> LocalExecutionPlaneScheduleClient:
    """Tạo client với mock HTTP transport."""
    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    return LocalExecutionPlaneScheduleClient(base_url="http://control-plane.internal", client=inner)


@pytest.mark.asyncio
async def test_schedule_reference_task_success():
    """Happy path — schedule_reference_task gọi scheduler.schedule() với đúng payload."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_scheduled_001",
                "coalescingKey": "evt:ws_test:evt_123",
                "targetSpecId": "cosa.agents.customer_support",
                "targetSpecKind": "agent",
                "inputPayload": {},
                "runAt": "2026-08-25T10:00:00.000Z",
                "status": "scheduled",
                "createdAt": "2026-08-25T10:00:00.000Z",
                "attemptCount": 0,
                "maxAttempts": 5,
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule()
    env = _FakeEnvelope()

    task_id = await client.schedule_reference_task(rule, env)

    # Verify request shape
    assert captured["url"] == "http://control-plane.internal/control-plane/internal/scheduled-tasks"
    body = captured["body"]
    assert body["targetSpecId"] == "cosa.agents.customer_support"
    assert body["targetSpecKind"] == "agent"
    assert body["coalescingKey"] == "evt:ws_test:evt_123"

    # Verify input_payload has reference-only fields, not raw business payload
    payload = body["inputPayload"]
    assert payload["kind"] == "event_trigger"
    assert payload["workspace_id"] == "ws_test"
    assert payload["event_id"] == "evt_123"
    assert payload["correlation_id"] == "corr_456"
    assert payload["trigger_rule_id"] == "rule_test_1"
    assert payload["agent_spec"]["id"] == "cosa.agents.customer_support"
    assert payload["aggregate_ref"]["type"] == "task"
    assert payload["aggregate_ref"]["id"] == "t_789"
    assert payload["mode"] == "proposal"
    assert payload["agent_profile"] == "customer_support"  # mapped from spec id

    # Verify task_id returned
    assert task_id == "task_scheduled_001"


@pytest.mark.asyncio
async def test_schedule_reference_task_maps_autopilot_agent_profile():
    """agent_spec.id=cosa.agents.customer_support_autopilot → agent_profile=customer_support_autopilot."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_ap_001",
                "targetSpecId": "cosa.agents.customer_support_autopilot",
                "runAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule("cosa.agents.customer_support_autopilot")
    env = _FakeEnvelope()

    await client.schedule_reference_task(rule, env)

    payload = captured["body"]["inputPayload"]
    assert payload["agent_profile"] == "customer_support_autopilot"


@pytest.mark.asyncio
async def test_schedule_reference_task_omits_agent_profile_for_unknown_spec_id():
    """agent_spec.id không match pattern → agent_profile omitted từ payload."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_unknown_001",
                "targetSpecId": "cosa.agents.unknown_agent",
                "runAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule("cosa.agents.unknown_agent")
    env = _FakeEnvelope()

    await client.schedule_reference_task(rule, env)

    payload = captured["body"]["inputPayload"]
    assert "agent_profile" not in payload


@pytest.mark.asyncio
async def test_schedule_reference_task_includes_thread_ref_for_engagement_thread():
    """aggregate_type=engagement.thread → include thread_ref."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_thread_001",
                "targetSpecId": "cosa.agents.customer_support",
                "runAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule()
    env = _FakeEnvelope(aggregate_type="engagement.thread", aggregate_id="thread_xyz")

    await client.schedule_reference_task(rule, env)

    payload = captured["body"]["inputPayload"]
    assert payload["thread_ref"] == {"thread_id": "thread_xyz"}


@pytest.mark.asyncio
async def test_schedule_reference_task_thread_ref_alias_engagement_thread():
    """aggregate_type=engagement_thread (underscore) → include thread_ref."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_thread_002",
                "targetSpecId": "cosa.agents.customer_support",
                "runAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule()
    env = _FakeEnvelope(aggregate_type="engagement_thread", aggregate_id="thread_abc")

    await client.schedule_reference_task(rule, env)

    payload = captured["body"]["inputPayload"]
    assert payload["thread_ref"] == {"thread_id": "thread_abc"}


@pytest.mark.asyncio
async def test_schedule_reference_task_thread_ref_alias_thread():
    """aggregate_type=thread → include thread_ref."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_thread_003",
                "targetSpecId": "cosa.agents.customer_support",
                "runAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule()
    env = _FakeEnvelope(aggregate_type="thread", aggregate_id="thread_def")

    await client.schedule_reference_task(rule, env)

    payload = captured["body"]["inputPayload"]
    assert payload["thread_ref"] == {"thread_id": "thread_def"}


@pytest.mark.asyncio
async def test_schedule_reference_task_omits_thread_ref_for_other_aggregate_types():
    """aggregate_type khác → thread_ref omitted."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_other_001",
                "targetSpecId": "cosa.agents.customer_support",
                "runAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    rule = _create_rule()
    env = _FakeEnvelope(aggregate_type="engagement", aggregate_id="eng_123")

    await client.schedule_reference_task(rule, env)

    payload = captured["body"]["inputPayload"]
    assert "thread_ref" not in payload


@pytest.mark.asyncio
async def test_schedule_reference_task_connection_error():
    """Scheduler unavailable → connection error propagates."""
    client = LocalExecutionPlaneScheduleClient(
        base_url="http://127.0.0.1:59999"  # Port không có ai nghe
    )
    rule = _create_rule()
    env = _FakeEnvelope()

    with pytest.raises(httpx.ConnectError):
        await client.schedule_reference_task(rule, env)

    await client.aclose()


@pytest.mark.asyncio
async def test_schedule_reference_task_http_error():
    """Scheduler trả 5xx → error propagates."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = _client_with_transport(handler)
    rule = _create_rule()
    env = _FakeEnvelope()

    with pytest.raises(httpx.HTTPStatusError):
        await client.schedule_reference_task(rule, env)


@pytest.mark.asyncio
async def test_aclose_closes_underlying_client():
    """aclose() forward đúng đến HttpControlPlaneSchedulerClient."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "task_001"})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    client = LocalExecutionPlaneScheduleClient(base_url="http://control-plane.internal", client=inner)

    # Should be able to close without error
    await client.aclose()
