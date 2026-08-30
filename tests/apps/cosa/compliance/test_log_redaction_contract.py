from __future__ import annotations

import json
import logging

from apps.cosa.observability.logging import JSONLogFormatter, redact_sensitive_text


def test_redact_sensitive_text_masks_credentials_and_pii() -> None:
    raw = (
        "User customer@example.com called with Bearer secret-token-1234567890 "
        "and sk-abcdefghijklmnopqrstuvwxyz123456"
    )
    redacted = redact_sensitive_text(raw)
    assert "customer@example.com" not in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "secret-token-1234567890" not in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_json_log_formatter_enforces_allowlist_metadata() -> None:
    formatter = JSONLogFormatter(service_name="test-service")
    logger = logging.getLogger("test_redaction")

    record = logger.makeRecord(
        name="test_redaction",
        level=logging.INFO,
        fn="test.py",
        lno=10,
        msg="Processed user request for customer@example.com with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        args=(),
        exc_info=None,
        extra={
            # Allowlisted keys:
            "run_id": "run_01",
            "workspace_id": "ws_100",
            "capability_id": "model.input",
            "decision": "ALLOW",
            "snapshot_hash": "sha256:snap123",
            # Forbidden / unallowlisted keys:
            "Authorization": "Bearer super-secret-token",
            "company_delegation": "delegation-jwt-secret",
            "delegation_token": "token-123",
            "prompt": "Sensitive prompt content",
            "completion": "Model completion text",
            "raw_subject_reference": "customer@example.com",
        },
    )

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    # Allowlisted keys must be present
    assert parsed["run_id"] == "run_01"
    assert parsed["workspace_id"] == "ws_100"
    assert parsed["capability_id"] == "model.input"
    assert parsed["decision"] == "ALLOW"
    assert parsed["snapshot_hash"] == "sha256:snap123"

    # Forbidden keys must be completely absent
    assert "Authorization" not in parsed
    assert "company_delegation" not in parsed
    assert "delegation_token" not in parsed
    assert "prompt" not in parsed
    assert "completion" not in parsed
    assert "raw_subject_reference" not in parsed

    # Message text must be redacted
    assert "customer@example.com" not in parsed["msg"]
    assert "[EMAIL_REDACTED]" in parsed["msg"]
    assert "Bearer [REDACTED]" in parsed["msg"]
    assert "eyJhbGciOi" not in parsed["msg"]
