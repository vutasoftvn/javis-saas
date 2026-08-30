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
    create_analytics_metric_contract_get_handler,
    create_analytics_pmf_scoreboard_get_handler,
    create_analytics_pmf_scoreboard_propose_handler,
    create_strategy_evidence_create_handler,
    create_strategy_gate_evaluation_create_handler,
    create_strategy_pilot_create_draft_handler,
    create_strategy_pilot_get_handler,
    create_strategy_project_get_handler,
)
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

pytestmark = pytest.mark.integration

TRANCHE_B2_CANONICAL_COUNT = 72

TRANCHE_B2_NEW_SKILL_IDS = [
    # Task 5: 6 P4 decision packs
    "discovery.affinity-synthesis",
    "strategy.pivot-persevere",
    "analytics.pmf-survey",
    "analytics.pmf-scoreboard",
    "product.outcome-roadmap",
    "product.backlog-prioritization",
    # Task 6: 4 P4 learning / health packs
    "product.continuous-discovery",
    "growth.experimentation-system",
    "customer-success.health-scoring",
    "customer-success.churn-analysis",
]


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {
        "project": {"id": "proj-b2", "lifecycleStage": "P4_PILOT_PMF"}
    }
    client.post.return_value = {
        "id": "run-b2-001",
        "projectId": "proj-b2",
        "result": "PROMISING",
        "calculationHash": "sha256_b2_calc_hash",
        "scoreComponents": [],
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
        principal_id="user:founder_accept_b2",
        platform_user_id="founder_accept_b2",
        workspace_id="ws-accept-b2",
    )
    client = TestClient(application)
    return {
        "app": application,
        "plane": plane,
        "client": client,
        "spec_registry": spec_registry,
        "company_client": mock_company_client,
    }


def test_tranche_b2_catalog_inventory_sync(acceptance_env):
    """Tranche B2 Acceptance: Catalog expands cleanly to 72 skills and includes all 10 new P4 packs."""
    client: TestClient = acceptance_env["client"]

    # 1. Sync built-in skills
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-accept-b2")
    assert res.status_code == 200
    sync_data = res.json()
    assert sync_data["synced_count"] >= TRANCHE_B2_CANONICAL_COUNT

    # 2. List all skills in workspace
    res_list = client.get("/agent/skills?workspace_id=ws-accept-b2")
    assert res_list.status_code == 200
    skills = res_list.json()
    assert len(skills) >= TRANCHE_B2_CANONICAL_COUNT

    available_skill_ids = {s["id"] for s in skills}
    for skill_id in TRANCHE_B2_NEW_SKILL_IDS:
        normalized = skill_id.replace(".", "-")
        assert (
            skill_id in available_skill_ids or normalized in available_skill_ids
        ), f"Missing Tranche B2 skillpack: {skill_id}"


@pytest.mark.asyncio
async def test_tranche_b2_pmf_and_advisory_flow(acceptance_env):
    """Tranche B2 Acceptance: PMF Scoreboard & Advisory Flow without auto-transition mutators."""
    company_client = acceptance_env["company_client"]
    plane = acceptance_env["plane"]

    # 1. Verify capability boundaries: advisory only
    registered_cap_ids = {spec.id for spec in plane.capability_registry.list_specs()}
    assert "analytics.metric_contract.get" in registered_cap_ids
    assert "analytics.pmf_scoreboard.get" in registered_cap_ids
    assert "analytics.pmf_scoreboard.propose" in registered_cap_ids

    assert "strategy.pivot.execute" not in registered_cap_ids
    assert "analytics.metric_snapshot.ingest" not in registered_cap_ids
    assert "strategy.gate.pass" not in registered_cap_ids

    # 2. Query Metric Contracts
    metric_handler = create_analytics_metric_contract_get_handler(company_client)
    company_client.get.return_value = {
        "items": [
            {
                "id": "contract-1",
                "metricKey": "activation_rate",
                "displayName": "Activation Rate",
                "status": "ACTIVE",
            }
        ]
    }
    res_contracts = await metric_handler(
        {"project_id": "proj-b2"},
        context={"workspace_id": "ws-accept-b2"},
    )
    assert len(res_contracts["contracts"]) == 1
    assert res_contracts["advisory"]["label"] == "insight"

    # 3. Query PMF Scoreboard
    pmf_get_handler = create_analytics_pmf_scoreboard_get_handler(company_client)
    company_client.get.return_value = {
        "items": [
            {
                "id": "run-b2-100",
                "result": "PROMISING",
                "calculationHash": "sha256_hash_123",
                "missingDataFlags": [],
                "reliabilityFlags": [],
                "inputSnapshotIds": ["snap-1"],
            }
        ]
    }
    res_pmf = await pmf_get_handler(
        {"project_id": "proj-b2"},
        context={"workspace_id": "ws-accept-b2"},
    )
    assert len(res_pmf["runs"]) == 1
    assert res_pmf["advisory"]["label"] == "insight"

    # 4. Propose PMF Advisory Memo
    pmf_prop_handler = create_analytics_pmf_scoreboard_propose_handler(company_client)
    res_prop = await pmf_prop_handler(
        {"project_id": "proj-b2"},
        context={"workspace_id": "ws-accept-b2"},
    )
    assert res_prop["status"] == "completed"
    assert res_prop["classification"] == "PROMISING"
    assert res_prop["memo"]["decision"].startswith("Tín hiệu PMF khả quan")
    assert res_prop["memo"]["human_owner"] == "Founder / Product DRI"
    assert res_prop["advisory"]["label"] == "proposal"
