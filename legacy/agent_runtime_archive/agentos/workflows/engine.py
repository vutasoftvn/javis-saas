from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionLevel, PolicyEngine
from agentos.tools.registry import ToolRegistry
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.models import StepOutcome, StepStatus, Workflow, WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agentos.workflows.steps import WorkflowStep
from agentos.workflows.tool_step import ToolCallStep


class WorkflowEngine:
    """Workflow execution engine supporting both:
    1. Linear step pipelines (backward-compatible `start` and `resume`).
    2. Declarative DAG execution (`execute_spec` and `resume_spec`) with
       parallel branch execution, automatic compensation (`on_failure`),
       strict governance for `tool_call` steps, and checkpointing for safe resumption.
    """

    def __init__(
        self,
        *,
        tool_registry: Optional[ToolRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
        governance_store: Optional[GovernanceStateStore] = None,
    ) -> None:
        self._tool_registry = tool_registry or ToolRegistry()
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._governance_store = governance_store or InMemoryGovernanceStateStore()

    # ------------------------------------------------------------------------
    # Linear Pipeline Execution (Existing API)
    # ------------------------------------------------------------------------

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
        workflow.completed_steps.append(step.name)
        workflow.checkpoints[step.name] = dict(workflow.state)
        workflow.current_step_index += 1
        return await self._run_from(workflow, steps)

    async def _run_from(self, workflow: Workflow, steps: list[WorkflowStep]) -> Workflow:
        while workflow.current_step_index < len(steps):
            step = steps[workflow.current_step_index]
            outcome = await step.run(workflow.state)

            if outcome.status == StepStatus.WAITING_APPROVAL:
                workflow.pending_approval_id = outcome.approval_id
                workflow.had_approval_gate = True
                workflow.checkpoints[step.name] = dict(workflow.state)
                workflow.transition(WorkflowStatus.WAITING_APPROVAL)
                return workflow

            if outcome.status == StepStatus.FAILED:
                workflow.failed_step_name = step.name
                workflow.error = outcome.error
                workflow.transition(WorkflowStatus.FAILED)
                await self._run_compensations(workflow, steps)
                return workflow

            workflow.state.update(outcome.updates)
            workflow.completed_steps.append(step.name)
            workflow.checkpoints[step.name] = dict(workflow.state)
            workflow.current_step_index += 1

        workflow.transition(WorkflowStatus.COMPLETED)
        return workflow

    async def _run_compensations(self, workflow: Workflow, steps: list[WorkflowStep]) -> None:
        errors: list[str] = []
        for step in reversed(steps[: workflow.current_step_index]):
            compensate = getattr(step, "compensate", None)
            if compensate is None:
                continue
            try:
                await compensate(workflow.state)
            except Exception as exc:
                errors.append(f"{step.name}: {exc}")
        if errors:
            workflow.state["_compensation_errors"] = errors

    # ------------------------------------------------------------------------
    # Declarative DAG Execution (Phase 8B)
    # ------------------------------------------------------------------------

    def _build_executable_step(
        self,
        step_spec: WorkflowStepSpec,
        custom_step_builders: Optional[dict[str, Callable[[WorkflowStepSpec], WorkflowStep]]] = None,
    ) -> WorkflowStep:
        if custom_step_builders and step_spec.id in custom_step_builders:
            return custom_step_builders[step_spec.id](step_spec)

        if step_spec.type == StepType.TOOL_CALL:
            if not step_spec.tool:
                raise ValueError(f"Step {step_spec.id} of type tool_call must specify a 'tool'")
            step_kwargs: dict[str, Any] = {}
            if step_spec.permission_level:
                step_kwargs["agent_permission_level"] = PermissionLevel(step_spec.permission_level)
            return ToolCallStep(
                name=step_spec.id,
                tool_name=step_spec.tool,
                tool_registry=self._tool_registry,
                policy_engine=self._policy_engine,
                approval_service=self._approval_service,
                governance_store=self._governance_store,
                inputs=step_spec.inputs,
                output_key=step_spec.output_key or step_spec.id,
                **step_kwargs,
            )

        raise NotImplementedError(
            f"Step type '{step_spec.type}' requires a custom step builder or implementation."
        )

    def build_steps_from_spec(
        self,
        spec: WorkflowSpec,
        custom_step_builders: Optional[dict[str, Callable[[WorkflowStepSpec], WorkflowStep]]] = None,
    ) -> list[WorkflowStep]:
        """Build danh sách WorkflowStep thực thi được từ 1 WorkflowSpec khai
        báo — public vì WorkflowDefinitionRegistry cần gọi lại đúng logic
        này khi resolve steps cho 1 version đã pin, thay vì tự giữ 1
        Callable Python tách biệt (bug gốc khiến version history và spec
        khai báo không nối với nhau — xem
        COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md)."""
        return [self._build_executable_step(s, custom_step_builders) for s in spec.steps]

    async def execute_spec(
        self,
        spec: WorkflowSpec,
        initial_state: dict[str, Any],
        custom_step_builders: Optional[dict[str, Callable[[WorkflowStepSpec], WorkflowStep]]] = None,
        workflow: Optional[Workflow] = None,
    ) -> Workflow:
        """Executes a declarative WorkflowSpec graph respecting `depends_on`,
        running independent steps concurrently in parallel waves, checkpointing
        after each step, and handling step-level compensation via `on_failure`.
        """
        if workflow is None:
            workflow = Workflow(name=spec.name or spec.id, state=dict(initial_state))
            workflow.transition(WorkflowStatus.RUNNING)
        elif workflow.status == WorkflowStatus.WAITING_APPROVAL:
            workflow.transition(WorkflowStatus.RUNNING)

        all_specs: dict[str, WorkflowStepSpec] = {s.id: s for s in spec.steps}
        built_steps = self.build_steps_from_spec(spec, custom_step_builders)
        steps_map: dict[str, WorkflowStep] = {s.id: step for s, step in zip(spec.steps, built_steps)}

        compensation_targets: set[str] = {s.on_failure for s in spec.steps if s.on_failure}
        forward_steps = [s for s in spec.steps if s.id not in compensation_targets]

        # Determine step dependencies and execute in topological waves
        completed_set: set[str] = set(workflow.completed_steps)
        failed_set: set[str] = set()

        while len([s for s in forward_steps if s.id in completed_set]) < len(forward_steps):
            # Find all forward steps whose dependencies are satisfied and not yet completed
            ready_step_ids = [
                s.id
                for s in forward_steps
                if s.id not in completed_set
                and s.id not in failed_set
                and all(dep in completed_set for dep in s.depends_on)
            ]

            if not ready_step_ids:
                # No steps ready: either everything is done, or dependencies failed / deadlock
                break

            # Run all ready steps concurrently in this wave
            async def run_single_step(step_id: str) -> tuple[str, StepOutcome]:
                step = steps_map[step_id]
                outcome = await step.run(workflow.state)
                return step_id, outcome

            wave_results = await asyncio.gather(*(run_single_step(sid) for sid in ready_step_ids))

            any_failure = False
            any_paused = False

            for step_id, outcome in wave_results:
                workflow.step_outcomes[step_id] = outcome
                step_spec = all_specs[step_id]

                if outcome.status == StepStatus.WAITING_APPROVAL:
                    workflow.pending_approval_id = outcome.approval_id
                    workflow.had_approval_gate = True
                    workflow.checkpoints[step_id] = dict(workflow.state)
                    workflow.transition(WorkflowStatus.WAITING_APPROVAL)
                    any_paused = True
                    break

                if outcome.status == StepStatus.FAILED:
                    failed_set.add(step_id)
                    workflow.failed_step_name = step_id
                    workflow.error = outcome.error

                    # Check if step has an on_failure compensation step configured
                    if step_spec.on_failure and step_spec.on_failure in steps_map:
                        comp_step_id = step_spec.on_failure
                        comp_step = steps_map[comp_step_id]
                        comp_outcome = await comp_step.run(workflow.state)
                        workflow.step_outcomes[comp_step_id] = comp_outcome
                        if comp_outcome.status == StepStatus.COMPLETED:
                            workflow.state.update(comp_outcome.updates)
                            workflow.completed_steps.append(comp_step_id)
                            workflow.checkpoints[comp_step_id] = dict(workflow.state)
                            workflow.state["_compensated_step"] = step_id
                            # Compensation succeeded
                            any_failure = True
                            break

                    any_failure = True
                    break

                # Step completed successfully
                workflow.state.update(outcome.updates)
                workflow.completed_steps.append(step_id)
                completed_set.add(step_id)
                workflow.checkpoints[step_id] = dict(workflow.state)

            if any_paused:
                return workflow

            if any_failure:
                workflow.transition(WorkflowStatus.FAILED)
                return workflow

        if workflow.status == WorkflowStatus.RUNNING:
            workflow.transition(WorkflowStatus.COMPLETED)
        return workflow
