from app.core.snowflake import generate_snowflake_id
from urllib.parse import parse_qs, urlparse

import pytest

from app.modules.integrations import google_oauth_service as oauth
from app.modules.integrations.google_oauth_service import GoogleOAuthError


@pytest.fixture(autouse=True)
def _oauth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/connectors/google/oauth/callback"
    )


def test_state_round_trips_the_workspace_it_was_signed_for():
    workspace_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    payload = oauth.verify_state(oauth.sign_state(workspace_id, user_id))

    assert payload["workspace_id"] == str(workspace_id)
    assert payload["user_id"] == str(user_id)


def test_tampered_state_is_rejected():
    """Callback của Google KHÔNG kèm JWT, workspace_id chỉ đến từ state. Sửa được state là
    gắn được hòm thư của mình vào workspace người khác (hoặc ngược lại)."""
    state = oauth.sign_state(generate_snowflake_id(), generate_snowflake_id())
    raw, signature = state.split(".", 1)
    forged = oauth.sign_state(generate_snowflake_id(), generate_snowflake_id()).split(".", 1)[0]

    with pytest.raises(GoogleOAuthError):
        oauth.verify_state(f"{forged}.{signature}")
    with pytest.raises(GoogleOAuthError):
        oauth.verify_state(f"{raw}.{'0' * len(signature)}")
    with pytest.raises(GoogleOAuthError):
        oauth.verify_state("khong-co-dau-cham")


def test_state_signed_with_another_secret_is_rejected(monkeypatch):
    state = oauth.sign_state(generate_snowflake_id(), generate_snowflake_id())
    monkeypatch.setenv("JWT_SECRET", "một-secret-khác")

    with pytest.raises(GoogleOAuthError):
        oauth.verify_state(state)


def test_expired_state_is_rejected(monkeypatch):
    monkeypatch.setattr(oauth, "STATE_TTL_SECONDS", -1)
    state = oauth.sign_state(generate_snowflake_id(), generate_snowflake_id())

    with pytest.raises(GoogleOAuthError) as exc:
        oauth.verify_state(state)

    assert "hết hạn" in str(exc.value)


def test_authorize_url_asks_for_offline_access_and_the_right_scopes():
    """Thiếu access_type=offline là Google không phát refresh token, và kết nối chết đúng
    sau 1 giờ - hỏng vào lúc người dùng đã quên mất mình vừa kết nối."""
    url = oauth.build_authorize_url(oauth.sign_state(generate_snowflake_id(), generate_snowflake_id()))
    params = parse_qs(urlparse(url).query)

    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    scopes = params["scope"][0].split(" ")
    assert "https://www.googleapis.com/auth/gmail.readonly" in scopes
    assert "https://www.googleapis.com/auth/gmail.compose" in scopes
    # Không xin quyền rộng hơn mức tính năng cần.
    assert not any("gmail.modify" in scope or "mail.google.com" in scope for scope in scopes)


def test_authorize_url_passes_the_login_hint():
    url = oauth.build_authorize_url("state", login_hint="ai@example.com")

    assert parse_qs(urlparse(url).query)["login_hint"] == ["ai@example.com"]


def test_unconfigured_server_says_what_is_missing(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    assert oauth.is_configured() is False
    with pytest.raises(GoogleOAuthError) as exc:
        oauth.build_authorize_url("state")

    assert "GOOGLE_CLIENT_ID" in str(exc.value)
