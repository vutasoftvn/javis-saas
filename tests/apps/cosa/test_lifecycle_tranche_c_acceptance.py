from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import InMemorySkillCandidateStore
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi.testclient import TestClient

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

pytestmark = pytest.mark.integration

from apps.cosa.agents.skillpack_seed import resolve_skillpacks_root
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec


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


def test_tranche_c_full_catalog_inventory_sync(acceptance_env):
    """Tranche C Acceptance: Catalog expands cleanly to all canonical skills with immutable definition hashes."""
    # 0. Derive deployment catalog identity from filesystem manifests
    root = resolve_skillpacks_root()
    manifest_paths = sorted(root.rglob("manifest.yaml"))
    deployment_specs = [parse_skillpack_spec(p.parent) for p in manifest_paths]

    deployment_ids = [spec.id for spec in deployment_specs]
    assert len(deployment_ids) == len(set(deployment_ids)), (
        f"Duplicate skill IDs in deployment manifests: {[i for i in deployment_ids if deployment_ids.count(i) > 1]}"
    )
    assert deployment_ids == sorted(deployment_ids), "Deployment manifest IDs must be deterministically sorted"

    deployment_identity_set = {
        (spec.id, spec.version, spec.compute_hash())
        for spec in deployment_specs
    }

    client: TestClient = acceptance_env["client"]

    # 1. Sync built-in skills
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-accept-c")
    assert res.status_code == 200
    sync_data = res.json()

    synced_items = sync_data["skills"]
    synced_ids = [item["skill_id"] for item in synced_items]
    assert len(synced_ids) == len(set(synced_ids)), "Sync response contains duplicate skill IDs"
    assert synced_ids == sorted(synced_ids), "Sync response skill IDs are not deterministically sorted"

    synced_identity_set = {
        (item["skill_id"], item["version"], item["definition_hash"])
        for item in synced_items
    }
    assert synced_identity_set == deployment_identity_set
    assert len(synced_identity_set) == len(deployment_identity_set)
    assert sync_data["synced_count"] == len(deployment_identity_set)

    # 2. List all skills in workspace
    res_list = client.get("/agent/skills?workspace_id=ws-accept-c")
    assert res_list.status_code == 200
    skills = res_list.json()

    listed_identity_set = {
        (skill["id"], skill["version"], skill["definition_hash"])
        for skill in skills
    }
    assert listed_identity_set == deployment_identity_set
    assert len(skills) == len(deployment_identity_set)

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
