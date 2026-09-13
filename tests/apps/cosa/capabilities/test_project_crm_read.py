from __future__ import annotations

import httpx
import pytest

from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.project_crm_read import (
    PROJECT_CRM_READ_SPEC,
    create_project_crm_read_handler,
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


def test_project_crm_read_spec_properties():
    assert PROJECT_CRM_READ_SPEC.id == "project.crm.read"
    assert PROJECT_CRM_READ_SPEC.risk == CapabilityRisk.LOW
    assert PROJECT_CRM_READ_SPEC.approval_policy == ApprovalPolicy.NEVER


@pytest.mark.asyncio
async def test_project_crm_read_success():
    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.url.path == "/commercial/projects/1001/crm/leads":
            return httpx.Response(
                200,
                json={
                    "leads": [
                        {"id": "lead_1", "name": "Acme Lead", "stage": "NEW"},
                    ],
                },
            )
        if request.url.path == "/commercial/projects/1001/crm/schema":
            return httpx.Response(
                200,
                json={
                    "customFields": [
                        {"id": "def_1", "stableKey": "budget", "label": "Budget"},
                    ],
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    client = _make_mock_client(mock_handler)
    handler = create_project_crm_read_handler(client)

    result = await handler(
        {"project_id": "1001", "workspace_id": "ws_1"},
        {"workspace_id": "ws_1"},
    )

    assert result["projectId"] == "1001"
    assert len(result["leads"]) == 1
    assert result["leads"][0]["id"] == "lead_1"
    assert len(result["fieldDefinitions"]) == 1
    assert result["fieldDefinitions"][0]["stableKey"] == "budget"

    # Verify requests sent to company service
    assert len(captured_requests) == 2
    assert captured_requests[0].headers["x-workspace-id"] == "ws_1"
    assert captured_requests[1].headers["x-workspace-id"] == "ws_1"


@pytest.mark.asyncio
async def test_project_crm_read_missing_project_id_raises():
    client = _make_mock_client(lambda req: httpx.Response(200, json={}))
    handler = create_project_crm_read_handler(client)

    with pytest.raises(ValueError, match="thiếu project_id"):
        await handler({"workspace_id": "ws_1"}, {"workspace_id": "ws_1"})
