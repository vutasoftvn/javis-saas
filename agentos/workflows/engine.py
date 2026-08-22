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
            workflow.failed_step_name = step.name
            workflow.error = outcome.error
            workflow.transition(WorkflowStatus.FAILED)
            await self._run_compensations(workflow, steps)
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
                workflow.had_approval_gate = True
                workflow.transition(WorkflowStatus.WAITING_APPROVAL)
                return workflow

            if outcome.status == StepStatus.FAILED:
                workflow.failed_step_name = step.name
                workflow.error = outcome.error
                workflow.transition(WorkflowStatus.FAILED)
                await self._run_compensations(workflow, steps)
                return workflow

            workflow.state.update(outcome.updates)
            workflow.current_step_index += 1

        workflow.transition(WorkflowStatus.COMPLETED)
        return workflow

    async def _run_compensations(self, workflow: Workflow, steps: list[WorkflowStep]) -> None:
        """Rollback best-effort (blueprint §47 "compensation"): mọi step
        trước step vừa fail đều đã hoàn thành (current_step_index chỉ tăng
        sau một step COMPLETED), nên compensate chúng theo thứ tự ngược lại
        thứ tự hoàn thành. Lỗi trong chính compensate được ghi lại, không
        raise — 1 rollback lỗi không được chặn các rollback khác chạy.
        """
        errors: list[str] = []
        for step in reversed(steps[: workflow.current_step_index]):
            compensate = getattr(step, "compensate", None)
            if compensate is None:
                continue
            try:
                await compensate(workflow.state)
            except Exception as exc:  # noqa: BLE001 — cố tình bắt rộng: lỗi rollback không được làm crash engine
                errors.append(f"{step.name}: {exc}")
        if errors:
            workflow.state["_compensation_errors"] = errors
