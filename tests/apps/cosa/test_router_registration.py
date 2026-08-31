from __future__ import annotations

from apps.cosa.api.app import create_cosa_app
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)
from agent.runs.repository import InMemoryRunRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.artifacts import InMemoryArtifactRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.vault.repository import InMemoryVaultRepository
from agent_testkit.fake_sdk_model import FakeSDKModel


def test_all_expected_routes_are_registered():
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
    app = create_cosa_app(plane)

    routes = set(app.openapi()["paths"].keys())
    assert "/agent/conversations" in routes
    assert "/agent/approvals" in routes
    assert "/agent/sessions/{conversation_id}" in routes
    assert "/agent/schedules" in routes
    assert "/agent/vault/documents" in routes
    assert "/agent/workforce/runs" in routes
    assert "/agent/settings/skills" in routes
