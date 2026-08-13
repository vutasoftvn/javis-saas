import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from app.core.snowflake import generate_snowflake_id
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.db.models import User
from app.db.models import Chatbot
from app.services.channels.channel_worker import process_telegram_bot

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


@pytest.mark.asyncio
async def test_telegram_worker_denies_messages_without_an_allowlist(monkeypatch):
    class Client:
        def __init__(self):
            self.posts = []

        async def get(self, *_args, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {
                "ok": True,
                "result": [{"update_id": 1, "message": {"chat": {"id": "untrusted"}, "text": "hello"}}],
            })

        async def post(self, *args, **kwargs):
            self.posts.append((args, kwargs))
            return SimpleNamespace(status_code=200, json=lambda: {"ok": True})

    monkeypatch.setattr("app.services.channels.channel_worker._generate_ai_reply", lambda _: "reply")
    bot = Chatbot(id=1, channel="telegram", channel_config_jsonb={"bot_token": "secret", "is_enabled": True, "allowed_chat_ids": ""})
    client = Client()

    await process_telegram_bot(client, bot, MagicMock())

    assert client.posts == []
    assert bot.channel_config_jsonb["allowed_chat_ids"] == ""
