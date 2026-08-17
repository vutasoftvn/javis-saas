import pytest
from app.core.telemetry import filter_attributes, trace_span


def test_telemetry_filters_sensitive_keys():
    raw_attrs = {
        "workspace_id": 12345,
        "user_id": 67890,
        "tool_name": "sales.pipeline_summary",
        "api_key": "sk-secret-key-12345",
        "access_token": "bearer-token-abc",
        "auth_header": "Basic xyz",
        "chain_of_thought": "Private reasoning steps...",
    }

    filtered = filter_attributes(raw_attrs)

    assert "workspace_id" in filtered
    assert "user_id" in filtered
    assert "tool_name" in filtered
    assert "api_key" not in filtered
    assert "access_token" not in filtered
    assert "auth_header" not in filtered
    assert "chain_of_thought" not in filtered


def test_telemetry_trace_span_context_manager():
    with trace_span("test_operation", {"workspace_id": 100}) as span:
        # Code execution inside span
        val = 1 + 1
        assert val == 2
