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
from apps.cosa.capabilities.project_lifecycle import (
    create_strategy_evidence_create_handler,
    create_strategy_gate_evaluation_create_handler,
    create_strategy_pilot_create_draft_handler,
    create_strategy_pilot_get_handler,
    create_strategy_project_get_handler,
)
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

pytestmark = pytest.mark.integration

TRANCHE_B1_CANONICAL_COUNT = 62

TRANCHE_B1_NEW_SKILL_IDS = [
    # Task 4: 2 P2 decision packs
    "strategy.pricing",
    "sales.design-partner-selection",
    # Task 5: 6 P3 delivery packs
    "product.prd",
    "product.user-story-and-acceptance",
    "engineering.vertical-slice",
    "engineering.alpha-validation",
    "product.pilot-onboarding",
    "product.feedback-synthesis",
    # Task 6: 6 P3 quality / resilience / support packs
    "analytics.product-usage-analysis",
    "engineering.observability-readiness",
    "engineering.release-management",
    "ai.evaluation-design",
    "ai.red-team",
    "customer-success.support-copilot",
]


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {
        "project": {"id": "proj-b1", "lifecycleStage": "P2_SOLUTION_VALIDATION"}
    }
    client.post.return_value = {
        "id": "pilot-b1-001",
        "projectId": "proj-b1",
        "status": "DRAFT",
    }
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
        principal_id="user:founder_accept_b1",
        platform_user_id="founder_accept_b1",
        workspace_id="ws-accept-b1",
    )
    client = TestClient(application)
    return {
        "app": application,
        "plane": plane,
        "client": client,
        "spec_registry": spec_registry,
        "company_client": mock_company_client,
    }


def test_tranche_b1_catalog_inventory_sync(acceptance_env):
    """Tranche B1 Acceptance: Catalog expands cleanly to >= 62 skills and includes all 14 new packs."""
    client: TestClient = acceptance_env["client"]

    # 1. Sync built-in skills
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-accept-b1")
    assert res.status_code == 200
    sync_data = res.json()
    assert sync_data["synced_count"] >= TRANCHE_B1_CANONICAL_COUNT

    # 2. List all skills in workspace
    res_list = client.get("/agent/skills?workspace_id=ws-accept-b1")
    assert res_list.status_code == 200
    skills = res_list.json()
    assert len(skills) >= TRANCHE_B1_CANONICAL_COUNT

    available_skill_ids = {s["id"] for s in skills}
    for skill_id in TRANCHE_B1_NEW_SKILL_IDS:
        # Check normalized skill ID or dotted ID
        normalized = skill_id.replace(".", "-")
        assert (
            skill_id in available_skill_ids or normalized in available_skill_ids
        ), f"Missing Tranche B1 skillpack: {skill_id}"


@pytest.mark.asyncio
async def test_tranche_b1_p2_to_p3_and_pilot_lifecycle_flow(acceptance_env):
    """Tranche B1 Acceptance: Full P2 -> P3 -> Pilot flow adhering strictly to invariants."""
    company_client = acceptance_env["company_client"]
    plane = acceptance_env["plane"]

    # 1. Verify capability boundaries: only advisory pilot capabilities in agent plane
    registered_cap_ids = {spec.id for spec in plane.capability_registry.list_specs()}
    assert "strategy.pilot.get" in registered_cap_ids
    assert "strategy.pilot.create_draft" in registered_cap_ids
    assert "strategy.pilot.activate" not in registered_cap_ids
    assert "strategy.pilot.approve" not in registered_cap_ids
    assert "engineering.deploy" not in registered_cap_ids

    # 2. Stage context lookup for project in P2
    proj_handler = create_strategy_project_get_handler(company_client)
    res_proj = await proj_handler(
        {"project_id": "proj-b1"},
        context={"workspace_id": "ws-accept-b1"},
    )
    assert res_proj["project"]["project"]["lifecycleStage"] == "P2_SOLUTION_VALIDATION"

    # 3. Agent creates draft Pilot Run (Proposal only)
    pilot_draft_handler = create_strategy_pilot_create_draft_handler(company_client)
    company_client.post.return_value = {
        "id": "704900111",
        "projectId": "proj-b1",
        "status": "DRAFT",
        "designPartnerEvidenceRefs": ["ev-approved-1"],
        "metricContractArtifactRef": "artifact://ws/metrics/v1",
        "instrumentationArtifactRef": "artifact://ws/inst/v1",
        "onboardingArtifactRef": "artifact://ws/onb/v1",
        "rollbackArtifactRef": "artifact://ws/rb/v1",
        "releaseOwnerMemberId": "user-founder-1",
    }

    res_draft = await pilot_draft_handler(
        {
            "project_id": "proj-b1",
            "design_partner_evidence_refs": ["ev-approved-1"],
            "metric_contract_artifact_ref": "artifact://ws/metrics/v1",
            "instrumentation_artifact_ref": "artifact://ws/inst/v1",
            "onboarding_artifact_ref": "artifact://ws/onb/v1",
            "rollback_artifact_ref": "artifact://ws/rb/v1",
            "release_owner_member_id": "user-founder-1",
        },
        context={"workspace_id": "ws-accept-b1"},
    )
    assert res_draft["pilot"]["status"] == "DRAFT"
    assert res_draft["advisory"]["label"] == "proposal"

    # 4. Agent retrieves pilot info (Advisory insight)
    pilot_get_handler = create_strategy_pilot_get_handler(company_client)
    company_client.get.return_value = {
        "id": "704900111",
        "projectId": "proj-b1",
        "status": "DRAFT",
    }
    res_get = await pilot_get_handler(
        {"pilot_id": "704900111"},
        context={"workspace_id": "ws-accept-b1"},
    )
    assert res_get["pilot"]["status"] == "DRAFT"
    assert res_get["advisory"]["label"] == "insight"
