from __future__ import annotations

import httpx
import pytest

from agentos.connectors.slack.client import SlackApiError, SlackConnectorClient
from agentos.connectors.vault import InMemoryVaultStore, SecretNotFoundError
from agentos.core.approval import ApprovalService
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.policy import ExecutionMode, PermissionLevel, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.tools.clusters.notification_tools import get_notification_tools
from agentos.tools.registry import ToolRegistry


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return httpx.Response(200, json={"ok": True, "ts": "12345.67"})


@pytest.mark.asyncio
async def test_slack_client_fetches_token_from_vault_and_posts():
    vault = InMemoryVaultStore()
    vault.set_secret("slack_bot_token", "xoxb-secret-token-12345", workspace_id="ws_acme")

    transport = _MockTransport([
        httpx.Response(200, json={"ok": True, "channel": "C123", "ts": "167890.00"})
    ])
    http_client = httpx.AsyncClient(transport=transport)

    client = SlackConnectorClient(secret_store=vault, http_client=http_client)
    res = await client.post_message(channel="general", text="Hello team!", workspace_id="ws_acme")

    assert res["ok"] is True
    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert req.headers["authorization"] == "Bearer xoxb-secret-token-12345"


@pytest.mark.asyncio
async def test_slack_client_missing_secret_raises_error():
    vault = InMemoryVaultStore()
    client = SlackConnectorClient(secret_store=vault)

    with pytest.raises(SecretNotFoundError):
        await client.post_message(channel="general", text="Hi", workspace_id="unknown_ws")


@pytest.mark.asyncio
async def test_slack_client_retries_on_transient_error():
    vault = InMemoryVaultStore({"slack_bot_token": "xoxb-test"})
    # First request returns 503 Server Error, second succeeds with 200
    transport = _MockTransport([
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(200, json={"ok": True, "ts": "123"}),
    ])
    http_client = httpx.AsyncClient(transport=transport)

    client = SlackConnectorClient(
        secret_store=vault,
        http_client=http_client,
        max_retries=3,
        retry_delay_seconds=0.01,
    )
    res = await client.post_message(channel="general", text="Retried message")

    assert res["ok"] is True
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_slack_tool_gated_by_governance_in_interactive_mode():
    vault = InMemoryVaultStore({"slack_bot_token": "xoxb-test"})
    slack_client = SlackConnectorClient(secret_store=vault)

    registry = ToolRegistry()
    for tool in get_notification_tools(slack_client):
        registry.register(tool)

    class _ToolCallModel:
        async def generate(self, system_prompt: str, messages: list[dict]) -> ModelResponse:
            return ModelResponse(
                tool_call=ToolCallRequest(
                    tool_name="commercial.notification.slack_send",
                    arguments={"channel": "general", "text": "Deploying now"},
                )
            )

    audit_sink = SqliteAuditSink()
    policy_engine = PolicyEngine(audit_sink=audit_sink)
    approval_svc = ApprovalService(audit_sink=audit_sink)

    runtime = AgentRuntime(
        model_provider=_ToolCallModel(),
        tool_registry=registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
    )

    task = TaskContext(
        goal="Notify team",
        agent_key="notifier",
        workspace_id="ws1",
        role="user",
        agent_permission_level=PermissionLevel.L2_DRAFT,
        metadata={"execution_mode": ExecutionMode.INTERACTIVE},
    )

    # In interactive mode, high-risk external send tool requires human approval
    result = await runtime.run(task)
    assert result.status == AgentRunStatus.WAITING_APPROVAL
    assert result.approval_id is not None

    # Audit records do NOT contain raw secrets
    logs = audit_sink.export_run(result.run_id)
    assert len(logs) >= 1
    for log in logs:
        assert "xoxb-secret-token" not in str(log)
