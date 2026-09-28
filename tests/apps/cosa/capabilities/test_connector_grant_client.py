"""`ConnectorGrantHttpClient` THẬT + resolver production (`build_connector_grant_resolver`) chạy qua
CapabilityGateway — review Task 4 (B3): principal, lý do từ chối của control plane, requiredScope.
Transport giả (`httpx.MockTransport`), không gọi mạng thật."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx
import pytest
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.grants import ConnectorGrantDeniedError
from agent.capabilities.registry import CapabilityRegistry
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.gmail import GmailReadAdapter

from apps.cosa.capabilities.connector_grant_client import (
    ConnectorGrantHttpClient,
    build_connector_grant_resolver,
)
from apps.cosa.capabilities.connector_secret import set_custom_connector_secret_resolver
from apps.cosa.capabilities.email_digest_read import (
    EMAIL_DIGEST_READ_SPEC,
    create_email_digest_read_handler,
)

SECRET_REF = "secret://cosa-connectors/ws_1/email-read"


@pytest.fixture(autouse=True)
def _secret() -> Iterator[None]:
    set_custom_connector_secret_resolver(lambda ref: "ya29.token")
    yield
    set_custom_connector_secret_resolver(None)


def _gmail(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/users/me/messages"):
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})
    return httpx.Response(
        200,
        json={
            "id": "m1",
            "threadId": "t1",
            "snippet": "hi",
            "payload": {"headers": [{"name": "Subject", "value": "S"}]},
        },
    )


def _setup(control_plane_response: httpx.Response):
    assert_calls: list[dict] = []

    def control_plane(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cosa/connectors/assert"
        assert request.headers["Authorization"] == "Bearer worker-token"
        assert_calls.append(json.loads(request.content))
        return control_plane_response

    client = ConnectorGrantHttpClient(
        base_url="http://control-plane.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(control_plane),
    )
    registry = CapabilityRegistry()
    registry.register(
        EMAIL_DIGEST_READ_SPEC,
        create_email_digest_read_handler(GmailReadAdapter(transport=httpx.MockTransport(_gmail))),
    )
    gateway = CapabilityGateway(
        registry=registry,
        repository=InMemoryRunRepository(),
        connector_grant_resolver=build_connector_grant_resolver(client, registry),
    )
    return gateway, assert_calls


def _request(principal: str = "user:1") -> GatewayExecutionRequest:
    return GatewayExecutionRequest(
        run_id="run_1",
        capability_id="email.digest.read",
        input_payload={"max_results": 3},
        workspace_id="ws_1",
        principal=principal,
        context={"conversation_id": "conv_1"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("principal", ["user:1", "system:copilot", "service:scheduler"])
async def test_real_client_grant_passes_gateway_for_real_run_principals(principal: str) -> None:
    gateway, calls = _setup(httpx.Response(200, json={"ok": True, "secretRef": SECRET_REF}))

    res = await gateway.execute(_request(principal))

    assert res.status == "completed", res.error_message
    assert res.output_payload["count"] == 1
    # requiredScope lấy từ spec (mail:read) được gửi tới control plane.
    assert calls == [
        {
            "organizationId": "ws_1",
            "conversationId": "conv_1",
            "connectorKey": "email-read",
            "action": "email.digest.read",
            "requiredScope": "mail:read",
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    [
        "connector_reauth_required",
        "connector_not_granted_to_session",
        "connector_installation_disabled",
        "connector_scope_missing",
        "connector_action_not_allowed",
    ],
)
async def test_control_plane_deny_reason_reaches_gateway_result(code: str) -> None:
    gateway, _ = _setup(httpx.Response(200, json={"ok": False, "error": code}))

    res = await gateway.execute(_request())

    assert res.status == "denied"
    assert isinstance(res.failure, ConnectorGrantDeniedError)
    assert res.failure.code == code
    assert res.error_message == f"Execution of 'email.digest.read' denied: {code}"
    events = await gateway._repo.list_events("run_1")
    denied = [e for e in events if e.event_type == "connector_grant.denied"]
    assert denied and denied[-1].payload["reason"] == code


@pytest.mark.asyncio
async def test_control_plane_deny_without_code_uses_generic_code() -> None:
    gateway, _ = _setup(httpx.Response(200, json={"ok": False}))
    res = await gateway.execute(_request())
    assert res.status == "denied"
    assert res.failure.code == "connector_grant_denied"


@pytest.mark.asyncio
async def test_control_plane_http_error_is_fail_closed_resolver_error() -> None:
    gateway, _ = _setup(httpx.Response(503, text="down"))
    res = await gateway.execute(_request())
    assert res.status == "denied"
    assert not isinstance(res.failure, ConnectorGrantDeniedError)
    events = await gateway._repo.list_events("run_1")
    assert any(e.event_type == "connector_grant.resolver_error" for e in events)


@pytest.mark.asyncio
async def test_client_omits_required_scope_when_not_given() -> None:
    bodies: list[dict] = []

    def cp(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "secretRef": SECRET_REF})

    client = ConnectorGrantHttpClient(
        base_url="http://cp.test",
        worker_token_provider=lambda: "t",
        transport=httpx.MockTransport(cp),
    )
    grant = await client.assert_usable(
        "sandbox-read", workspace_id="ws_1", conversation_id="c", action="mcp.sandbox-read.x"
    )
    assert "requiredScope" not in bodies[0]
    assert grant is not None
    assert grant.principal == "*"
    assert grant.tenant_id == "ws_1"
    assert grant.allowed_actions == ("mcp.sandbox-read.x",)
    assert grant.metadata == {"secret_ref": SECRET_REF}


# B5 (Task 6b) — assert_usable_for_execution: preflight connector cho lịch nền
# uỷ quyền trước, TRƯỚC khi tạo conversation/model. Không raise khi ok:false —
# trả nguyên dict để caller (scheduled_tasks.py) tự map mã lỗi.


@pytest.mark.asyncio
async def test_assert_usable_for_execution_sends_execution_id_not_conversation_id() -> None:
    bodies: list[dict] = []

    def cp(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cosa/connectors/assert"
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "secretRef": SECRET_REF})

    client = ConnectorGrantHttpClient(
        base_url="http://cp.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(cp),
    )
    res = await client.assert_usable_for_execution(
        "email-read",
        workspace_id="ws_1",
        execution_id="exec_1",
        action="email.digest.read",
        required_scope="mail:read",
    )
    assert bodies[0]["executionId"] == "exec_1"
    assert "conversationId" not in bodies[0]
    assert bodies[0]["requiredScope"] == "mail:read"
    assert res == {"ok": True, "secretRef": SECRET_REF, "error": None}


@pytest.mark.asyncio
async def test_assert_usable_for_execution_does_not_raise_on_ok_false() -> None:
    def cp(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "connector_reauth_required"})

    client = ConnectorGrantHttpClient(
        base_url="http://cp.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(cp),
    )
    res = await client.assert_usable_for_execution(
        "email-read", workspace_id="ws_1", execution_id="exec_1", action="email.digest.read"
    )
    assert res == {"ok": False, "secretRef": None, "error": "connector_reauth_required"}


@pytest.mark.asyncio
async def test_assert_usable_for_execution_raises_on_http_error() -> None:
    def cp(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    client = ConnectorGrantHttpClient(
        base_url="http://cp.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(cp),
    )
    with pytest.raises(RuntimeError):
        await client.assert_usable_for_execution(
            "email-read", workspace_id="ws_1", execution_id="exec_1", action="email.digest.read"
        )


# B5 (Task 6b, fix review "Important #2") — build_connector_grant_resolver PHẢI đi đường
# executionId (không phải conversationId) khi context của run mang schedule_execution_id (lịch
# nền uỷ quyền trước). Trước fix: resolver LUÔN gọi assert_usable(conversation_id=...) bất kể
# nguồn gốc run -> email.digest.read giữa lúc chạy lịch nền uỷ quyền trước LUÔN bị DENY (100%),
# vì mỗi execution tạo 1 conversation MỚI, không bao giờ có session grant. Test này chạy qua
# CapabilityGateway thật (như test_real_client_grant_passes_gateway_for_real_run_principals ở
# trên) để khoá đúng hành vi end-to-end, không chỉ đơn vị hàm resolver.


def _scheduled_request(execution_id: str = "exec_sched_1") -> GatewayExecutionRequest:
    return GatewayExecutionRequest(
        run_id="run_sched_1",
        capability_id="email.digest.read",
        input_payload={"max_results": 3},
        workspace_id="ws_1",
        principal="user:founder_1",
        # `conversation_id` cũng có mặt (như run lịch thật luôn có, xem
        # execute_scheduled_session_task) — khẳng định resolver ưu tiên
        # executionId khi có, không lẫn lộn cả hai.
        context={"conversation_id": "conv_sched_abcd1234", "schedule_execution_id": execution_id},
    )


@pytest.mark.asyncio
async def test_resolver_uses_execution_id_not_conversation_id_for_scheduled_run() -> None:
    assert_calls: list[dict] = []

    def control_plane(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cosa/connectors/assert"
        assert_calls.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "secretRef": SECRET_REF})

    client = ConnectorGrantHttpClient(
        base_url="http://control-plane.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(control_plane),
    )
    registry = CapabilityRegistry()
    registry.register(
        EMAIL_DIGEST_READ_SPEC,
        create_email_digest_read_handler(GmailReadAdapter(transport=httpx.MockTransport(_gmail))),
    )
    gateway = CapabilityGateway(
        registry=registry,
        repository=InMemoryRunRepository(),
        connector_grant_resolver=build_connector_grant_resolver(client, registry),
    )

    res = await gateway.execute(_scheduled_request())

    assert res.status == "completed", res.error_message
    assert res.output_payload["count"] == 1
    assert assert_calls == [
        {
            "organizationId": "ws_1",
            "executionId": "exec_sched_1",
            "connectorKey": "email-read",
            "action": "email.digest.read",
            "requiredScope": "mail:read",
        }
    ]
    # Khẳng định KHÔNG có field conversationId nào lọt vào body gửi control plane.
    assert "conversationId" not in assert_calls[0]


@pytest.mark.asyncio
async def test_resolver_denies_scheduled_run_when_execution_snapshot_grant_invalid() -> None:
    def control_plane(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["executionId"] == "exec_sched_1"
        return httpx.Response(200, json={"ok": False, "error": "connector_reauth_required"})

    client = ConnectorGrantHttpClient(
        base_url="http://control-plane.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(control_plane),
    )
    registry = CapabilityRegistry()
    registry.register(
        EMAIL_DIGEST_READ_SPEC,
        create_email_digest_read_handler(GmailReadAdapter(transport=httpx.MockTransport(_gmail))),
    )
    gateway = CapabilityGateway(
        registry=registry,
        repository=InMemoryRunRepository(),
        connector_grant_resolver=build_connector_grant_resolver(client, registry),
    )

    res = await gateway.execute(_scheduled_request())

    assert res.status == "denied"
    assert isinstance(res.failure, ConnectorGrantDeniedError)
    assert res.failure.code == "connector_reauth_required"


@pytest.mark.asyncio
async def test_resolver_still_uses_conversation_id_when_no_schedule_execution_id() -> None:
    """Chat/API thường (không có schedule_execution_id trong context) giữ nguyên đường cũ —
    không regress hành vi conversation-grant hiện có."""
    assert_calls: list[dict] = []

    def control_plane(request: httpx.Request) -> httpx.Response:
        assert_calls.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "secretRef": SECRET_REF})

    client = ConnectorGrantHttpClient(
        base_url="http://control-plane.test",
        worker_token_provider=lambda: "worker-token",
        transport=httpx.MockTransport(control_plane),
    )
    registry = CapabilityRegistry()
    registry.register(
        EMAIL_DIGEST_READ_SPEC,
        create_email_digest_read_handler(GmailReadAdapter(transport=httpx.MockTransport(_gmail))),
    )
    gateway = CapabilityGateway(
        registry=registry,
        repository=InMemoryRunRepository(),
        connector_grant_resolver=build_connector_grant_resolver(client, registry),
    )

    res = await gateway.execute(
        _request()
    )  # context chỉ có conversation_id, không có schedule_execution_id

    assert res.status == "completed", res.error_message
    assert assert_calls == [
        {
            "organizationId": "ws_1",
            "conversationId": "conv_1",
            "connectorKey": "email-read",
            "action": "email.digest.read",
            "requiredScope": "mail:read",
        }
    ]
