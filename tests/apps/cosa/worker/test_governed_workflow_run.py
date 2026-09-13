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


def _build_plane(*, resolver=None, kernel=None):
    run_repository = InMemoryRunRepository()
    workflow_definition_repository = InMemoryWorkflowDefinitionRepository()
    approval_service = DurableApprovalService(run_repository)
    workflow_engine = WorkflowEngine(
        resolver=resolver,
        kernel=kernel,
        approval_service=approval_service,
    )
    workflow_orchestration = WorkflowOrchestration(
        gateway=None,
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
