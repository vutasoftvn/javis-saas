"""Task 11 (plan 2026-09-13-founder-configurable-agent-skill-workflow) —
worker dispatch of `governed_workflow_run` scheduler tasks, checkpoint resume,
and live Company deployment authority re-checked on every AGENT effect
(including on resume, not just at run start)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from agent.capabilities.approval_service import DurableApprovalService
from agent.contracts.run import RunStatus
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.workflows.engine import WorkflowEngine
from agent.workflows.manifest import make_manifest
from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec

from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from apps.cosa.worker.governed_workflow_run import (
    execute_governed_workflow_run,
    execute_governed_workflow_run_task,
)
from apps.cosa.worker.main import dispatch_one_task

WORKSPACE_ID = "ws-governed-1"
PROJECT_ID = "proj-governed-1"
DEPLOYMENT_ID = "dep-governed-1"
AGENT_SPEC_ID = "agentspec-governed-1"


class FakeDeploymentResolver:
    """Test double for `CompanyDeploymentAuthorityResolver` — lets a test flip
    a deployment PAUSED to prove `AgentWorkflowStep` re-checks live authority
    on every call, not only once at run start."""

    def __init__(self) -> None:
        self.state = "ACTIVE"

    async def resolve_authority(
        self, workspace_id: str, project_id: str, deployment_id: str
    ) -> dict:
        return {
            "state": self.state,
            "workspaceId": workspace_id,
            "projectId": project_id,
            "agentSpec": {"id": AGENT_SPEC_ID, "version": "1.0.0", "definitionHash": "hash1"},
        }

    def pause(self) -> None:
        self.state = "PAUSED"


class FakeKernel:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self, request):
        self.calls += 1
        return SimpleNamespace(status="COMPLETED", final_output={"ok": True})


class FakeGateway:
    """Test double for `CapabilityGateway` — used to prove a TOOL_CALL step's
    live deployment-authority check happens BEFORE the gateway is ever
    invoked, not just before the workflow reports failure."""

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, request):
        self.calls += 1
        return SimpleNamespace(
            status="completed",
            output_payload={"ok": True},
            wait_descriptor=None,
            error_message=None,
        )


def _one_step_spec(workflow_id: str) -> WorkflowSpec:
    """A single DETERMINISTIC step spec — enough to exercise dispatch wiring
    without needing a kernel/resolver."""
    from agent.workflows.deterministic_handlers import WHITELISTED_DETERMINISTIC_HANDLERS

    handler_name = next(iter(WHITELISTED_DETERMINISTIC_HANDLERS))
    return WorkflowSpec(
        id=workflow_id,
        name="Single Step Governed Workflow",
        version="1.0.0",
        steps=[WorkflowStepSpec(id="only_step", type=StepType.DETERMINISTIC, handler=handler_name)],
    ).with_hash()


def _approval_then_agent_spec(workflow_id: str) -> WorkflowSpec:
    """APPROVAL_GATE -> AGENT — pauses for approval, then executes a governed
    AGENT effect on resume."""
    return WorkflowSpec(
        id=workflow_id,
        name="Approval Then Agent Governed Workflow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="approve",
                type=StepType.APPROVAL_GATE,
                subject_key="workspace_id",
                action="run_governed_effect",
            ),
            WorkflowStepSpec(
                id="agent_step",
                type=StepType.AGENT,
                depends_on=["approve"],
                project_agent_deployment_id=DEPLOYMENT_ID,
                output_key="agent_output",
            ),
        ],
    ).with_hash()


def _approval_then_tool_call_spec(workflow_id: str) -> WorkflowSpec:
    """APPROVAL_GATE -> TOOL_CALL — proves `GatewayToolCallStep` re-checks live
    deployment authority on resume, not just `AgentWorkflowStep`."""
    return WorkflowSpec(
        id=workflow_id,
        name="Approval Then Tool Call Governed Workflow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="approve",
                type=StepType.APPROVAL_GATE,
                subject_key="workspace_id",
                action="run_governed_tool_call",
            ),
            WorkflowStepSpec(
                id="tool_step",
                type=StepType.TOOL_CALL,
                tool="noop.tool",
                depends_on=["approve"],
                output_key="tool_output",
            ),
        ],
    ).with_hash()


def _approval_only_spec(workflow_id: str) -> WorkflowSpec:
    """A single APPROVAL_GATE step — isolates the approval-continuation live
    authority check itself (no downstream AGENT/TOOL_CALL effect involved)."""
    return WorkflowSpec(
        id=workflow_id,
        name="Approval Only Governed Workflow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="approve",
                type=StepType.APPROVAL_GATE,
                subject_key="workspace_id",
                action="run_governed_approval_only",
            ),
        ],
    ).with_hash()


def _build_plane(*, resolver=None, kernel=None, gateway=None):
    run_repository = InMemoryRunRepository()
    workflow_definition_repository = InMemoryWorkflowDefinitionRepository()
    approval_service = DurableApprovalService(run_repository)
    workflow_engine = WorkflowEngine(
        resolver=resolver,
        kernel=kernel,
        gateway=gateway,
        approval_service=approval_service,
    )
    workflow_orchestration = WorkflowOrchestration(
        gateway=gateway,
        workflow_engine=workflow_engine,
        workflow_registry=None,
        approval_service=approval_service,
        workflow_definition_repository=workflow_definition_repository,
    )
    return SimpleNamespace(
        run_repository=run_repository,
        approval_service=approval_service,
        workflow_definition_repository=workflow_definition_repository,
        workflow_orchestration=workflow_orchestration,
        stream_event_repository=InMemoryRunStreamEventRepository(),
        project_activity_service=None,
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
    )


def _payload(run_id: str, workflow_asset_id: str, spec: WorkflowSpec, **over) -> dict:
    base = {
        "task_type": "governed_workflow_run",
        "run_id": run_id,
        "workspace_id": WORKSPACE_ID,
        "project_id": PROJECT_ID,
        "workflow_binding_id": "binding-1",
        "workflow_asset_id": workflow_asset_id,
        "workflow_version": "1.0.0",
        "workflow_definition_hash": spec.definition_hash,
        "correlation_id": "corr-1",
    }
    base.update(over)
    return base


class _FakeTask:
    def __init__(self, task_id: str, input_payload: dict) -> None:
        self.task_id = task_id
        self.claim_token = f"claim_{task_id}"
        self.input_payload = input_payload


@pytest.mark.asyncio
async def test_worker_dispatches_governed_workflow_task_to_real_handler():
    workflow_id = f"wf_dispatch_{uuid.uuid4().hex[:8]}"
    spec = _one_step_spec(workflow_id)
    plane = _build_plane()
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    payload = _payload(run_id, workflow_id, spec)
    task = _FakeTask(f"task_{uuid.uuid4().hex[:8]}", payload)

    await dispatch_one_task(plane, task)

    run = await plane.run_repository.get_run(run_id)
    assert run is not None
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_duplicate_dispatch_of_same_run_id_does_not_re_execute():
    workflow_id = f"wf_dup_{uuid.uuid4().hex[:8]}"
    spec = _one_step_spec(workflow_id)
    plane = _build_plane()
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    payload = _payload(run_id, workflow_id, spec)

    first = await execute_governed_workflow_run_task(plane, None, payload)
    assert first.status == "completed"

    manifest_after_first = await plane.run_repository.get_workflow_manifest(run_id)
    second = await execute_governed_workflow_run_task(plane, None, payload)
    assert second.status == "completed"
    manifest_after_second = await plane.run_repository.get_workflow_manifest(run_id)

    # Insert-once manifest: a duplicate dispatch never resolves a second one.
    assert manifest_after_first.manifest_hash == manifest_after_second.manifest_hash


@pytest.mark.asyncio
async def test_revoked_project_agent_blocks_effect_after_resume():
    workflow_id = f"wf_revoke_{uuid.uuid4().hex[:8]}"
    spec = _approval_then_agent_spec(workflow_id)
    resolver = FakeDeploymentResolver()
    kernel = FakeKernel()
    plane = _build_plane(resolver=resolver, kernel=kernel)
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    manifest = await plane.run_repository.create_workflow_manifest(
        make_manifest(
            run_id=run_id,
            project_id=PROJECT_ID,
            workspace_id=WORKSPACE_ID,
            workflow_asset_id=workflow_id,
            workflow_version="1.0.0",
            workflow_definition_hash=spec.definition_hash,
            project_agent_deployment_id=DEPLOYMENT_ID,
            pinned_agent_specs={AGENT_SPEC_ID: {"version": "1.0.0", "definition_hash": "hash1"}},
        )
    )

    # 1. First execution pauses at the APPROVAL_GATE step.
    first = await execute_governed_workflow_run(plane, manifest)
    assert first.status == "waiting_approval"
    assert kernel.calls == 0

    run = await plane.run_repository.get_run(run_id)
    assert run.status == RunStatus.WAITING_APPROVAL

    # 2. Approve while the deployment is still active.
    pending = await plane.run_repository.list_pending_approvals(workspace_id=WORKSPACE_ID)
    assert len(pending) == 1
    await plane.approval_service.submit_decision(
        approval_id=pending[0].approval_id, reviewer="founder_user", approved=True
    )

    # 3. Revoke (pause) the project agent deployment BEFORE resume runs the AGENT effect.
    resolver.pause()

    # 4. Resume — must re-check live Company authority, not reuse the earlier ACTIVE result.
    second = await execute_governed_workflow_run(plane, manifest)
    assert second.status == "failed"
    assert kernel.calls == 0

    run_after = await plane.run_repository.get_run(run_id)
    assert run_after.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_resume_with_active_deployment_completes_the_agent_effect():
    workflow_id = f"wf_resume_ok_{uuid.uuid4().hex[:8]}"
    spec = _approval_then_agent_spec(workflow_id)
    resolver = FakeDeploymentResolver()
    kernel = FakeKernel()
    plane = _build_plane(resolver=resolver, kernel=kernel)
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    manifest = await plane.run_repository.create_workflow_manifest(
        make_manifest(
            run_id=run_id,
            project_id=PROJECT_ID,
            workspace_id=WORKSPACE_ID,
            workflow_asset_id=workflow_id,
            workflow_version="1.0.0",
            workflow_definition_hash=spec.definition_hash,
            project_agent_deployment_id=DEPLOYMENT_ID,
            pinned_agent_specs={AGENT_SPEC_ID: {"version": "1.0.0", "definition_hash": "hash1"}},
        )
    )

    first = await execute_governed_workflow_run(plane, manifest)
    assert first.status == "waiting_approval"

    pending = await plane.run_repository.list_pending_approvals(workspace_id=WORKSPACE_ID)
    await plane.approval_service.submit_decision(
        approval_id=pending[0].approval_id, reviewer="founder_user", approved=True
    )

    second = await execute_governed_workflow_run(plane, manifest)
    assert second.status == "completed"
    assert kernel.calls == 1


@pytest.mark.asyncio
async def test_revoked_project_agent_blocks_tool_call_effect_after_resume():
    """Same shape as `test_revoked_project_agent_blocks_effect_after_resume`
    but for a TOOL_CALL step — `GatewayToolCallStep` must also re-check live
    Company deployment authority on resume, not only `AgentWorkflowStep`."""
    workflow_id = f"wf_revoke_tool_{uuid.uuid4().hex[:8]}"
    spec = _approval_then_tool_call_spec(workflow_id)
    resolver = FakeDeploymentResolver()
    gateway = FakeGateway()
    plane = _build_plane(resolver=resolver, gateway=gateway)
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    manifest = await plane.run_repository.create_workflow_manifest(
        make_manifest(
            run_id=run_id,
            project_id=PROJECT_ID,
            workspace_id=WORKSPACE_ID,
            workflow_asset_id=workflow_id,
            workflow_version="1.0.0",
            workflow_definition_hash=spec.definition_hash,
            project_agent_deployment_id=DEPLOYMENT_ID,
        )
    )

    first = await execute_governed_workflow_run(plane, manifest)
    assert first.status == "waiting_approval"
    assert gateway.calls == 0

    pending = await plane.run_repository.list_pending_approvals(workspace_id=WORKSPACE_ID)
    assert len(pending) == 1
    await plane.approval_service.submit_decision(
        approval_id=pending[0].approval_id, reviewer="founder_user", approved=True
    )

    resolver.pause()

    second = await execute_governed_workflow_run(plane, manifest)
    assert second.status == "failed"
    assert gateway.calls == 0

    run_after = await plane.run_repository.get_run(run_id)
    assert run_after.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_revoked_project_agent_blocks_approval_continuation_itself():
    """The approval-gate continuation itself (resuming past an already-
    APPROVED gate) must re-check live Company deployment authority — a gate
    approved while ACTIVE must not be treated as actionable once the
    deployment has since been paused/revoked, even before any downstream
    AGENT/TOOL_CALL effect would have run."""
    workflow_id = f"wf_revoke_gate_{uuid.uuid4().hex[:8]}"
    spec = _approval_only_spec(workflow_id)
    resolver = FakeDeploymentResolver()
    plane = _build_plane(resolver=resolver)
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    manifest = await plane.run_repository.create_workflow_manifest(
        make_manifest(
            run_id=run_id,
            project_id=PROJECT_ID,
            workspace_id=WORKSPACE_ID,
            workflow_asset_id=workflow_id,
            workflow_version="1.0.0",
            workflow_definition_hash=spec.definition_hash,
            project_agent_deployment_id=DEPLOYMENT_ID,
        )
    )

    first = await execute_governed_workflow_run(plane, manifest)
    assert first.status == "waiting_approval"

    pending = await plane.run_repository.list_pending_approvals(workspace_id=WORKSPACE_ID)
    assert len(pending) == 1
    await plane.approval_service.submit_decision(
        approval_id=pending[0].approval_id, reviewer="founder_user", approved=True
    )

    resolver.pause()

    second = await execute_governed_workflow_run(plane, manifest)
    assert second.status == "failed"

    run_after = await plane.run_repository.get_run(run_id)
    assert run_after.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_approved_workflow_gate_is_actually_relayed_to_a_resume_task():
    """End-to-end through the REAL production wiring — not calling
    `execute_governed_workflow_run` a second time by hand: approve the
    `workflow_gate`, run `relay_approved_actions` (outbox -> scheduled
    `approval_action` task), dispatch that task through `dispatch_one_task`
    (routes to `_dispatch_approval_action_task` -> `schedule_workflow_gate_resume`),
    then dispatch the `governed_workflow_run` task it schedules and confirm the
    run actually completes."""
    from apps.cosa.worker.approval_actions import relay_approved_actions

    workflow_id = f"wf_gate_relay_{uuid.uuid4().hex[:8]}"
    spec = _approval_then_agent_spec(workflow_id)
    resolver = FakeDeploymentResolver()
    kernel = FakeKernel()
    plane = _build_plane(resolver=resolver, kernel=kernel)
    await plane.workflow_definition_repository.save_definition(spec, workspace_id=WORKSPACE_ID)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    manifest = await plane.run_repository.create_workflow_manifest(
        make_manifest(
            run_id=run_id,
            project_id=PROJECT_ID,
            workspace_id=WORKSPACE_ID,
            workflow_asset_id=workflow_id,
            workflow_version="1.0.0",
            workflow_definition_hash=spec.definition_hash,
            project_agent_deployment_id=DEPLOYMENT_ID,
            pinned_agent_specs={AGENT_SPEC_ID: {"version": "1.0.0", "definition_hash": "hash1"}},
        )
    )

    first = await execute_governed_workflow_run(plane, manifest)
    assert first.status == "waiting_approval"

    pending = await plane.run_repository.list_pending_approvals(workspace_id=WORKSPACE_ID)
    assert len(pending) == 1
    approval = pending[0]
    # run_id is encoded in subject_ref, not the run_id column (see
    # schedule_workflow_gate_resume's docstring for why).
    assert approval.subject_ref.startswith(f"{run_id}:")

    await plane.approval_service.submit_decision(
        approval_id=approval.approval_id, reviewer="founder_user", approved=True
    )

    # 1. Outbox relay picks up the approved workflow_gate action.
    scheduled_approval_ids = await relay_approved_actions(plane, worker_id="worker-1")
    assert approval.approval_id in scheduled_approval_ids

    # 2. Poll + dispatch that `approval_action` task through the real worker path.
    tasks = await plane.scheduler.poll_due_tasks(worker_id="worker-1", limit=10)
    approval_action_tasks = [
        t for t in tasks if t.input_payload.get("subject_kind") == "workflow_gate"
    ]
    assert len(approval_action_tasks) == 1
    await dispatch_one_task(plane, approval_action_tasks[0])

    # 3. That handler must have scheduled a fresh `governed_workflow_run` task
    #    for the exact same run_id.
    resume_tasks = await plane.scheduler.poll_due_tasks(worker_id="worker-1", limit=10)
    governed_tasks = [
        t for t in resume_tasks if t.input_payload.get("task_type") == "governed_workflow_run"
    ]
    assert len(governed_tasks) == 1
    assert governed_tasks[0].input_payload["run_id"] == run_id

    # 4. Dispatching THAT task must actually resume and complete the run.
    await dispatch_one_task(plane, governed_tasks[0])
    run_after = await plane.run_repository.get_run(run_id)
    assert run_after.status == RunStatus.COMPLETED
    assert kernel.calls == 1
