from __future__ import annotations

import json

from apps.cosa.compliance.audit_metadata import safe_audit_metadata


def test_safe_audit_metadata_excludes_prompt_and_result() -> None:
    event = safe_audit_metadata(
        "model.denied",
        {"run_id": "run_1", "prompt": "secret contract clause"},
        {"reason_code": "PROVIDER_NOT_APPROVED"},
    )
    serialized = json.dumps(event)
    assert "secret contract clause" not in serialized
    assert event["reason_code"] == "PROVIDER_NOT_APPROVED"
    assert event["run_id"] == "run_1"
    assert event["event_type"] == "model.denied"
