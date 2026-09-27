"""`email.digest.read` (plan hub vận hành đợt 2 B3) — chạy qua CapabilityGateway thật với grant
resolver giả + Gmail `httpx.MockTransport`. Không gọi mạng thật."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.grants import ConnectorGrant
from agent.capabilities.registry import CapabilityRegistry
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.gmail import GmailReadAdapter, GmailReauthRequiredError

from apps.cosa.capabilities.access_matrix import MATRIX, Tier
from apps.cosa.capabilities.connector_secret import (
    ConnectorSecretUnresolvableError,
    connector_secret_env_name,
    resolve_connector_secret,
    set_custom_connector_secret_resolver,
)
from apps.cosa.capabilities.email_digest_read import (
    EMAIL_DIGEST_READ_SPEC,
    EmailNotConnectedError,
    create_email_digest_read_handler,
)

SECRET_REF = "secret://cosa-connectors/ws_a/email-read"
TOKEN = "ya29.resolved-token"


@pytest.fixture(autouse=True)
def _reset_secret_resolver() -> Iterator[None]:
    set_custom_connector_secret_resolver(None)
    yield
    set_custom_connector_secret_resolver(None)


def _gmail_ok(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    if request.url.path.endswith("/users/me/messages"):
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})
    return httpx.Response(
        200,
        json={
            "id": "m1",
            "threadId": "t1",
            "snippet": "Nhắc hạn nộp báo cáo",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hạn nộp"},
                    {"name": "From", "value": "ke-toan@x.vn"},
                    {"name": "Date", "value": "Sun, 27 Sep 2026 08:00:00 +0700"},
                ]
            },
        },
    )


def _grant(**overrides) -> ConnectorGrant:
    base = {
        "grant_id": "email-read:conv_1",
        "tenant_id": "ws_a",
        "principal": "user_a",
        "connector_id": "email-read",
        "allowed_actions": ("email.digest.read",),
        "metadata": {"secret_ref": SECRET_REF},
    }
    base.update(overrides)
    return ConnectorGrant(**base)


def _gateway(gmail_handler, *, grant: ConnectorGrant | None, with_resolver: bool = True):
    registry = CapabilityRegistry()
    adapter = GmailReadAdapter(transport=httpx.MockTransport(gmail_handler))
    registry.register(EMAIL_DIGEST_READ_SPEC, create_email_digest_read_handler(adapter))
    calls: list[str] = []

    async def resolver(connector_id: str, req: GatewayExecutionRequest) -> ConnectorGrant | None:
        calls.append(connector_id)
        return grant

    gateway = CapabilityGateway(
        registry=registry,
        repository=InMemoryRunRepository(),
        connector_grant_resolver=resolver if with_resolver else None,
    )
    return gateway, calls


def _request(payload: dict | None = None, run_id: str = "run_1") -> GatewayExecutionRequest:
    return GatewayExecutionRequest(
        run_id=run_id,
        capability_id="email.digest.read",
        input_payload=payload if payload is not None else {"max_results": 5},
        workspace_id="ws_a",
        principal="user_a",
    )


def test_spec_is_t0_read_bound_to_email_connector() -> None:
    spec = EMAIL_DIGEST_READ_SPEC
    assert spec.risk == CapabilityRisk.LOW
    assert spec.approval_policy == ApprovalPolicy.NEVER
    assert spec.connector_requirements == {"connector_id": "email-read"}
    assert spec.input_schema == {
        "type": "object",
        "additionalProperties": False,
        "properties": {"max_results": {"type": "integer", "minimum": 1, "maximum": 50}},
    }
    entry = MATRIX["email.digest.read"]
    assert entry.tier is Tier.T0_READ
    assert entry.company_agent_cap is None


@pytest.mark.asyncio
async def test_reads_unread_summaries_with_token_from_grant_secret_ref() -> None:
    seen_refs: list[str] = []

    def resolve(ref: str) -> str:
        seen_refs.append(ref)
        return TOKEN

    set_custom_connector_secret_resolver(resolve)
    gateway, calls = _gateway(_gmail_ok, grant=_grant())

    res = await gateway.execute(_request())

    assert res.status == "completed", res.error_message
    assert calls == ["email-read"]  # gateway re-verify grant ở lần execute này
    assert seen_refs == [SECRET_REF]  # token lấy từ secret_ref của đúng grant đó
    assert res.output_payload == {
        "emails": [
            {
                "id": "m1",
                "thread_id": "t1",
                "subject": "Hạn nộp",
                "sender": "ke-toan@x.vn",
                "date": "Sun, 27 Sep 2026 08:00:00 +0700",
                "snippet": "Nhắc hạn nộp báo cáo",
            }
        ],
        "count": 1,
    }


@pytest.mark.asyncio
async def test_no_grant_is_denied_before_handler() -> None:
    hits: list[httpx.Request] = []

    def gmail(request: httpx.Request) -> httpx.Response:
        hits.append(request)
        return httpx.Response(200, json={})

    set_custom_connector_secret_resolver(lambda ref: TOKEN)
    gateway, _ = _gateway(gmail, grant=None)
    res = await gateway.execute(_request())

    assert res.status == "denied"
    assert "No grant found for connector" in (res.error_message or "")
    assert hits == []


@pytest.mark.asyncio
async def test_handler_without_verified_grant_fails_clearly_not_empty() -> None:
    set_custom_connector_secret_resolver(lambda ref: TOKEN)
    gateway, _ = _gateway(_gmail_ok, grant=None, with_resolver=False)
    res = await gateway.execute(_request())

    assert res.status == "failed"
    assert isinstance(res.failure, EmailNotConnectedError)
    assert (res.error_message or "").startswith("email_not_connected:")
    assert res.output_payload is None


@pytest.mark.asyncio
async def test_expired_token_surfaces_reauth_error_type() -> None:
    set_custom_connector_secret_resolver(lambda ref: "expired")
    gateway, _ = _gateway(lambda request: httpx.Response(401), grant=_grant())
    res = await gateway.execute(_request())

    assert res.status == "failed"
    assert isinstance(res.failure, GmailReauthRequiredError)
    assert (res.error_message or "").startswith("email_reauth_required:")
    assert "expired" not in (res.error_message or "")


@pytest.mark.asyncio
async def test_unresolvable_secret_errors_without_leaking_secret_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(connector_secret_env_name(SECRET_REF), raising=False)
    gateway, _ = _gateway(_gmail_ok, grant=_grant())
    res = await gateway.execute(_request())

    assert res.status == "failed"
    assert isinstance(res.failure, ConnectorSecretUnresolvableError)
    assert SECRET_REF not in (res.error_message or "")
    assert "ws_a/email-read" not in (res.error_message or "")


@pytest.mark.asyncio
async def test_grant_without_secret_ref_fails_clearly() -> None:
    gateway, _ = _gateway(_gmail_ok, grant=_grant(metadata={"secret_ref": ""}))
    res = await gateway.execute(_request())
    assert res.status == "failed"
    assert isinstance(res.failure, ConnectorSecretUnresolvableError)


@pytest.mark.asyncio
async def test_extra_argument_rejected_without_calling_gmail() -> None:
    hits: list[httpx.Request] = []

    def gmail(request: httpx.Request) -> httpx.Response:
        hits.append(request)
        return _gmail_ok(request)

    set_custom_connector_secret_resolver(lambda ref: TOKEN)
    gateway, _ = _gateway(gmail, grant=_grant())
    res = await gateway.execute(_request({"max_results": 5, "query": "from:boss"}))
    assert res.status == "failed"
    # Validator của registry không áp additionalProperties ⇒ handler tự từ chối, không lọc im lặng.
    assert isinstance(res.failure, ValueError)
    assert "query" in (res.error_message or "")
    assert hits == []


@pytest.mark.asyncio
async def test_env_resolution_for_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    assert connector_secret_env_name(SECRET_REF) == "COSA_CONNECTOR_SECRET_WS_A_EMAIL_READ"
    monkeypatch.setenv("COSA_CONNECTOR_SECRET_WS_A_EMAIL_READ", "env-token")
    assert await resolve_connector_secret(SECRET_REF) == "env-token"


@pytest.mark.asyncio
async def test_custom_async_resolver_returning_none_falls_back_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolver(ref: str) -> str | None:
        return None

    set_custom_connector_secret_resolver(resolver)
    monkeypatch.setenv(connector_secret_env_name(SECRET_REF), "env-token")
    assert await resolve_connector_secret(SECRET_REF) == "env-token"
