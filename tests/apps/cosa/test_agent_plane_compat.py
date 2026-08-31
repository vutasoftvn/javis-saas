"""Test compatibility layer: new narrower services work alongside old attributes."""

from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.vault.repository import InMemoryVaultRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.composition.compliance_coordination import ComplianceCoordination
from apps.cosa.composition.run_execution_service import RunExecutionService
from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)


def test_run_execution_service_accessible_via_property():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )

    # Old direct access still works
    assert plane.kernel is not None
    assert plane.repository is not None
    assert plane.scheduler is not None

    # New narrower interface works
    run_exec = plane.run_execution
    assert isinstance(run_exec, RunExecutionService)
    assert run_exec.kernel is plane.kernel
    assert run_exec.repository is plane.repository
    assert run_exec.scheduler is plane.scheduler


def test_workflow_orchestration_accessible_via_property():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )

    # Old direct access still works
    assert plane.gateway is not None
    assert plane.workflow_engine is not None

    # New narrower interface works
    wf_orch = plane.workflow_orchestration
    assert isinstance(wf_orch, WorkflowOrchestration)
    assert wf_orch.gateway is plane.gateway
    assert wf_orch.workflow_engine is plane.workflow_engine


def test_compliance_coordination_accessible_via_property():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )

    # Old direct access still works
    assert plane.policy_engine is not None
    assert plane.governance_store is not None

    # New narrower interface works
    comp_coord = plane.compliance_coordination
    assert isinstance(comp_coord, ComplianceCoordination)
    assert comp_coord.policy_engine is plane.policy_engine
    assert comp_coord.governance_store is plane.governance_store
