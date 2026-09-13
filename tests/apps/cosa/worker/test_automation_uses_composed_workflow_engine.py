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
async def test_approval_gate_decision_schedules_workflow_gate_outbox_action() -> None:
    """Task 11 (plan 2026-09-13-founder-configurable-agent-skill-workflow) —
    an approved APPROVAL_GATE decision DOES enqueue an outbox action, keyed by
    `subject_kind == "workflow_gate"` (not by an allow-listed `action` string,
    since workflow authors choose arbitrary action names). This is what lets
    `apps/cosa/worker/governed_workflow_run.py::schedule_workflow_gate_resume`
    actually reach a paused governed workflow run in production — before Task
    11, `ApprovalGateStep` approvals were asserted to NEVER reach the outbox
    (see git history), which meant an approved gate had no production trigger
    to resume the run it paused."""
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
        initial_state={"workspace_id": "ws-1", "sub": "test_target", "run_id": "run_gate_test"},
    )
    assert wf.status == WorkflowStatus.WAITING_APPROVAL
    assert wf.pending_approval_id is not None

    approval = await repo.get_approval(wf.pending_approval_id)
    # `run_id` rides in `requirement["run_id"]` (a plain JSONB column, not the
    # `run_id` column itself — the DB CHECK constraint
    # `chk_agent_approvals_binding` forbids a CHANGE_REQUEST approval from
    # carrying `run_id` directly).
    assert approval.run_id is None
    assert approval.requirement.get("run_id") == "run_gate_test"

    # Submit decision
    res = await approval_svc.submit_decision(
        approval_id=wf.pending_approval_id,
        reviewer="founder",
        approved=True,
    )
    assert res.status == "approved"

    # The approval gate's outbox action IS enqueued, carrying the run_id.
    from datetime import UTC, datetime

    actions = await repo.claim_approval_actions(worker_id="w-1", now=datetime.now(UTC), limit=10)
    assert len(actions) == 1
    assert actions[0].subject_kind == "workflow_gate"
