import jwt as pyjwt

from app.core.snowflake import generate_snowflake_id
from app.modules.realtime.token_service import generate_livekit_token


def test_generate_livekit_token_has_correct_room_and_identity(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-that-is-long-enough-1234567890")

    room_name = f"cosa-{generate_snowflake_id()}"
    token = generate_livekit_token(
        room_name=room_name,
        identity="human:42",
        display_name="user-42",
    )

    payload = pyjwt.decode(token, "test-secret-that-is-long-enough-1234567890", algorithms=["HS256"])

    assert payload["sub"] == "human:42"
    assert payload["iss"] == "test-key"
    assert payload["name"] == "user-42"
    assert payload["video"]["room"] == room_name
    assert payload["video"]["roomJoin"] is True
    assert payload["video"]["canPublish"] is True
    assert payload["video"]["canSubscribe"] is True
    assert payload["video"]["canPublishData"] is True


def test_generate_livekit_token_respects_ttl(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-that-is-long-enough-1234567890")

    token = generate_livekit_token(
        room_name="cosa-room",
        identity="human:1",
        display_name="user-1",
        ttl_seconds=120,
    )
    payload = pyjwt.decode(token, "test-secret-that-is-long-enough-1234567890", algorithms=["HS256"])

    assert payload["exp"] - payload["nbf"] == 120


def test_generate_livekit_token_default_ttl_is_four_hours(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-that-is-long-enough-1234567890")

    token = generate_livekit_token(
        room_name="cosa-room",
        identity="human:1",
        display_name="user-1",
    )
    payload = pyjwt.decode(token, "test-secret-that-is-long-enough-1234567890", algorithms=["HS256"])

    assert payload["exp"] - payload["nbf"] == 4 * 3600
