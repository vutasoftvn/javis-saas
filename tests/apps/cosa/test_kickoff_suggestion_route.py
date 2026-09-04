from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from fastapi import FastAPI
from apps.cosa.api.kickoff_suggestion_routes import create_kickoff_suggestion_router


@pytest.fixture
def test_app():
    app = FastAPI()
    router = create_kickoff_suggestion_router()
    app.include_router(router)

    mock_plane = MagicMock()
    mock_scheduler = MagicMock()
    mock_scheduler.schedule = AsyncMock()
    mock_plane.scheduler = mock_scheduler
    app.state.plane = mock_plane
    return app


_VALID_BODY = {
    "workspace_id": "ws_123",
    "project_id": "proj_456",
    "run_id": "run-abc-123",
    "target_customer": "Founder B2B SaaS",
    "problem_statement": "Không biết validate ý tưởng",
    "evidence_level": "NONE",
    "selected_stage": "P0_DISCOVERY",
    "stage_duration_weeks": 2,
}


@pytest.mark.asyncio
async def test_dispatch_unauthorized_missing_token(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/agent/kickoff/first-week-suggestion", json=_VALID_BODY)
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_authorized_schedules_task(test_app, monkeypatch):
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "secret-test-token")
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/agent/kickoff/first-week-suggestion",
            headers={"X-Cosa-Service-Token": "secret-test-token"},
            json=_VALID_BODY,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["run_id"] == "run-abc-123"

        scheduler = test_app.state.plane.scheduler
        assert scheduler.schedule.await_count == 1
        call_args = scheduler.schedule.call_args.kwargs
        assert call_args["target_spec_id"] == "cosa.agents.operations"
        payload = call_args["input_payload"]
        assert payload["task_type"] == "kickoff_suggestion"
        assert payload["run_id"] == "run-abc-123"
        assert payload["project_id"] == "proj_456"
        assert payload["target_customer"] == "Founder B2B SaaS"
