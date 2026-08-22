# backend/tests/agentos/evals/test_workflow_eval.py
from agentos.evals.workflow_eval import evaluate_workflow
from agentos.workflows.models import Workflow, WorkflowStatus


def test_evaluate_workflow_completed_without_approval_gate():
    workflow = Workflow(name="flow")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.transition(WorkflowStatus.COMPLETED)

    result = evaluate_workflow(workflow)

    assert result.completed is True
    assert result.failed_step_name is None
    assert result.reached_approval_gate is False
    assert result.time_to_completion_seconds >= 0.0


def test_evaluate_workflow_failed_reports_the_failing_step():
    workflow = Workflow(name="flow")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.failed_step_name = "business-write"
    workflow.transition(WorkflowStatus.FAILED)

    result = evaluate_workflow(workflow)

    assert result.completed is False
    assert result.failed_step_name == "business-write"


def test_evaluate_workflow_reports_approval_gate_was_reached():
    workflow = Workflow(name="flow")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.had_approval_gate = True
    workflow.transition(WorkflowStatus.COMPLETED)

    result = evaluate_workflow(workflow)

    assert result.reached_approval_gate is True
