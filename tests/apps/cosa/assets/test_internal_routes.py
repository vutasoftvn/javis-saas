import pytest
from httpx import ASGITransport, AsyncClient

from apps.cosa.api.app import create_cosa_app


@pytest.mark.asyncio
async def test_internal_routes_requires_service_token():
    app = create_cosa_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/agent/internal/founder-assets/commands",
            json={"workspace_id": "ws-1", "operation": "CLONE"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_internal_routes_processes_valid_command():
    app = create_cosa_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {
            "X-Service-Token": "dev-founder-asset-service-token",
        }
        body = {
            "workspace_id": "ws-1",
            "operation": "CREATE",
            "asset_kind": "AGENT",
            "asset_id": "agent.custom.2",
            "name": "Custom Agent 2",
            "version": "0.1.0",
            "content": {"instructions": "hello world"},
            "created_by": "founder-1",
        }
        resp = await client.post(
            "/agent/internal/founder-assets/commands",
            headers=headers,
            json=body,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_id"] == "agent.custom.2"
        assert data["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_internal_routes_creates_skill_draft_with_skill_kind():
    app = create_cosa_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"X-Service-Token": "dev-founder-asset-service-token"}
        body = {
            "workspace_id": "ws-1",
            "operation": "CREATE",
            "asset_kind": "SKILL",
            "asset_id": "skill.custom.search",
            "name": "Custom Search",
            "version": "0.1.0",
            "content": {"name": "skill.custom.search", "instructions": "search"},
            "created_by": "founder-1",
        }
        resp = await client.post(
            "/agent/internal/founder-assets/commands",
            headers=headers,
            json=body,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_id"] == "skill.custom.search"
        assert data["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_internal_routes_publish_requires_company_command_ref():
    app = create_cosa_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"X-Service-Token": "dev-founder-asset-service-token"}
        body = {
            "workspace_id": "ws-1",
            "operation": "PUBLISH",
            "asset_id": "agent.custom.2",
            "expected_hash": "sha256:dummy",
            # missing company_command_ref
        }
        resp = await client.post(
            "/agent/internal/founder-assets/commands",
            headers=headers,
            json=body,
        )
        assert resp.status_code == 400
        assert "company_command_ref is required" in resp.json()["detail"]
