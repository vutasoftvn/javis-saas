import os
from unittest.mock import patch

from app.workforce.agents.execution.redaction import redact


def test_redact_api_keys_and_tokens():
    text = "Error sk-abc12345678901234567890 occurred with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted = redact(text)

    assert "sk-abc12345678901234567890" not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "[REDACTED_TOKEN]" in redacted


def test_redact_sensitive_environment_variables():
    with patch.dict(os.environ, {"MASTER_SECRET_KEY": "super-secret-cosa-key-12345"}):
        text = "Process failed using key super-secret-cosa-key-12345 at runtime"
        redacted = redact(text)

        assert "super-secret-cosa-key-12345" not in redacted
        assert "[REDACTED_MASTER_SECRET_KEY]" in redacted
