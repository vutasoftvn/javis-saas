"""Test that worker automation handler uses composed workflow_orchestration engine and respects approval boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent.contracts.run import RunStatus
from agent.runs.repository import InMemoryRunRepository
from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import StepOutcome, StepStatus, Workflow, WorkflowStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from apps.cosa.worker.handlers import execute_automation_run_task


class SpyWorkflowEngine(WorkflowEngine):
    def __init__(self, gateway: Any = None) -> None:
        super().__init__(gateway=gateway)
        self.executed_specs: list[WorkflowSpec] = []

    async def execute_spec(
        self,
        spec: WorkflowSpec,
        initial_state: dict[str, Any],
        custom_step_builders: Any = None,
        workflow: Workflow | None = None,
    ) -> Workflow:
        self.executed_specs.append(spec)
        return await super().execute_spec(
            spec,
            initial_state=initial_state,
            custom_step_builders=custom_step_builders,
            workflow=workflow,
        )


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, request):
        rec = {
            "capability_id": getattr(request, "capability_id", None),
            "run_id": getattr(request, "run_id", None),
            "tool_call_id": getattr(request, "tool_call_id", None) or "call_x",
        }
        self.calls.append(rec)
        return SimpleNamespace(tool_call_id=rec["tool_call_id"], status="completed", output_payload={})


@pytest.mark.asyncio
async def test_worker_automation_invokes_composed_workflow_orchestration() -> None:
    gateway = RecordingGateway()
    spy_engine = SpyWorkflowEngine(gateway=gateway)
    orchestration = WorkflowOrchestration(
        gateway=gateway,
        workflow_engine=spy_engine,
        workflow_registry=None,
        approval_service=None,
    )

    plane = SimpleNamespace(
        run_repository=InMemoryRunRepository(),
        gateway=gateway,
        stream_event_repository=None,
        workflow_orchestration=orchestration,
    )

    payload = {
        "task_type": "automation_run",
        "run_id": "run_spy_test",
        "invocation_id": "inv-spy-1",
        "workspace_id": "ws-1",
        "automation_key": "operating.weekly-review",
        "revision": 1,
        "revision_hash": "r" * 64,
        "trigger_kind": "manual",
        "trigger_identity": "req-1",
        "correlation_id": "corr-1",
        "agent_profile": "operations",
        "configuration": {"projectId": "p1"},
    }

    await execute_automation_run_task(plane, SimpleNamespace(), payload)

    assert len(spy_engine.executed_specs) == 1
    assert spy_engine.executed_specs[0].id == "operating.weekly-review"

    run = await plane.run_repository.get_run("run_spy_test")
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_approval_gate_decision_does_not_schedule_generic_worker_outbox() -> None:
    """APPROVAL_GATE workflow steps remain library-only; generic workflow-gate decisions do NOT enqueue outbox actions."""
    from agent.capabilities.approval_service import DurableApprovalService

    repo = InMemoryRunRepository()
    approval_svc = DurableApprovalService(repo)

    gateway = RecordingGateway()
    engine = WorkflowEngine(gateway=gateway, approval_service=approval_svc)

    spec = WorkflowSpec(
        id="gate-spec",
        steps=[
            WorkflowStepSpec(
                id="gate-1",
                type=StepType.APPROVAL_GATE,
                action="test_action",
                subject_key="sub",
            )
        ],
    )

    wf = await engine.execute_spec(
        spec,
        initial_state={"workspace_id": "ws-1", "sub": "test_target"},
    )
    assert wf.status == WorkflowStatus.WAITING_APPROVAL
    assert wf.pending_approval_id is not None

    # Submit decision
    res = await approval_svc.submit_decision(
        approval_id=wf.pending_approval_id,
        reviewer="founder",
        approved=True,
    )
    assert res.status == "approved"

    # Generic approval gate does NOT emit approval_action_outbox records
    from datetime import UTC, datetime

    actions = await repo.claim_approval_actions(worker_id="w-1", now=datetime.now(UTC), limit=10)
    assert len(actions) == 0
