from app.modules.agent_memory.redact import redact_text


def test_redact_text_handles_none_and_empty():
    assert redact_text(None) is None
    assert redact_text("") == ""


def test_redact_openai_style_api_key():
    text = "Set OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwx1234 before running."
    result = redact_text(text)
    assert "sk-abcdefghijklmnopqrstuvwx1234" not in result
    assert "[REDACTED:openai_api_key]" in result


def test_redact_google_api_key():
    text = "GOOGLE_API_KEY=AIzaSyD-abcdefghijklmnopqrstuvwxyz012345"
    result = redact_text(text)
    assert "AIzaSyD-abcdefghijklmnopqrstuvwxyz012345" not in result
    assert "[REDACTED:google_api_key]" in result


def test_redact_github_token():
    text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    result = redact_text(text)
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in result
    assert "[REDACTED:github_token]" in result


def test_redact_slack_token():
    text = "webhook uses xoxb-1234567890-abcdefghij"
    result = redact_text(text)
    assert "xoxb-1234567890-abcdefghij" not in result
    assert "[REDACTED:slack_token]" in result


def test_redact_authorization_header():
    text = "curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc'"
    result = redact_text(text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc" not in result
    assert "[REDACTED:authorization_header]" in result


def test_redact_bare_bearer_token():
    text = "sent bearer a1b2c3d4e5f6a1b2c3d4e5f6 to the API"
    result = redact_text(text)
    assert "a1b2c3d4e5f6a1b2c3d4e5f6" not in result
    assert "[REDACTED:bearer_token]" in result


def test_redact_private_key_block():
    text = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEA1234567890abcdef\n"
        "-----END RSA PRIVATE KEY-----"
    )
    result = redact_text(text)
    assert "MIIEpAIBAAKCAQEA1234567890abcdef" not in result
    assert "[REDACTED:private_key_block]" in result


def test_redact_connection_string_with_credentials():
    text = "DATABASE_URL=postgresql://appuser:s3cr3tpass@db.internal:5432/cosa"
    result = redact_text(text)
    assert "appuser:s3cr3tpass" not in result
    assert "[REDACTED:connection_string_credentials]" in result


def test_redact_password_assignment():
    text = "config had password: hunter2fallback in the log line"
    result = redact_text(text)
    assert "hunter2fallback" not in result
    assert "[REDACTED:password_assignment]" in result


def test_redact_session_cookie():
    text = "response header Cookie: session_id=abc123def456; other=1"
    result = redact_text(text)
    assert "abc123def456" not in result
    assert "[REDACTED:session_cookie]" in result


def test_redact_generic_secret_assignment():
    text = "refresh_token: 8f14e45fceea167a5a36dedd4bea2543"
    result = redact_text(text)
    assert "8f14e45fceea167a5a36dedd4bea2543" not in result
    assert "[REDACTED:generic_secret_assignment]" in result


def test_redact_seed_phrase_twelve_words():
    text = (
        "wallet seed was legal winner thank year wave sausage worth "
        "useful legal winner thank recovered from backup"
    )
    result = redact_text(text)
    assert "[REDACTED:seed_phrase]" in result


def test_redact_leaves_ordinary_text_untouched():
    text = "Fixed the flaky test in test_devices.py by mocking the DB session."
    assert redact_text(text) == text
