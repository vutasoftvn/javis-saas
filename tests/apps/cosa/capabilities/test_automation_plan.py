"""Capability `automation.plan.propose` (plan hub vận hành đợt 2 B4).

Handler tự kiểm connector với control plane (grant client giả), rồi POST nháp kế hoạch lên company
với body camelCase CHỈ gồm field cho phép; project_id lấy từ context run, không từ model.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.capabilities.grants import ConnectorGrantDeniedError

from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES, MATRIX, Tier
from apps.cosa.capabilities.automation_plan import (
    AUTOMATION_PLAN_PROPOSE_SPEC,
    OUTPUT_KIND,
    create_automation_plan_propose_handler,
)
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient

PATH = "/operations/projects/42/automation-plans/proposals"
CTX = {
    "workspace_id": "ws-1",
    "project_id": "42",
    "conversation_id": "conv-1",
    "run_id": "run-7",
}
COMPANY_DATA = {
    "proposalId": "9001",
    "projectId": "42",
    "status": "DRAFT",
    "plan": {"skillId": "operations.email-digest"},
    "readiness": {"ready": True, "blockers": []},
    "createdAt": "2026-09-28T00:00:00.000Z",
    "decidedAt": None,
    "approvedScheduleId": None,
}


def _payload(**overrides):
    payload = {
        "skill_id": "operations.email-digest",
        "connector_keys": ["email-read"],
        "channel_kind": "telegram",
        "schedule": {"kind": "daily", "hour": 7, "minute": 30, "timezone": "Asia/Ho_Chi_Minh"},
        "token_budget_per_run": 20000,
    }
    payload.update(overrides)
    return payload


def _clients(grant_error: Exception | None = None):
    client = AsyncMock()
    client.post.return_value = {"data": COMPANY_DATA, "meta": {"dataState": "populated"}}
    grants = AsyncMock(spec=ConnectorGrantHttpClient)
    if grant_error is not None:
        grants.assert_usable.side_effect = grant_error
    return client, grants


def test_spec_is_t1_draft_with_company_cap_and_no_secret_fields() -> None:
    entry = MATRIX["automation.plan.propose"]
    assert entry.tier is Tier.T1_DRAFT
    assert entry.company_agent_cap == "automation.plan.propose"
    assert "automation.plan.propose" not in CHAT_T2_CAPABILITIES

    schema = AUTOMATION_PLAN_PROPOSE_SPEC.input_schema
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schedule"]["additionalProperties"] is False
    props = set(schema["properties"]) | set(schema["properties"]["schedule"]["properties"])
    forbidden = {"chat_id", "secret_ref", "token", "recipient", "connector_status", "project_id"}
    assert not props & forbidden


@pytest.mark.asyncio
async def test_connected_connector_posts_camelcase_body_only_allowed_fields() -> None:
    client, grants = _clients()
    out = await create_automation_plan_propose_handler(client, grants)(_payload(), CTX)

    grants.assert_usable.assert_awaited_once_with(
        "email-read",
        workspace_id="ws-1",
        conversation_id="conv-1",
        action="email.digest.read",
        required_scope="mail:read",
    )
    client.post.assert_awaited_once()
    assert client.post.await_args.args == (PATH,)
    assert client.post.await_args.kwargs == {
        "json": {
            "skillId": "operations.email-digest",
            "connectorKeys": ["email-read"],
            "connectorStatus": {"email-read": "connected"},
            "schedule": {
                "kind": "daily",
                "timezone": "Asia/Ho_Chi_Minh",
                "hour": 7,
                "minute": 30,
            },
            "tokenBudgetPerRun": 20000,
            "channelKind": "telegram",
        },
        "headers": {"X-Workspace-Id": "ws-1", "X-COSA-Run-Id": "run-7"},
    }
    assert out == {"kind": OUTPUT_KIND, **COMPANY_DATA}


@pytest.mark.asyncio
async def test_denied_grant_reports_missing_connector() -> None:
    client, grants = _clients(ConnectorGrantDeniedError("connector_not_granted_to_session"))
    await create_automation_plan_propose_handler(client, grants)(
        _payload(agent_deployment_id="555", propose_new_agent=False), CTX
    )
    body = client.post.await_args.kwargs["json"]
    assert body["connectorStatus"] == {"email-read": "missing"}
    assert body["agentDeploymentId"] == "555"
    assert "proposeNewAgent" not in body


@pytest.mark.asyncio
async def test_connector_checked_even_when_model_omits_it_and_new_agent_flag_forwarded() -> None:
    client, grants = _clients()
    await create_automation_plan_propose_handler(client, grants)(
        _payload(connector_keys=[], propose_new_agent=True), CTX
    )
    grants.assert_usable.assert_awaited_once()
    body = client.post.await_args.kwargs["json"]
    assert body["connectorStatus"] == {"email-read": "connected"}
    assert body["proposeNewAgent"] is True


@pytest.mark.asyncio
async def test_no_conversation_means_missing_without_calling_control_plane() -> None:
    client, grants = _clients()
    ctx = {"workspace_id": "ws-1", "project_id": "42"}
    await create_automation_plan_propose_handler(client, grants)(_payload(), ctx)
    grants.assert_usable.assert_not_awaited()
    assert client.post.await_args.kwargs["json"]["connectorStatus"] == {"email-read": "missing"}
    assert client.post.await_args.kwargs["headers"] == {"X-Workspace-Id": "ws-1"}


@pytest.mark.asyncio
async def test_invocation_context_object_with_metadata_is_supported() -> None:
    client, grants = _clients()
    ctx = SimpleNamespace(
        workspace_id="ws-1",
        conversation_id="conv-9",
        run_id="run-9",
        metadata={"project_id": "42"},
    )
    await create_automation_plan_propose_handler(client, grants)(
        _payload(
            schedule={"kind": "one_time", "run_at": "2026-10-01T00:30:00Z", "timezone": "UTC"}
        ),
        ctx,
    )
    assert grants.assert_usable.await_args.kwargs["conversation_id"] == "conv-9"
    assert client.post.await_args.args == (PATH,)
    assert client.post.await_args.kwargs["json"]["schedule"] == {
        "kind": "one_time",
        "timezone": "UTC",
        "runAt": "2026-10-01T00:30:00Z",
    }


@pytest.mark.asyncio
async def test_control_plane_infra_error_propagates() -> None:
    client, grants = _clients(RuntimeError("connector assert failed: HTTP 502"))
    with pytest.raises(RuntimeError):
        await create_automation_plan_propose_handler(client, grants)(_payload(), CTX)
    client.post.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [
        _payload(chat_id="123"),
        _payload(connector_status={"email-read": "connected"}),
        _payload(project_id="999"),
        _payload(secret_ref="secret://x"),
        _payload(skill_id="operations.payout"),
        _payload(connector_keys=["slack"]),
        _payload(channel_kind="sms"),
        _payload(token_budget_per_run=0),
        _payload(token_budget_per_run=200001),
        _payload(token_budget_per_run=True),
        _payload(schedule={"kind": "daily", "hour": 7, "timezone": "UTC", "chat_id": "1"}),
        _payload(schedule={"kind": "hourly", "timezone": "UTC"}),
        _payload(schedule={"kind": "daily", "hour": 7}),
        _payload(propose_new_agent="yes"),
    ],
)
@pytest.mark.asyncio
async def test_rejects_unknown_or_invalid_args_without_calling_anything(payload) -> None:
    client, grants = _clients()
    with pytest.raises(ValueError):
        await create_automation_plan_propose_handler(client, grants)(payload, CTX)
    client.post.assert_not_awaited()
    grants.assert_usable.assert_not_awaited()


@pytest.mark.parametrize(
    "ctx",
    [
        {"project_id": "42"},
        {"workspace_id": "ws-1"},
        {"workspace_id": "ws-1", "project_id": "../identity"},
    ],
)
@pytest.mark.asyncio
async def test_requires_workspace_and_numeric_project_from_context(ctx) -> None:
    client, grants = _clients()
    with pytest.raises(ValueError):
        await create_automation_plan_propose_handler(client, grants)(_payload(), ctx)
    client.post.assert_not_awaited()
