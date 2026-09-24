from __future__ import annotations

import pytest
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.registry.publisher import publish_agent_spec
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.workflows.agent_spec_resolver import RegistryAgentSpecResolver
from agent.workflows.agent_step import AgentWorkflowStep
from agent.workflows.manifest import make_manifest
from agent.workflows.models import StepStatus

AGENT_SPEC = AgentSpec(
    id="agent.analyst", version="1.0.0", instructions="Phân tích báo cáo bán hàng."
).with_hash()
AGENT_HASH = AGENT_SPEC.definition_hash


async def spec_resolver() -> RegistryAgentSpecResolver:
    registry = InMemorySpecRegistryRepository()
    await publish_agent_spec(AGENT_SPEC, repository=registry, publisher="test")
    return RegistryAgentSpecResolver(registry)


class FakeKernel:
    """Conform `ExecutionKernel.run(request, spec)` — kernel một-đối-số sẽ TypeError."""

    def __init__(self, return_output: str = "agent completed task") -> None:
        self.request: RunRequest | None = None
        self.spec: AgentSpec | None = None
        self.return_output = return_output

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        self.request = request
        self.spec = spec
        return RunResult(
            run_id=request.run_id or "run_test",
            status=RunStatus.COMPLETED,
            final_output=self.return_output,
        )


class FakeResolver:
    def __init__(self, skills: dict | None = None, authority_data: dict | None = None) -> None:
        self.skills = skills or {}
        self.authority_data = authority_data or {
            "state": "ACTIVE",
            "workspaceId": "ws-1",
            "projectId": "p-1",
            "agentSpec": {
                "id": "agent.analyst",
                "version": "1.0.0",
                "definitionHash": AGENT_HASH,
            },
        }

    async def resolve_authority(self, workspace_id: str, project_id: str, deployment_id: str) -> dict:
        return self.authority_data

    async def resolve_skills(self, workspace_id: str, skill_refs: dict) -> dict:
        return self.skills


def state_for_manifest() -> dict:
    manifest = make_manifest(
        run_id="run-wf-1",
        workspace_id="ws-1",
        project_id="p-1",
        project_agent_deployment_id="dep_agent_123",
        pinned_agent_specs={
            "agent.analyst": {
                "version": "1.0.0",
                "definition_hash": AGENT_HASH,
            }
        },
    )
    return {
        "_manifest": manifest,
        "workspace_id": "ws-1",
        "project_id": "p-1",
        "task_prompt": "Analyze sales report",
    }


@pytest.mark.asyncio
async def test_agent_step_uses_manifest_pinned_spec_and_project_deployment():
    fake_kernel = FakeKernel()
    resolver = FakeResolver()
    step = AgentWorkflowStep(
        resolver=resolver, kernel=fake_kernel, spec_resolver=await spec_resolver()
    )

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.COMPLETED
    assert fake_kernel.request is not None
    assert fake_kernel.request.root_executable_ref.definition_hash == AGENT_HASH
    assert fake_kernel.request.workspace_id == "ws-1"
    assert fake_kernel.request.metadata["project_id"] == "p-1"
    # Kernel nhận AgentSpec đầy đủ đã resolve theo exact pin, không phải spec tổng hợp.
    assert fake_kernel.spec == AGENT_SPEC
    assert fake_kernel.spec.instructions == "Phân tích báo cáo bán hàng."


@pytest.mark.asyncio
async def test_agent_step_rejects_inactive_deployment():
    fake_kernel = FakeKernel()
    resolver = FakeResolver(authority_data={"state": "PAUSED", "workspaceId": "ws-1", "projectId": "p-1"})
    step = AgentWorkflowStep(
        resolver=resolver, kernel=fake_kernel, spec_resolver=await spec_resolver()
    )

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.FAILED
    assert "not active" in (outcome.error or "").lower()
    assert fake_kernel.request is None


@pytest.mark.asyncio
async def test_agent_step_fails_closed_without_live_authority_resolver():
    fake_kernel = FakeKernel()
    step = AgentWorkflowStep(resolver=None, kernel=fake_kernel, spec_resolver=await spec_resolver())

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.FAILED
    assert "authority" in (outcome.error or "").lower()
    assert fake_kernel.request is None


@pytest.mark.asyncio
async def test_agent_step_rejects_live_authority_that_drifted_from_manifest_pin():
    fake_kernel = FakeKernel()
    resolver = FakeResolver(
        authority_data={
            "state": "ACTIVE",
            "workspaceId": "ws-1",
            "projectId": "p-1",
            "agentSpec": {
                "id": "agent.analyst",
                "version": "2.0.0",
                "definitionHash": "sha256:drifted-agent-hash",
            },
        }
    )
    step = AgentWorkflowStep(
        resolver=resolver, kernel=fake_kernel, spec_resolver=await spec_resolver()
    )

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.FAILED
    assert "pin" in (outcome.error or "").lower()
    assert fake_kernel.request is None


@pytest.mark.asyncio
async def test_agent_step_fails_closed_without_exact_spec_resolver():
    fake_kernel = FakeKernel()
    step = AgentWorkflowStep(resolver=FakeResolver(), kernel=fake_kernel)

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.FAILED
    assert "AgentSpec resolver" in (outcome.error or "")
    assert fake_kernel.request is None


@pytest.mark.asyncio
async def test_agent_step_fails_when_registry_content_missing_for_pin():
    fake_kernel = FakeKernel()
    empty = RegistryAgentSpecResolver(InMemorySpecRegistryRepository())
    step = AgentWorkflowStep(resolver=FakeResolver(), kernel=fake_kernel, spec_resolver=empty)

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.FAILED
    assert "not published" in (outcome.error or "")
    assert fake_kernel.request is None


@pytest.mark.asyncio
async def test_agent_step_fails_when_registry_hash_differs_from_pin():
    registry = InMemorySpecRegistryRepository()
    drifted = AgentSpec(id="agent.analyst", version="1.0.0", instructions="khác").with_hash()
    await publish_agent_spec(drifted, repository=registry, publisher="test")
    fake_kernel = FakeKernel()
    step = AgentWorkflowStep(
        resolver=FakeResolver(),
        kernel=fake_kernel,
        spec_resolver=RegistryAgentSpecResolver(registry),
    )

    outcome = await step.run(state_for_manifest())

    assert outcome.status == StepStatus.FAILED
    assert "hash" in (outcome.error or "").lower()
    assert fake_kernel.request is None
