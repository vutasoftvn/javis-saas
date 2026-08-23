from __future__ import annotations

import pytest

from agentos.core.events import InMemoryEventBus
from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.observability.otel import OtelTracer
from agentos.tools.registry import ToolRegistry


def test_otel_tracer_parent_child_hierarchy_and_correlation_id():
    tracer = OtelTracer(service_name="agentos-chat")

    # Parent span: agent request
    parent = tracer.start_span(
        "agent.request",
        correlation_id="corr-test-999",
        workspace_id="ws1",
        attributes={"task.goal": "Prepare report"},
    )

    # Child span: context builder
    child_ctx = tracer.start_span(
        "context_builder.build",
        trace_id=parent.trace_id,
        parent_span_id=parent.span_id,
        correlation_id=parent.correlation_id,
    )
    tracer.end_span(child_ctx, status="OK", snippets_count=5)

    # Child span: tool call
    child_tool = tracer.start_span(
        "tool.invoke",
        trace_id=parent.trace_id,
        parent_span_id=parent.span_id,
        correlation_id=parent.correlation_id,
        attributes={"tool_name": "commercial.lead.list"},
    )
    tracer.end_span(child_tool, status="OK")

    tracer.end_span(parent, status="OK")

    # Query spans by correlation ID
    spans = tracer.get_spans(correlation_id="corr-test-999")
    assert len(spans) == 3

    assert parent.span_id == child_ctx.parent_span_id
    assert parent.span_id == child_tool.parent_span_id
    assert child_ctx.attributes["snippets_count"] == 5
    assert child_ctx.attributes["correlation_id"] == "corr-test-999"


@pytest.mark.asyncio
async def test_otel_and_sqlite_trace_sink_work_concurrently():
    sqlite_sink = SqliteTraceSink()
    otel_tracer = OtelTracer(service_name="agentos")

    provider = StubModelProvider([ModelResponse(text="Task finished successfully")])
    registry = ToolRegistry()
    runtime = AgentRuntime(
        model_provider=provider,
        tool_registry=registry,
        trace_sink=sqlite_sink,
    )

    task = TaskContext(
        goal="Generate summary",
        agent_key="reporter",
        workspace_id="ws1",
        correlation_id="corr-concurrent-1",
    )

    # Instrument runtime run with OTEL span
    root_span = otel_tracer.start_span("agent.run", correlation_id=task.correlation_id)
    result = await runtime.run(task)
    otel_tracer.end_span(root_span, status=result.status.value)

    assert result.status == AgentRunStatus.COMPLETED

    # Verify OTEL captured the span
    otel_spans = otel_tracer.get_spans(correlation_id="corr-concurrent-1")
    assert len(otel_spans) == 1
    assert otel_spans[0].name == "agent.run"
    assert otel_spans[0].status == "COMPLETED"

    # Verify SQLite trace sink also captured the events
    traces = sqlite_sink.export_by_correlation_id("corr-concurrent-1")
    assert len(traces) >= 2  # agent.run.started + agent.run.completed
