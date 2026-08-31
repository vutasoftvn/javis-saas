import pytest
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


@pytest.fixture
def built_app():
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
    return create_cosa_app(plane)


def test_all_conversation_routes_exist(built_app):
    """All conversation CRUD routes must exist post-split."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/conversations",
        "/agent/conversations/{conversation_id}",
        "/agent/conversations/{conversation_id}/messages",
        "/agent/conversations/{conversation_id}/artifacts",
        "/agent/sessions/{conversation_id}",
        "/agent/sessions/{conversation_id}/timeline",
        "/agent/sessions/{conversation_id}/artifacts",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"


def test_all_approval_routes_exist(built_app):
    """All approval routes must exist at /agent/workforce/approvals (consolidated)."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/workforce/approvals",
        "/agent/workforce/approvals/{approval_id}/decision",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after consolidation"


def test_old_approval_routes_removed(built_app):
    """Old /agent/approvals routes must NOT exist (moved to workforce)."""
    routes = set(built_app.openapi()["paths"].keys())
    old_routes = [
        "/agent/approvals",
        "/agent/approvals/{approval_id}/decision",
    ]
    for route in old_routes:
        assert route not in routes, f"Old route {route} still present after consolidation"


def test_all_knowledge_routes_exist(built_app):
    """All knowledge ingestion routes must exist."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/knowledge/uploads",
        "/agent/knowledge/uploads/{ingestion_id}/complete",
        "/agent/knowledge/ingestions/{ingestion_id}/review",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"


def test_all_connector_routes_exist(built_app):
    """All connector proxy routes must exist."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/connectors/install",
        "/agent/connectors/authorize",
        "/agent/connectors/grant",
        "/agent/connectors/revoke",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"


def test_all_schedule_routes_exist(built_app):
    """All schedule routes must exist."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/schedules",
        "/agent/schedules/{schedule_id}/run-now",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"
