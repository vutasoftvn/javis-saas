"""Integration tests for AI Programs internal API router."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_programs_api():
    """Verify GET /api/v1/internal/ai/programs returns registered list."""
    response = client.get("/api/v1/internal/ai/programs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    keys = [p["key"] for p in data]
    assert "ceo.brief" in keys
    assert "sales.lead_qualification" in keys


def test_get_program_detail_api():
    """Verify GET /api/v1/internal/ai/programs/{key}."""
    response = client.get("/api/v1/internal/ai/programs/ceo.brief")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "ceo.brief"
    assert data["domain"] == "management"


def test_run_program_api():
    """Verify POST /api/v1/internal/ai/programs/run."""
    payload = {
        "workspace_id": "test_workspace_123",
        "program_key": "ceo.brief",
        "input": {
            "pending_approvals": [{"title": "Hire engineer"}],
        },
    }
    response = client.post("/api/v1/internal/ai/programs/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["program_key"] == "ceo.brief"
    assert data["status"] == "completed"
    assert "headline" in data["output"]
    assert "today_top_3" in data["output"]


def test_promote_and_rollback_api():
    """Verify candidate promotion and rollback endpoints."""
    promote_res = client.post(
        "/api/v1/internal/ai/programs/ceo.brief/promote",
        json={"version": "1.2.0", "approved_by": "lead_engineer"},
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["active_version"] == "1.2.0"

    rollback_res = client.post(
        "/api/v1/internal/ai/programs/ceo.brief/rollback",
        json={"target_version": "1.0.0"},
    )
    assert rollback_res.status_code == 200
    assert rollback_res.json()["active_version"] == "1.0.0"
