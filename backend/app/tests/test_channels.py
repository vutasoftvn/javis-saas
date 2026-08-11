import pytest
from app.core.snowflake import generate_snowflake_id
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.db.models import User

client = TestClient(app)

def mock_get_current_user():
    user = User()
    user.id = generate_snowflake_id()
    user.status = "active"
    user.email = "test@example.com"
    return user

app.dependency_overrides[get_current_user] = mock_get_current_user

def test_telegram_webhook_not_found():
    random_id = str(generate_snowflake_id())
    response = client.post(f"/api/v1/channels/telegram/webhook/{random_id}", json={"update_id": 123})
    assert response.status_code == 404
    assert response.json()["detail"] in ("Chatbot not found", "Not Found")

def test_zalo_webhook_not_found():
    random_id = str(generate_snowflake_id())
    response = client.post(f"/api/v1/channels/zalo/webhook/{random_id}", json={"event_name": "user_send_text"})
    assert response.status_code == 404
    assert response.json()["detail"] in ("Chatbot not found", "Not Found")
