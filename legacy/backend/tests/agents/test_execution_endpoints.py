from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from core.auth import get_current_workspace_member
from core.snowflake import generate_snowflake_id
from db.models import WorkspaceMember
from db.session import get_db
from main import app


def _member(workspace_id: int, user_id: int) -> WorkspaceMember:
    m = WorkspaceMember()
    m.workspace_id = workspace_id
    m.user_id = user_id
    m.role = "admin"
    return m


def test_execution_endpoint_returns_403_when_flag_disabled():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    member = _member(ws_id, user_id)
    db = MagicMock()

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db

    try:
        with patch("workforce.agents.execution_router.is_enabled", return_value=False):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/execution/jobs",
                json={"agent_key": "test_agent", "commands": ["python -c 'print(1)'"]},
            )
            assert response.status_code == 403
            assert "Execution runtime is disabled" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_execution_create_job_returns_201_and_string_ids_when_flag_enabled():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    member = _member(ws_id, user_id)
    db = MagicMock()

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db

    try:
        with patch("workforce.agents.execution_router.is_enabled", return_value=True):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/execution/jobs",
                json={"agent_key": "test_agent", "commands": ["python -c 'print(1)'"]},
            )
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert isinstance(data["id"], str)
            assert data["id_str"] == data["id"]
            assert data["workspace_id"] == str(ws_id)
            assert data["status"] == "queued"
    finally:
        app.dependency_overrides.clear()


def test_execution_get_job_cross_workspace_returns_404():
    ws_id = generate_snowflake_id()
    other_ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    member = _member(ws_id, user_id)
    db = MagicMock()

    # Query returns None for scoped lookup
    db.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db

    try:
        with patch("workforce.agents.execution_router.is_enabled", return_value=True):
            client = TestClient(app)
            response = client.get("/api/v1/agents/execution/jobs/999999999")
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
