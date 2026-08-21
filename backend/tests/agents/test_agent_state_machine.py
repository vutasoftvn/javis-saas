import pytest
from workforce.agents.governance.states import (
    AgentRunStatus,
    AgentPlanStatus,
    AgentPlanStepStatus,
    validate_run_transition,
    validate_plan_transition,
    validate_step_transition,
)


def test_agent_run_status_valid_transitions():
    assert validate_run_transition(AgentRunStatus.CREATED, AgentRunStatus.RUNNING) == "running"
    assert validate_run_transition("running", "waiting_approval") == "waiting_approval"
    assert validate_run_transition("waiting_approval", "running") == "running"
    assert validate_run_transition("running", "retrying") == "retrying"
    assert validate_run_transition("retrying", "fallback") == "fallback"
    assert validate_run_transition("fallback", "completed") == "completed"
    assert validate_run_transition("running", "failed_final") == "failed_final"


def test_agent_run_status_invalid_transitions():
    with pytest.raises(ValueError):
        validate_run_transition("completed", "running")

    with pytest.raises(ValueError):
        validate_run_transition("failed_final", "running")


def test_agent_plan_status_valid_transitions():
    assert validate_plan_transition(AgentPlanStatus.DRAFT, AgentPlanStatus.APPROVED) == "approved"
    assert validate_plan_transition("approved", "in_progress") == "in_progress"
    assert validate_plan_transition("in_progress", "completed") == "completed"
    assert validate_plan_transition("in_progress", "failed_final") == "failed_final"


def test_agent_plan_status_invalid_transitions():
    with pytest.raises(ValueError):
        validate_plan_transition("completed", "in_progress")

    with pytest.raises(ValueError):
        validate_plan_transition("failed_final", "draft")


def test_agent_plan_step_status_transitions():
    assert validate_step_transition("pending", "running") == "running"
    assert validate_step_transition("running", "waiting_approval") == "waiting_approval"
    assert validate_step_transition("running", "retrying") == "retrying"
    assert validate_step_transition("retrying", "fallback") == "fallback"
    assert validate_step_transition("fallback", "completed") == "completed"
    assert validate_step_transition("running", "failed_final") == "failed_final"

    with pytest.raises(ValueError):
        validate_step_transition("completed", "running")
