import pytest

from agent_core.workflows.models import (
    InvalidWorkflowTransition,
    StepOutcome,
    StepStatus,
    Workflow,
    WorkflowStatus,
)


def test_workflow_starts_pending():
    workflow = Workflow(name="onboarding")
    assert workflow.status == WorkflowStatus.PENDING
    assert workflow.is_terminal() is False


def test_workflow_valid_transition_to_running():
    workflow = Workflow(name="onboarding")
    workflow.transition(WorkflowStatus.RUNNING)
    assert workflow.status == WorkflowStatus.RUNNING


def test_workflow_invalid_transition_raises():
    workflow = Workflow(name="onboarding")
    with pytest.raises(InvalidWorkflowTransition):
        workflow.transition(WorkflowStatus.COMPLETED)


def test_workflow_completed_is_terminal():
    workflow = Workflow(name="onboarding")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.transition(WorkflowStatus.COMPLETED)
    assert workflow.is_terminal() is True


def test_workflow_can_resume_from_waiting_approval():
    workflow = Workflow(name="onboarding")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.transition(WorkflowStatus.WAITING_APPROVAL)
    workflow.transition(WorkflowStatus.RUNNING)
    assert workflow.status == WorkflowStatus.RUNNING


def test_step_outcome_defaults():
    outcome = StepOutcome(status=StepStatus.COMPLETED)
    assert outcome.updates == {}
    assert outcome.error is None


def test_workflow_new_fields_default_to_none_and_false():
    workflow = Workflow(name="onboarding")
    assert workflow.failed_step_name is None
    assert workflow.had_approval_gate is False
