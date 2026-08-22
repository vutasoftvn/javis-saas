from __future__ import annotations

from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.models import StepStatus, Workflow, WorkflowStatus
from agentos.workflows.steps import WorkflowStep


class WorkflowEngine:
    """Runs a linear list of WorkflowStep (blueprint §47 example: Start →
    Agent Research → Human Approval → Business Write → Notify → End).
    Steps can mix deterministic, agent-reasoning, and approval-gate kinds
    freely — the engine only reacts to StepOutcome, not which kind it is.
    """

    async def start(self, name: str, steps: list[WorkflowStep], initial_state: dict) -> Workflow:
        workflow = Workflow(name=name, state=dict(initial_state))
        workflow.transition(WorkflowStatus.RUNNING)
        return await self._run_from(workflow, steps)

    async def resume(self, workflow: Workflow, steps: list[WorkflowStep]) -> Workflow:
        if workflow.status != WorkflowStatus.WAITING_APPROVAL:
            return workflow
        step = steps[workflow.current_step_index]
        if not isinstance(step, ApprovalGateStep):
            raise TypeError(f"Cannot resume: step {step.name!r} at the paused index is not an ApprovalGateStep")
        outcome = step.check_pending(workflow.pending_approval_id)
        if outcome.status == StepStatus.WAITING_APPROVAL:
            return workflow
        workflow.transition(WorkflowStatus.RUNNING)
        workflow.pending_approval_id = None
        if outcome.status == StepStatus.FAILED:
            workflow.error = outcome.error
            workflow.transition(WorkflowStatus.FAILED)
            return workflow
        workflow.state.update(outcome.updates)
        workflow.current_step_index += 1
        return await self._run_from(workflow, steps)

    async def _run_from(self, workflow: Workflow, steps: list[WorkflowStep]) -> Workflow:
        while workflow.current_step_index < len(steps):
            step = steps[workflow.current_step_index]
            outcome = await step.run(workflow.state)

            if outcome.status == StepStatus.WAITING_APPROVAL:
                workflow.pending_approval_id = outcome.approval_id
                workflow.transition(WorkflowStatus.WAITING_APPROVAL)
                return workflow

            if outcome.status == StepStatus.FAILED:
                workflow.error = outcome.error
                workflow.transition(WorkflowStatus.FAILED)
                return workflow

            workflow.state.update(outcome.updates)
            workflow.current_step_index += 1

        workflow.transition(WorkflowStatus.COMPLETED)
        return workflow
