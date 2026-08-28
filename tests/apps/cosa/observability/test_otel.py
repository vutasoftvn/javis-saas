from __future__ import annotations

import os
import pytest

from apps.cosa.observability.otel import (
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    init_tracing,
    inject_trace_carrier,
    sync_trace_span,
    trace_span,
)


def test_init_tracing_noop_without_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    provider = init_tracing("cosa-test-service")
    assert provider is not None
    tracer = get_tracer("test")
    assert tracer is not None


@pytest.mark.asyncio
async def test_trace_span_async_lifecycle():
    init_tracing("cosa-test-async")

    assert get_current_trace_id() is None
    assert get_current_span_id() is None

    async with trace_span("test.operation", attributes={"run_id": "run_test_123", "count": 42}) as span:
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        assert trace_id is not None
        assert len(trace_id) == 32
        assert span_id is not None
        assert len(span_id) == 16

        # Test carrier injection during active span
        headers = {"Content-Type": "application/json"}
        carrier = inject_trace_carrier(headers)
        assert "traceparent" in carrier
        assert trace_id in carrier["traceparent"]

    # Outside span context
    assert get_current_trace_id() is None


def test_sync_trace_span_lifecycle():
    init_tracing("cosa-test-sync")

    with sync_trace_span("test.sync_op", attributes={"test_key": "test_val"}):
        trace_id = get_current_trace_id()
        assert trace_id is not None
        assert len(trace_id) == 32

    assert get_current_trace_id() is None


@pytest.mark.asyncio
async def test_trace_span_records_exception():
    init_tracing("cosa-test-exc")

    with pytest.raises(ValueError, match="Operation failed"):
        async with trace_span("failing.span", attributes={"run_id": "run_fail"}):
            raise ValueError("Operation failed")
