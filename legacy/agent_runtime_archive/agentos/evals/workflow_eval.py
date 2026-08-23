# backend/agentos/evals/workflow_eval.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.workflows.models import Workflow, WorkflowStatus


class WorkflowEvalResult(BaseModel):
    completed: bool
    failed_step_name: str | None
    time_to_completion_seconds: float
    reached_approval_gate: bool


def evaluate_workflow(workflow: Workflow) -> WorkflowEvalResult:
    """Workflow Eval (blueprint §53), the metrics achievable purely from
    the Phase 8 Workflow object: completion, which step failed (if any),
    and wall-clock time to reach a terminal state. Retry count and cost
    aren't tracked by WorkflowEngine yet — later hardening. Approval wait
    duration needs the Approval object's own timestamps
    (created_at/decided_at, already on Phase 8's Approval) joined in by
    the caller, since Workflow itself only stores the approval id, not
    the Approval object.
    """
    return WorkflowEvalResult(
        completed=workflow.status == WorkflowStatus.COMPLETED,
        failed_step_name=workflow.failed_step_name,
        time_to_completion_seconds=(workflow.updated_at - workflow.created_at).total_seconds(),
        reached_approval_gate=workflow.had_approval_gate,
    )
