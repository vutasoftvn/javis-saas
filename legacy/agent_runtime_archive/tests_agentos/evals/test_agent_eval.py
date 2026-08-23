# backend/tests/agentos/evals/test_agent_eval.py
from agentos.core.models import AgentRun, AgentRunStatus
from agentos.evals.agent_eval import evaluate_agent_run


def test_evaluate_agent_run_marks_goal_completion_true_when_completed():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)

    result = evaluate_agent_run(run, [{"name": "tool_call.completed"}])

    assert result.goal_completion is True
    assert result.tool_calls_made == 1


def test_evaluate_agent_run_marks_goal_completion_false_when_failed():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.FAILED)

    result = evaluate_agent_run(run, [])

    assert result.goal_completion is False


def test_evaluate_agent_run_carries_optional_human_acceptance():
    run = AgentRun(agent_key="a1", goal="g")

    result = evaluate_agent_run(run, [], human_acceptance=True)

    assert result.human_acceptance is True
