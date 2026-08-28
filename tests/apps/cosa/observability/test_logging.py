from __future__ import annotations

import io
import json
import logging

from apps.cosa.observability.logging import (
    JSONLogFormatter,
    clear_log_context,
    log_context,
    redact_sensitive_text,
    set_log_context,
    setup_logging,
)


def test_redact_sensitive_text_api_keys():
    # Fixture giả — chuỗi placeholder không phải key thật (tránh secret-scanner
    # push protection). Chỉ cần khớp regex sk-[A-Za-z0-9_-]{20,} để test redaction.
    fake_key = "sk-PLACEHOLDERplaceholderPLACEHOLDER00"
    raw = f"Calling model provider with {fake_key} and key=secret12345"
    redacted = redact_sensitive_text(raw)
    assert fake_key not in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_redact_sensitive_text_bearer_tokens():
    raw = "Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdef"
    redacted = redact_sensitive_text(raw)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
    assert "Bearer [REDACTED]" in redacted


def test_redact_sensitive_text_postgres_dsn():
    raw = "Connecting to postgresql+asyncpg://db_user:SuperSecretPassword123@prod-db.example.com:5432/javis_db"
    redacted = redact_sensitive_text(raw)
    assert "SuperSecretPassword123" not in redacted
    assert "postgresql+asyncpg://db_user:[REDACTED]@prod-db.example.com:5432/javis_db" in redacted


def test_json_log_formatter_with_context():
    formatter = JSONLogFormatter(service_name="cosa-api-test")
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Processing execution task",
        args=(),
        exc_info=None,
    )

    with log_context(run_id="run_12345", workspace_id="ws_abcde"):
        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "INFO"
        assert data["msg"] == "Processing execution task"
        assert data["service"] == "cosa-api-test"
        assert data["run_id"] == "run_12345"
        assert data["workspace_id"] == "ws_abcde"
        assert "ts" in data


def test_setup_logging_and_stream_output():
    setup_logging(service_name="cosa-test-svc", log_level="INFO", json_format=True)
    logger = logging.getLogger("test.structured")

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONLogFormatter(service_name="cosa-test-svc"))
    logger.addHandler(handler)

    with log_context(run_id="run_999", workspace_id="ws_888"):
        logger.info("Test message with token sk-abcdef12345678901234567890")

    output = stream.getvalue()
    assert output.strip() != ""
    data = json.loads(output.strip())
    assert data["run_id"] == "run_999"
    assert data["workspace_id"] == "ws_888"
    assert "sk-abcdef12345678901234567890" not in data["msg"]
    assert "[REDACTED_API_KEY]" in data["msg"]
