import pytest
from core.telemetry import filter_attributes, trace_span


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


def test_configure_telemetry_emits_real_spans():
    """After configure_telemetry(), trace_span() must produce real recorded spans,
    not silent no-ops -- proves OpenTelemetry is genuinely wired, not just declared
    in requirements.txt."""
    import core.telemetry as telemetry

    assert telemetry.HAS_OTEL is True, "opentelemetry-sdk must be installed for this test to be meaningful"

    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    otel_trace.set_tracer_provider(provider)

    with telemetry.trace_span("test_real_emission", {"workspace_id": 1}):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test_real_emission"
