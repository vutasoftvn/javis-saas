from __future__ import annotations

import httpx
import pytest

from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.commercial_customer_read import (
    COMMERCIAL_CUSTOMER_360_READ_SPEC,
    create_commercial_customer_360_read_handler,
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


def test_customer_360_read_spec_properties():
    assert COMMERCIAL_CUSTOMER_360_READ_SPEC.id == "commercial.customer_360.read"
    assert COMMERCIAL_CUSTOMER_360_READ_SPEC.risk == CapabilityRisk.LOW
    assert COMMERCIAL_CUSTOMER_360_READ_SPEC.approval_policy == ApprovalPolicy.NEVER


@pytest.mark.asyncio
async def test_customer_360_read_with_identity_verified_true():
    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.url.path == "/commercial/engagement/customer360/c_123":
            return httpx.Response(
                200,
                json={
                    "contact": {"id": "c_123", "name": "Bob"},
                    "account": {"id": "a_1", "name": "BobCo"},
                    "invoices": [{"id": "inv_1", "amount": 500}],
                    "subscriptions": [{"id": "sub_1", "plan": "pro"}],
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    client = _make_mock_client(mock_handler)
    handler = create_commercial_customer_360_read_handler(client)

    result = await handler(
        {"contact_id": "c_123", "identity_verified": True},
        {"workspace_id": "ws_test"},
    )

    assert len(captured_requests) == 1
    assert captured_requests[0].method == "GET"
    assert "c_123" in captured_requests[0].url.path
    assert captured_requests[0].url.params.get("identityVerified") == "true"
    assert captured_requests[0].headers.get("X-Workspace-Id") == "ws_test"
    assert "invoices" in result


@pytest.mark.asyncio
async def test_customer_360_read_with_identity_verified_false():
    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "contact": {"id": "c_123", "name": "Bob"},
                "account": {"id": "a_1", "name": "BobCo"},
            },
        )

    client = _make_mock_client(mock_handler)
    handler = create_commercial_customer_360_read_handler(client)

    result = await handler(
        {"contact_id": "c_123", "identity_verified": False},
        {"workspace_id": "ws_test"},
    )

    assert captured_requests[0].url.params.get("identityVerified") == "false"
    assert "invoices" not in result


@pytest.mark.asyncio
async def test_customer_360_read_missing_contact_id():
    client = _make_mock_client(lambda req: httpx.Response(200, json={}))
    handler = create_commercial_customer_360_read_handler(client)

    with pytest.raises(ValueError, match="thiếu contact_id"):
        await handler({}, {"workspace_id": "ws_test"})


@pytest.mark.asyncio
async def test_customer_360_read_missing_workspace_id():
    client = _make_mock_client(lambda req: httpx.Response(200, json={}))
    handler = create_commercial_customer_360_read_handler(client)

    with pytest.raises(ValueError, match="thiếu workspace_id"):
        await handler({"contact_id": "c_123"}, {})
