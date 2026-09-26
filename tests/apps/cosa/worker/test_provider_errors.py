import pytest

from apps.cosa.worker.provider_errors import classify_run_error

DEEPSEEK_MSG = (
    'litellm.BadRequestError: DeepseekException - {"error":{"message":"Insufficient '
    'Balance (request_id: x)","type":"unknown_error","param":null,"code":"invalid_request_error"}}'
)


def test_insufficient_balance_vi() -> None:
    r = classify_run_error(DEEPSEEK_MSG, "vi-VN")
    assert r.code == "provider_insufficient_balance"
    assert "hết hạn mức" in r.user_message
    assert "litellm" not in r.user_message and "request_id" not in r.user_message


def test_insufficient_balance_en() -> None:
    r = classify_run_error(DEEPSEEK_MSG, "en-US")
    assert r.code == "provider_insufficient_balance"
    assert "quota" in r.user_message.lower()


@pytest.mark.parametrize(
    ("msg", "code"),
    [
        ("litellm.AuthenticationError: invalid api key", "provider_auth"),
        ("litellm.RateLimitError: 429 too many requests", "provider_rate_limited"),
        ("litellm.ServiceUnavailableError: 503", "provider_unavailable"),
        ("litellm.Timeout: request timed out", "provider_unavailable"),
        ("Error running tool x: 422: unknown variables: ['query']", "tool_input_invalid"),
        ("Max turns (10) exceeded", "agent_max_turns"),
        ("something else entirely", "unknown"),
    ],
)
def test_codes(msg: str, code: str) -> None:
    assert classify_run_error(msg, "vi-VN").code == code


def test_unknown_locale_defaults_to_vi() -> None:
    assert "hết hạn mức" in classify_run_error(DEEPSEEK_MSG, "").user_message


def test_unknown_error_message_does_not_echo_raw_text() -> None:
    r = classify_run_error("secret-path /etc/x leaked", "vi-VN")
    assert "secret-path" not in r.user_message
