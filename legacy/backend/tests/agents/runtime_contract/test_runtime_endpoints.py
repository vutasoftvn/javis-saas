import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_AGENT_RUNTIME_DEEPSEEK
from db.session import get_db
from db.models import WorkspaceMember
from core.snowflake import generate_snowflake_id


@pytest.fixture
def mock_context():
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()

    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="owner",
    )
    return member, user_id, workspace_id


def test_runtime_health_endpoint(client: TestClient):
    response = client.get("/api/v1/agents/runtime/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "unavailable")
    assert "runtime_name" in data


def test_runtime_run_endpoint_mock(client: TestClient, mock_context):
    member, user_id, workspace_id = mock_context
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        payload = {
            "company_id": str(workspace_id),
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "agent_key": "runtime_test_agent",
            "task": "Qualify potential lead",
            "context": {"runtime_name": "mock"},
            "permission_profile": "read_only",
        }

        response = client.post("/api/v1/agents/runtime/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["runtime"] == "mock"
        assert "run_id" in data
    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
        app.dependency_overrides.pop(get_db, None)


def test_runtime_run_endpoint_tenant_mismatch_forbidden(client: TestClient, mock_context):
    member, user_id, workspace_id = mock_context
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        payload = {
            "company_id": str(workspace_id),
            "workspace_id": "999999999999",  # Different workspace
            "user_id": str(user_id),
            "agent_key": "runtime_test_agent",
            "task": "Qualify lead",
        }

        response = client.post("/api/v1/agents/runtime/run", json=payload)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
        app.dependency_overrides.pop(get_db, None)


def test_runtime_run_endpoint_deepseek_flag_enforced(client: TestClient, mock_context):
    member, user_id, workspace_id = mock_context
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # Flag is disabled by default (mock_db query returns None)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        payload = {
            "company_id": str(workspace_id),
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "agent_key": "runtime_test_agent",
            "task": "Qualify lead",
            "context": {"runtime_name": "deepseek_harness"},
        }

        response = client.post("/api/v1/agents/runtime/run", json=payload)
        assert response.status_code == 403

        # Now simulate flag enabled (mock_db query returns an active flag object)
        flag_mock = MagicMock()
        flag_mock.enabled = True
        mock_db.query.return_value.filter.return_value.first.return_value = flag_mock

        response2 = client.post("/api/v1/agents/runtime/run", json=payload)
        assert response2.status_code in (200, 503)
    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
        app.dependency_overrides.pop(get_db, None)
