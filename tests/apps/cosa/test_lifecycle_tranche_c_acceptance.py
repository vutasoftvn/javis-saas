from __future__ import annotations

from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

pytestmark = pytest.mark.integration

# 95 (pre-existing catalog baseline) + 22 real Tranche C growth/scale packs
# (Task 4/5/6: marketing, sales, finance, customer-success, operations, growth,
# strategy, people domains) - 3 duplicate legacy packs retired 2026-08-31
# (strategy.assumption-discovery, strategy.gate-evaluation, marketing.positioning
# — content merged into their governed canonical successors) = 114.
TRANCHE_C_CANONICAL_COUNT = 114


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {
        "project": {"id": "proj-c", "lifecycleStage": "P5_GROWTH"}
    }
    client.post.return_value = {"id": "task-c-001", "status": "todo"}
    return client


@pytest.fixture
def acceptance_env(mock_company_client):
    spec_registry = InMemorySpecRegistryRepository()
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=spec_registry,
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    application = create_cosa_app(plane=plane)
    application.state.skill_candidate_store = InMemorySkillCandidateStore()
    override_authenticated_identity(
        application,
        principal_id="user:founder_accept_c",
        platform_user_id="founder_accept_c",
        workspace_id="ws-accept-c",
    )
    client = TestClient(application)
    return {
        "app": application,
        "plane": plane,
        "client": client,
        "spec_registry": spec_registry,
        "company_client": mock_company_client,
    }


def test_tranche_c_full_95_catalog_inventory_sync(acceptance_env):
    """Tranche C Acceptance: Catalog expands cleanly to all 95 canonical skills with immutable definition hashes."""
    client: TestClient = acceptance_env["client"]

    # 1. Sync built-in skills
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-accept-c")
    assert res.status_code == 200
    sync_data = res.json()
    assert sync_data["synced_count"] == TRANCHE_C_CANONICAL_COUNT

    # 2. List all skills in workspace
    res_list = client.get("/agent/skills?workspace_id=ws-accept-c")
    assert res_list.status_code == 200
    skills = res_list.json()
    assert len(skills) == TRANCHE_C_CANONICAL_COUNT

    for skill in skills:
        assert skill["status"] == "PUBLISHED"
        assert skill["definition_hash"] != ""
        assert "project_stages" in skill
        assert "autonomy_ceiling" in skill
        assert "side_effect_class" in skill


@pytest.mark.asyncio
async def test_tranche_c_growth_scale_governance_invariants(acceptance_env):
    """Tranche C Acceptance: Full growth & scale governance invariants."""
    plane = acceptance_env["plane"]

    registered_cap_ids = {spec.id for spec in plane.capability_registry.list_specs()}

    # Invariant: Forbidden autonomous mutators are strictly absent
    assert "strategy.gate.pass" not in registered_cap_ids
    assert "strategy.pivot.execute" not in registered_cap_ids
    assert "engineering.deploy" not in registered_cap_ids
    assert "people.hire.execute" not in registered_cap_ids
    assert "legal.contract.sign" not in registered_cap_ids
