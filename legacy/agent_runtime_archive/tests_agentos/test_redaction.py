from agentos.core.redaction import REDACTED_PLACEHOLDER, redact_payload


def test_redact_payload_masks_top_level_sensitive_key():
    result = redact_payload({"api_key": "sk-live-12345", "tool_name": "call_llm"})
    assert result["api_key"] == REDACTED_PLACEHOLDER
    assert result["tool_name"] == "call_llm"


def test_redact_payload_masks_nested_sensitive_key():
    result = redact_payload({"arguments": {"password": "hunter2", "username": "bob"}})
    assert result["arguments"]["password"] == REDACTED_PLACEHOLDER
    assert result["arguments"]["username"] == "bob"


def test_redact_payload_masks_sensitive_key_inside_list():
    result = redact_payload({"result": [{"access_token": "abc"}, {"ok": True}]})
    assert result["result"][0]["access_token"] == REDACTED_PLACEHOLDER
    assert result["result"][1]["ok"] is True


def test_redact_payload_does_not_touch_lookalike_keys():
    """Regression guard: substring-matching "token" would wrongly redact
    input_tokens/output_tokens (real fields on model_generation.completed
    events, agentos/core/executor.py:82-83) — must be exact-key matching."""
    payload = {"input_tokens": 10, "output_tokens": 5}
    assert redact_payload(payload) == payload


def test_redact_payload_is_case_and_separator_insensitive():
    result = redact_payload({"Authorization": "Bearer abc", "API-KEY": "xyz"})
    assert result["Authorization"] == REDACTED_PLACEHOLDER
    assert result["API-KEY"] == REDACTED_PLACEHOLDER


def test_redact_payload_does_not_mutate_input():
    original = {"password": "hunter2"}
    redact_payload(original)
    assert original["password"] == "hunter2"


def test_redact_payload_handles_all_canonical_sensitive_keys():
    payload = {
        "api_key": "k1",
        "apikey": "k2",
        "secret": "s1",
        "password": "p1",
        "passwd": "p2",
        "token": "t1",
        "access_token": "at1",
        "refresh_token": "rt1",
        "authorization": "Bearer auth1",
        "auth": "auth2",
        "bearer": "bearer1",
        "private_key": "pk1",
        "client_secret": "cs1",
        "credit_card": "4111",
        "ssn": "000-00-0000",
    }
    result = redact_payload(payload)
    for key in payload:
        assert result[key] == REDACTED_PLACEHOLDER, f"Key {key} was not redacted"


def test_redact_payload_preserves_primitives_numbers_and_none():
    payload = {
        "count": 42,
        "ratio": 3.1415,
        "flag": False,
        "empty": None,
        "items": [1, 2, "hello", True, None],
    }
    result = redact_payload(payload)
    assert result == payload
    assert isinstance(result["count"], int)
    assert isinstance(result["ratio"], float)
    assert result["empty"] is None
    assert result["items"] == [1, 2, "hello", True, None]


def test_redact_payload_masks_embedded_connector_tokens():
    # Slack token in raw string message
    slack_msg = "Error posting to Slack with token xoxb-1234567890-abcdef123456"
    assert "xoxb-1234567890-abcdef123456" not in redact_payload(slack_msg)
    assert REDACTED_PLACEHOLDER in redact_payload(slack_msg)

    # OpenAI API key in error text
    openai_err = "API connection failed using sk-proj-1234567890abcdefghijklmn"
    assert "sk-proj-1234567890" not in redact_payload(openai_err)
    assert REDACTED_PLACEHOLDER in redact_payload(openai_err)

    # Postgres connection string with password
    db_uri = "Connection failed: postgres://admin:SuperSecretPass123@db.internal:5432/app"
    redacted_db = redact_payload(db_uri)
    assert "SuperSecretPass123" not in redacted_db
    assert "postgres://admin:***REDACTED***@db.internal:5432/app" in redacted_db
