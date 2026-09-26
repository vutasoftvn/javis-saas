from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from apps.cosa.capabilities.client import CompanyServiceClient
from tests.apps.cosa.api.test_graphql_routes import test_app
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


def asgi_client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.asyncio
async def test_member_cannot_read_workspace_authority_overview(test_app):
    app, _ = test_app
    override_authenticated_identity(app, workspace_id="ws-a", role_id="member")
    async with asgi_client(app) as client:
        response = await client.post(
            "/agent/graphql",
            json={
                "operationId": "workspaceAuthorityOverview",
                "variables": {},
            },
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_founder_reads_workspace_authority_overview(test_app):
    app, plane = test_app
    override_authenticated_identity(app, workspace_id="ws-a", role_id="founder")

    plane.company_client.get = AsyncMock(
        return_value={
            "roles": [{"roleKey": "founder", "name": "Founder"}],
            "assignments": [],
            "grants": [],
            "bindings": [],
            "events": [],
            "members": [{"id": "1", "memberType": "HUMAN"}],
        }
    )

    async with asgi_client(app) as client:
        response = await client.post(
            "/agent/graphql",
            json={
                "operationId": "workspaceAuthorityOverview",
                "variables": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    overview = data["data"]["workspaceAuthorityOverview"]
    assert "roles" in overview
    assert len(overview["roles"]) == 1



@pytest.mark.asyncio
async def test_workspace_authority_overview_rejects_unknown_variables(test_app):
    app, _ = test_app
    override_authenticated_identity(app, workspace_id="ws-a", role_id="founder")
    async with asgi_client(app) as client:
        response = await client.post(
            "/agent/graphql",
            json={
                "operationId": "workspaceAuthorityOverview",
                "variables": {"workspaceId": "ws-other"},
            },
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_workspace_authority_overview_forwards_caller_bearer(test_app):
    """Company `/identity/authorization/overview` bắt buộc bearer — thiếu nó
    Company trả 401 và màn Cài đặt hiện "GraphQL request failed: 500"."""
    app, plane = test_app
    override_authenticated_identity(app, workspace_id="ws-a", role_id="founder")
    plane.company_client.get = AsyncMock(return_value={"roles": [], "members": []})

    async with asgi_client(app) as client:
        response = await client.post(
            "/agent/graphql",
            json={"operationId": "workspaceAuthorityOverview", "variables": {}},
        )

    assert response.status_code == 200
    headers = plane.company_client.get.await_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-bearer-token"
    assert headers["X-Workspace-Id"] == "ws-a"


@pytest.mark.asyncio
@pytest.mark.parametrize(("upstream", "expected"), [(401, 401), (403, 403), (500, 502)])
async def test_workspace_authority_overview_maps_company_errors(test_app, upstream, expected):
    from apps.cosa.capabilities.client import CompanyServiceError

    app, plane = test_app
    override_authenticated_identity(app, workspace_id="ws-a", role_id="founder")
    plane.company_client.get = AsyncMock(
        side_effect=CompanyServiceError("boom", status_code=upstream)
    )

    async with asgi_client(app) as client:
        response = await client.post(
            "/agent/graphql",
            json={"operationId": "workspaceAuthorityOverview", "variables": {}},
        )

    assert response.status_code == expected
