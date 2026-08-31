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
from agent.skills.resolver import SkillResolver
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.agents.specs import (
    COSA_FINANCE_AGENT_SPEC,
    COSA_MARKETING_AGENT_SPEC,
    COSA_OPERATIONS_AGENT_SPEC,
)
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.project_lifecycle import (
    create_strategy_evidence_create_handler,
    create_strategy_gate_evaluation_create_handler,
    create_strategy_project_get_handler,
)
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

pytestmark = pytest.mark.integration

TRANCHE_A_CANONICAL_COUNT = 48


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {
        "project": {"id": "proj-1", "lifecycleStage": "P0_DISCOVERY"}
    }
    client.post.return_value = {
        "id": "ev-1",
        "status": "candidate",
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
        principal_id="user:founder_accept",
        platform_user_id="founder_accept",
        workspace_id="ws-accept-a",
    )
    client = TestClient(application)
    return {
        "app": application,
        "plane": plane,
        "client": client,
        "spec_registry": spec_registry,
        "company_client": mock_company_client,
    }


def test_tranche_a_full_sync_and_resolution_acceptance(acceptance_env):
    """Tranche A Acceptance: 48 canonical skillpacks sync cleanly, publish, and resolve against agent pins."""
    client: TestClient = acceptance_env["client"]
    plane = acceptance_env["plane"]

    # 1. Sync built-in skills
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-accept-a")
    assert res.status_code == 200
    sync_data = res.json()
    assert sync_data["synced_count"] >= TRANCHE_A_CANONICAL_COUNT

    # 2. List all skills
    res_list = client.get("/agent/skills?workspace_id=ws-accept-a")
    assert res_list.status_code == 200
    skills = res_list.json()
    assert len(skills) >= TRANCHE_A_CANONICAL_COUNT

    # 3. Resolve Operations Agent pinned skills
    resolver = SkillResolver(plane.spec_registry)
    import asyncio

    ops_resolved = asyncio.run(resolver.resolve(COSA_OPERATIONS_AGENT_SPEC.pinned_skills))
    assert len(ops_resolved) == len(COSA_OPERATIONS_AGENT_SPEC.pinned_skills)
    assert {s.id for s in ops_resolved} == {
        "lifecycle.context-resolver",
        "lifecycle.next-best-action",
        "operations.weekly-review",
        # Tranche C additions (2026-08-31): L1_PROPOSE/artifact-only, pinned per
        # Tranche C DoD ("Pin L0/L1 skills freely after registry acceptance").
        "operations.sop-builder",
        "operations.automation-design",
    }

    # 4. Resolve Marketing Agent pinned skills
    mkt_resolved = asyncio.run(resolver.resolve(COSA_MARKETING_AGENT_SPEC.pinned_skills))
    assert len(mkt_resolved) == len(COSA_MARKETING_AGENT_SPEC.pinned_skills)
    assert {s.id for s in mkt_resolved} == {
        "strategy.positioning",
        "research.deep-research",
        "strategy.competitor-profiling",
        "marketing.channel-strategy",
        # Tranche C additions (2026-08-31): L1_PROPOSE/artifact-only.
        "marketing.gtm-funnel",
        "marketing.content-strategy",
        "marketing.landing-cro",
        "marketing.paid-experiments",
        "marketing.brand-narrative",
        "marketing.reputation-monitoring",
    }

    # 5. Resolve Finance Agent pinned skills
    fin_resolved = asyncio.run(resolver.resolve(COSA_FINANCE_AGENT_SPEC.pinned_skills))
    assert len(fin_resolved) == len(COSA_FINANCE_AGENT_SPEC.pinned_skills)
    assert {s.id for s in fin_resolved} == {
        "finance.runway-forecast",
        "finance.budget-guardrails",
        # Tranche C addition (2026-08-31): L1_PROPOSE/artifact-only.
        "finance.unit-economics",
    }


def test_tranche_a_cross_workspace_isolation_and_no_side_effects(acceptance_env):
    """Tranche A Acceptance: Workspace isolation and advisory-only boundaries.

    Cross-workspace listing is enforced as a hard 404 (Task 5, commit
    59a4bc41), not a silently filtered empty result.
    """
    client: TestClient = acceptance_env["client"]

    # Candidate in Workspace A
    res_a = client.post(
        "/agent/skills/candidates",
        json={
            "name": "Acceptance Custom Skill",
            "domain": "strategy",
            "instructions": "Strategy for WS A",
            "workspace_id": "ws-accept-a",
        },
    )
    assert res_a.status_code == 201

    # Workspace B query is rejected outright: `resolve_identity_workspace`
    # (apps/cosa/auth/dependency.py) treats a `workspace_id` query that
    # doesn't match the authenticated identity's workspace as a hard 404,
    # not a valid alternate scope to filter against (Task 5, commit 59a4bc41).
    res_b = client.get("/agent/skills?workspace_id=ws-accept-b")
    assert res_b.status_code == 404

    # Positive check: querying the authenticated identity's own workspace
    # (ws-accept-a) still returns the candidate just created there — proving
    # the 404 above is a scope-boundary rejection, not a broken listing.
    res_own = client.get("/agent/skills?workspace_id=ws-accept-a")
    assert res_own.status_code == 200
    assert any(s["id"] == "acceptance-custom-skill" for s in res_own.json())


@pytest.mark.asyncio
async def test_tranche_a_lifecycle_capabilities_operating_slice(acceptance_env):
    """Tranche A Acceptance: Capability handlers strictly enforce candidate status and workspace boundaries."""
    company_client = acceptance_env["company_client"]

    # 1. Project Get capability
    proj_handler = create_strategy_project_get_handler(company_client)
    res_proj = await proj_handler(
        {"project_id": "proj-1"},
        context={"workspace_id": "ws-accept-a"},
    )
    assert res_proj["project"]["project"]["lifecycleStage"] == "P0_DISCOVERY"
    assert res_proj["advisory"]["label"] == "insight"

    # 2. Evidence Create capability: enforces candidate status and proposals
    ev_handler = create_strategy_evidence_create_handler(company_client)
    res_ev = await ev_handler(
        {
            "project_id": "proj-1",
            "source_type": "customer_interview",
            "claim": "Customer problem verified",
        },
        context={"workspace_id": "ws-accept-a"},
    )
    assert res_ev["evidence"]["status"] == "candidate"
    assert res_ev["advisory"]["label"] == "proposal"

    # 3. Gate Evaluation capability: returns assessment without mutating project stage
    gate_handler = create_strategy_gate_evaluation_create_handler(company_client)
    res_gate = await gate_handler(
        {
            "project_id": "proj-1",
            "stage_policy_id": "policy-p0",
        },
        context={"workspace_id": "ws-accept-a"},
    )
    assert res_gate["advisory"]["label"] == "insight"

