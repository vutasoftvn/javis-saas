import pytest

from agentos.core.models import AgentRun, AgentRunStatus, InvalidAgentRunTransition


def test_agent_run_starts_created():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    assert run.status == AgentRunStatus.CREATED
    assert run.is_terminal() is False


def test_agent_run_valid_transition_to_running():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    run.transition(AgentRunStatus.RUNNING)
    assert run.status == AgentRunStatus.RUNNING


def test_agent_run_invalid_transition_raises():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    with pytest.raises(InvalidAgentRunTransition):
        run.transition(AgentRunStatus.COMPLETED)


def test_agent_run_completed_is_terminal():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)
    assert run.is_terminal() is True
