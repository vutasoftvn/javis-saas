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
    assert metrics.input_tokens == 0
    assert metrics.output_tokens == 0
    assert metrics.cost_usd is None


def test_compute_run_metrics_sums_real_token_usage_across_generation_spans():
    run = AgentRun(agent_key="a1", goal="g")
    spans = [
        {"name": "model_generation.completed", "model": "claude-sonnet-5", "input_tokens": 100, "output_tokens": 20},
        {"name": "model_generation.completed", "model": "claude-sonnet-5", "input_tokens": 50, "output_tokens": 10},
    ]

    metrics = compute_run_metrics(run, spans)

    assert metrics.input_tokens == 150
    assert metrics.output_tokens == 30
    # No pricing_table supplied -> no fabricated cost.
    assert metrics.cost_usd is None


def test_compute_run_metrics_computes_cost_only_with_a_supplied_pricing_table():
    run = AgentRun(agent_key="a1", goal="g")
    spans = [
        {"name": "model_generation.completed", "model": "test-model", "input_tokens": 1_000_000, "output_tokens": 1_000_000},
    ]

    metrics = compute_run_metrics(run, spans, pricing_table={"test-model": (3.0, 15.0)})

    assert metrics.cost_usd == 18.0


def test_compute_run_metrics_leaves_cost_none_when_any_model_is_unpriced():
    run = AgentRun(agent_key="a1", goal="g")
    spans = [
        {"name": "model_generation.completed", "model": "priced-model", "input_tokens": 1000, "output_tokens": 0},
        {"name": "model_generation.completed", "model": "unpriced-model", "input_tokens": 1000, "output_tokens": 0},
    ]

    metrics = compute_run_metrics(run, spans, pricing_table={"priced-model": (1.0, 1.0)})

    assert metrics.cost_usd is None
