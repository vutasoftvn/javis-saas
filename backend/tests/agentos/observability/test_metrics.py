# backend/tests/agentos/observability/test_metrics.py
from agentos.core.models import AgentRun, AgentRunStatus
from agentos.observability.metrics import compute_run_metrics


def test_compute_run_metrics_counts_completed_tool_calls():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)
    spans = [
        {"name": "agent_run.started"},
        {"name": "tool_call.started"},
        {"name": "tool_call.completed"},
        {"name": "tool_call.started"},
        {"name": "tool_call.completed"},
        {"name": "agent_run.completed"},
    ]

    metrics = compute_run_metrics(run, spans)

    assert metrics.tool_call_count == 2
    assert metrics.span_count == 6
    assert metrics.latency_seconds >= 0.0


def test_compute_run_metrics_zero_tool_calls_and_no_spans():
    run = AgentRun(agent_key="a1", goal="g")

    metrics = compute_run_metrics(run, [])

    assert metrics.tool_call_count == 0
    assert metrics.span_count == 0
