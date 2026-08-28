from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from fastapi import FastAPI
from apps.cosa.api.copilot_routes import create_copilot_router


@pytest.fixture
def test_app():
    app = FastAPI()
    router = create_copilot_router()
    app.include_router(router)

    mock_plane = MagicMock()
    mock_scheduler = MagicMock()
    mock_scheduler.schedule = AsyncMock()
    mock_plane.scheduler = mock_scheduler
    app.state.plane = mock_plane
    return app


@pytest.mark.asyncio
async def test_dispatch_copilot_unauthorized_missing_token(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/agent/copilot/customer-support",
            json={
                "workspace_id": "ws_123",
                "thread_ref": {"thread_id": "t_456"},
                "intent": "summarize",
                "correlation_id": "corr-1",
            },
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_copilot_authorized_success(test_app, monkeypatch):
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "secret-test-token")
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/agent/copilot/customer-support",
            headers={"X-Cosa-Service-Token": "secret-test-token"},
            json={
                "workspace_id": "ws_123",
                "thread_ref": {"thread_id": "t_456", "contact_id": "c_789"},
                "intent": "summarize",
                "knowledge_scope": {"profile_types": ["product"]},
                "identity_verified": True,
                "correlation_id": "corr-1",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert data["run_id"].startswith("run_")

        # Verify scheduler schedule called with target_spec_id cosa.customer_support
        scheduler = test_app.state.plane.scheduler
        assert scheduler.schedule.await_count == 1
        call_args = scheduler.schedule.call_args.kwargs
        assert call_args["target_spec_id"] == "cosa.customer_support"
        payload = call_args["input_payload"]
        assert payload["task_type"] == "run"
        assert payload["agent_profile"] == "customer_support"
        assert payload["copilot"] is True
        assert payload["workspace_id"] == "ws_123"
        assert payload["thread_ref"] == {"thread_id": "t_456", "contact_id": "c_789"}
        assert payload["intent"] == "summarize"
        assert payload["identity_verified"] is True
