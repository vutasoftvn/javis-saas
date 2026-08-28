from __future__ import annotations

import json
from typing import Any
import httpx
import pytest

from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.engagement_read import (
    ENGAGEMENT_THREAD_READ_SPEC,
    create_engagement_thread_read_handler,
)


def _make_mock_client(handler_fn) -> CompanyServiceClient:
    transport = httpx.MockTransport(handler_fn)
    client = CompanyServiceClient(base_url="http://mock-company-service")

    async def _mock_request(
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        url = f"{client.base_url}/{path.lstrip('/')}"
        req_headers = dict(client.default_headers)
        if headers:
            req_headers.update(headers)
        async with httpx.AsyncClient(transport=transport) as hc:
            resp = await hc.request(method, url, params=params, json=json, headers=req_headers)
            return resp.json()

    client._request = _mock_request
    return client


def test_engagement_thread_read_spec_properties():
    assert ENGAGEMENT_THREAD_READ_SPEC.id == "engagement.thread.read"
    assert ENGAGEMENT_THREAD_READ_SPEC.risk == CapabilityRisk.LOW
    assert ENGAGEMENT_THREAD_READ_SPEC.approval_policy == ApprovalPolicy.NEVER


@pytest.mark.asyncio
async def test_engagement_thread_read_success():
    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.url.path == "/commercial/engagement/threads/t_123/context":
            return httpx.Response(
                200,
                json={
                    "thread": {"id": "t_123", "status": "open", "priority": "urgent"},
                    "contactId": "c_456",
                    "identityVerified": True,
                    "messages": [{"id": "m_1", "body": "Help me", "visibility": "public"}],
                    "assignment": None,
                    "labels": [],
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    client = _make_mock_client(mock_handler)
    handler = create_engagement_thread_read_handler(client)

    result = await handler({"thread_id": "t_123"}, {"workspace_id": "ws_test"})

    assert len(captured_requests) == 1
    assert captured_requests[0].method == "GET"
    assert captured_requests[0].url.path == "/commercial/engagement/threads/t_123/context"
    assert captured_requests[0].headers.get("X-Workspace-Id") == "ws_test"
    assert result["thread"]["id"] == "t_123"
    assert result["identityVerified"] is True
    assert len(result["messages"]) == 1


@pytest.mark.asyncio
async def test_engagement_thread_read_missing_thread_id():
    client = _make_mock_client(lambda req: httpx.Response(200, json={}))
    handler = create_engagement_thread_read_handler(client)

    with pytest.raises(ValueError, match="thiếu thread_id"):
        await handler({}, {"workspace_id": "ws_test"})


@pytest.mark.asyncio
async def test_engagement_thread_read_missing_workspace_id():
    client = _make_mock_client(lambda req: httpx.Response(200, json={}))
    handler = create_engagement_thread_read_handler(client)

    with pytest.raises(ValueError, match="thiếu workspace_id"):
        await handler({"thread_id": "t_123"}, {})
