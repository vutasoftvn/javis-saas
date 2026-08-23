from agentos.core.models import AgentRun, AgentRunStatus
from agentos.evals.model_eval import evaluate_models_across_runs


def _completed_run(model: str, *, input_tokens: int, output_tokens: int) -> tuple[AgentRun, list[dict]]:
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)
    spans = [
        {
            "name": "model_generation.completed",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    ]
    return run, spans


def _failed_run(model: str) -> tuple[AgentRun, list[dict]]:
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.FAILED)
    spans = [{"name": "model_generation.completed", "model": model, "input_tokens": 10, "output_tokens": 0}]
    return run, spans


def test_evaluate_models_groups_by_model_and_sums_tokens():
    runs = [
        _completed_run("claude-sonnet-5", input_tokens=100, output_tokens=20),
        _completed_run("claude-sonnet-5", input_tokens=50, output_tokens=10),
        _completed_run("claude-haiku-4-5", input_tokens=30, output_tokens=5),
    ]

    results = evaluate_models_across_runs(runs)

    assert set(results) == {"claude-sonnet-5", "claude-haiku-4-5"}
    sonnet = results["claude-sonnet-5"]
    assert sonnet.calls == 2
    assert sonnet.runs_seen == 2
    assert sonnet.total_input_tokens == 150
    assert sonnet.total_output_tokens == 30
    assert sonnet.success_rate == 1.0


def test_evaluate_models_computes_success_rate_across_completed_and_failed_runs():
    runs = [
        _completed_run("claude-sonnet-5", input_tokens=10, output_tokens=2),
        _failed_run("claude-sonnet-5"),
    ]

    results = evaluate_models_across_runs(runs)

    assert results["claude-sonnet-5"].runs_seen == 2
    assert results["claude-sonnet-5"].runs_completed == 1
    assert results["claude-sonnet-5"].success_rate == 0.5


def test_evaluate_models_leaves_cost_none_without_pricing_table():
    runs = [_completed_run("test-model", input_tokens=1000, output_tokens=100)]

    results = evaluate_models_across_runs(runs)

    assert results["test-model"].total_cost_usd is None


def test_evaluate_models_computes_cost_with_pricing_table():
    runs = [_completed_run("test-model", input_tokens=1_000_000, output_tokens=1_000_000)]

    results = evaluate_models_across_runs(runs, pricing_table={"test-model": (3.0, 15.0)})

    assert results["test-model"].total_cost_usd == 18.0


def test_evaluate_models_returns_empty_dict_for_no_generation_spans():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)

    results = evaluate_models_across_runs([(run, [{"name": "tool_call.completed"}])])

    assert results == {}
