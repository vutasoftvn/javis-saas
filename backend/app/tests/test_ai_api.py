from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.core.snowflake import generate_snowflake_id


def test_ai_usage_endpoint_success():
    ws_id = generate_snowflake_id()
    mock_member = WorkspaceMember(workspace_id=ws_id, role="member")

    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.all.return_value = []

    app.dependency_overrides[get_current_workspace_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: db_mock

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/ai/usage?workspace_id={ws_id}&period=7d")
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "week_7d" in data
        assert "rolling_30d" in data
        assert "all_time" in data
        assert "by_provider" in data
        assert "openrouter_key_info" in data
    finally:
        app.dependency_overrides.clear()


def test_ai_usage_endpoint_forbidden():
    ws_id = generate_snowflake_id()
    other_ws_id = generate_snowflake_id()
    mock_member = WorkspaceMember(workspace_id=ws_id, role="member")

    app.dependency_overrides[get_current_workspace_member] = lambda: mock_member
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/ai/usage?workspace_id={other_ws_id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
