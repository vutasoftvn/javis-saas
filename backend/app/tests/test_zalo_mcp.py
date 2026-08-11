import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.auth import get_current_user
from app.db.models import User

client = TestClient(app)

def mock_get_current_user():
    return User(id="33908e96-98ba-4179-b3a4-f2bc18bbc7ed", email="test@mivacorp.com")

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()

def test_start_zalo_qr_forbidden_workspace():
    # Workspace không thuộc về user test -> trả về 403
    response = client.post(
        "/api/v1/connectors/zalo/start",
        json={"workspace_id": "00000000-0000-0000-0000-000000000000", "label": "Test Zalo"}
    )
    assert response.status_code == 403

def test_get_zalo_qr_status_non_existent():
    response = client.get("/api/v1/connectors/zalo/status/non_existent_sid")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "error"
    assert "không tồn tại" in data["error"]

def test_cancel_zalo_qr():
    response = client.post("/api/v1/connectors/zalo/cancel/fake_sid")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
