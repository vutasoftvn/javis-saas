from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from agent_core.governance.contracts import AutonomyLevel
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
from agent_core.workflows.approval_step import ApprovalGateStep
from agent_core.workflows.models import StepOutcome, StepStatus, Workflow, WorkflowStatus
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent_core.workflows.steps import CompensatingStep, DeterministicStep, WorkflowStep
from agent_core.workflows.tool_step import GatewayToolCallStep, ToolCallStep

__all__ = ["WorkflowEngine"]


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
        tool_registry: Any | None = None,
        gateway: Any | None = None,
        policy_engine: Any | None = None,
        approval_service: Any | None = None,
        governance_store: GovernanceStateStore | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._gateway = gateway
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._governance_store = governance_store or InMemoryGovernanceStateStore()

    # ------------------------------------------------------------------------
    # Linear Pipeline Execution
    # ------------------------------------------------------------------------

    async def start(
        self, name: str, steps: list[WorkflowStep], initial_state: dict[str, Any]
    ) -> Workflow:
        workflow = Workflow(name=name, state=dict(initial_state))
        workflow.transition(WorkflowStatus.RUNNING)
        return await self._run_from(workflow, steps)

    async def resume(self, workflow: Workflow, steps: list[WorkflowStep]) -> Workflow:
        if workflow.status != WorkflowStatus.WAITING_APPROVAL:
            return workflow
        step = steps[workflow.current_step_index]
        if not isinstance(step, ApprovalGateStep):
            raise TypeError(
                f"Cannot resume: step {step.name!r} at the paused index is not an ApprovalGateStep"
            )
        outcome = step.check_pending(workflow.pending_approval_id or "")
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
            if isinstance(step, CompensatingStep):
                try:
                    await step.compensate(workflow.state)
                except Exception as exc:
                    errors.append(f"{step.name}: {exc}")
        if errors:
            workflow.state["_compensation_errors"] = errors

    # ------------------------------------------------------------------------
    # Declarative DAG Spec Execution
    # ------------------------------------------------------------------------

    def build_steps_from_spec(
        self,
        spec: WorkflowSpec,
        custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]] | None = None,
    ) -> list[WorkflowStep]:
        builders = custom_step_builders or {}
        compiled_steps: list[WorkflowStep] = []

        for step_spec in spec.steps:
            if step_spec.id in builders:
                compiled_steps.append(builders[step_spec.id](step_spec))
                continue

            step_name = step_spec.name or step_spec.id

            if step_spec.type == StepType.TOOL_CALL:
                tool_name = step_spec.tool or step_spec.id
                if self._gateway:
                    compiled_steps.append(
                        GatewayToolCallStep(
                            name=step_name,
                            tool_name=tool_name,
                            gateway=self._gateway,
                            inputs=step_spec.inputs,
                            output_key=step_spec.output_key,
                        )
                    )
                elif self._tool_registry:
                    autonomy = AutonomyLevel.L3_AUTONOMOUS
                    if step_spec.autonomy_level:
                        autonomy = AutonomyLevel(step_spec.autonomy_level)
                    elif step_spec.permission_level:
                        with contextlib.suppress(ValueError):
                            autonomy = AutonomyLevel(step_spec.permission_level)
                    compiled_steps.append(
                        ToolCallStep(
                            name=step_name,
                            tool_name=tool_name,
                            tool_registry=self._tool_registry,
                            policy_engine=self._policy_engine,
                            approval_service=self._approval_service,
                            governance_store=self._governance_store,
                            inputs=step_spec.inputs,
                            output_key=step_spec.output_key,
                            autonomy_level=autonomy,
                        )
                    )
                else:
                    raise RuntimeError(
                        f"WorkflowEngine cannot compile TOOL_CALL step '{step_name}': no gateway or tool_registry provided"
                    )
            elif step_spec.type == StepType.APPROVAL_GATE:
                compiled_steps.append(
                    ApprovalGateStep(
                        name=step_name,
                        policy_engine=self._policy_engine,
                        approval_service=self._approval_service,
                        action=step_spec.action or step_name,
                        subject_key=step_spec.subject_key or "subject",
                    )
                )
            elif step_spec.type == StepType.DETERMINISTIC:

                async def noop_fn(s: dict[str, Any]) -> dict[str, Any]:
                    return {}

                compiled_steps.append(DeterministicStep(name=step_name, fn=noop_fn))
            else:

                async def fallback_fn(s: dict[str, Any]) -> dict[str, Any]:
                    return {}

                compiled_steps.append(DeterministicStep(name=step_name, fn=fallback_fn))

        return compiled_steps

    async def execute_spec(
        self,
        spec: WorkflowSpec,
        initial_state: dict[str, Any],
        custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]] | None = None,
        workflow: Workflow | None = None,
    ) -> Workflow:
        if workflow is None:
            workflow = Workflow(name=spec.name or spec.id, state=dict(initial_state))
            workflow.transition(WorkflowStatus.RUNNING)
        elif workflow.status == WorkflowStatus.WAITING_APPROVAL:
            workflow.transition(WorkflowStatus.RUNNING)
            workflow.pending_approval_id = None
        return await self._execute_dag(workflow, spec, custom_step_builders)

    async def resume_spec(
        self,
        workflow: Workflow,
        spec: WorkflowSpec,
        custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]] | None = None,
    ) -> Workflow:
        return await self.execute_spec(
            spec, initial_state={}, custom_step_builders=custom_step_builders, workflow=workflow
        )

    async def _execute_dag(
        self,
        workflow: Workflow,
        spec: WorkflowSpec,
        custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]] | None = None,
    ) -> Workflow:
        all_specs: dict[str, WorkflowStepSpec] = {s.id: s for s in spec.steps}
        built_steps = self.build_steps_from_spec(spec, custom_step_builders)
        steps_map: dict[str, WorkflowStep] = {
            s.id: step for s, step in zip(spec.steps, built_steps, strict=False)
        }

        compensation_targets: set[str] = {s.on_failure for s in spec.steps if s.on_failure}
        forward_steps = [s for s in spec.steps if s.id not in compensation_targets]

        if not forward_steps:
            workflow.error = (
                "workflow has no forward steps (empty spec or all-compensation spec "
                "bypassed schema validation)"
            )
            workflow.transition(WorkflowStatus.FAILED)
            return workflow

        completed_set: set[str] = set(workflow.completed_steps)
        failed_set: set[str] = set()

        while len([s for s in forward_steps if s.id in completed_set]) < len(forward_steps):
            ready_step_ids = [
                s.id
                for s in forward_steps
                if s.id not in completed_set
                and s.id not in failed_set
                and all(dep in completed_set for dep in s.depends_on)
            ]

            if not ready_step_ids:
                # Không còn step nào "ready" nhưng vẫn còn forward step chưa
                # hoàn tất — chỉ xảy ra nếu spec có cycle/dependency treo đã
                # lọt qua WorkflowSpec._validate_dag (vd spec dựng bằng
                # model_construct hoặc bị mutate sau khi validate). Đây là
                # fail-safe tầng engine — không được rơi xuống COMPLETED.
                stuck_ids = [
                    s.id
                    for s in forward_steps
                    if s.id not in completed_set and s.id not in failed_set
                ]
                workflow.failed_step_name = stuck_ids[0] if stuck_ids else None
                workflow.error = (
                    f"workflow DAG stuck: {len(stuck_ids)} step(s) can never become ready "
                    f"(cycle or dangling dependency bypassed schema validation): {stuck_ids}"
                )
                workflow.transition(WorkflowStatus.FAILED)
                return workflow

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
                            any_failure = True
                            break

                    any_failure = True
                    break

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
            incomplete = [s.id for s in forward_steps if s.id not in completed_set]
            if incomplete:
                # Không bao giờ nên xảy ra (vòng lặp while chỉ thoát tự nhiên khi
                # completed_set phủ hết forward_steps) — giữ assertion làm lưới an
                # toàn cuối cùng thay vì âm thầm báo COMPLETED sai.
                workflow.failed_step_name = incomplete[0]
                workflow.error = (
                    f"workflow reached exit with incomplete forward step(s): {incomplete}"
                )
                workflow.transition(WorkflowStatus.FAILED)
                return workflow
            workflow.transition(WorkflowStatus.COMPLETED)
        return workflow
