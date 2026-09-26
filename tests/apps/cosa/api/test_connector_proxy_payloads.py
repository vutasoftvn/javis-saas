"""Payload proxy /agent/connectors/* phải khớp contract Encore của services/cosa.

Trước đây `/connectors/authorize` thiếu `organizationId` (bắt buộc) và
`/connectors/grant` gửi `"expiresAt": null` (Encore từ chối null cho field
optional) nên cả hai luôn 400.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from apps.cosa.api import connector_routes
from apps.cosa.api.schemas import AuthorizeConnectorRequest, GrantConnectorRequest


class _Identity:
    workspace_id = "ws_42"

    def mint_control_plane_delegation(self) -> str:
        return "delegation.token.value"


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"url": str(request.url), "json": json.loads(request.content)})
        return httpx.Response(200, json={"id": "ok"})

    real_client = httpx.AsyncClient

    def fake_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(connector_routes.httpx, "AsyncClient", fake_client)
    monkeypatch.setattr(
        connector_routes, "resolve_platform_control_plane_url", lambda: "http://cosa.test"
    )
    return calls


@pytest.mark.asyncio
async def test_authorize_sends_organization_id(captured: list[dict[str, Any]]) -> None:
    body = AuthorizeConnectorRequest(
        installation_id="inst_1",
        secret_ref="sec_1",
        granted_scopes=["read"],
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    await connector_routes.authorize_connector(None, body, _Identity())  # type: ignore[arg-type]

    assert captured[0]["url"] == "http://cosa.test/cosa/connectors/authorize"
    assert captured[0]["json"]["organizationId"] == "ws_42"


@pytest.mark.asyncio
async def test_grant_without_expiry_omits_expires_at(captured: list[dict[str, Any]]) -> None:
    body = GrantConnectorRequest(conversation_id="conv_1", authorization_id="auth_1")
    await connector_routes.grant_connector(None, body, _Identity())  # type: ignore[arg-type]

    payload = captured[0]["json"]
    assert payload["organizationId"] == "ws_42"
    assert "expiresAt" not in payload
