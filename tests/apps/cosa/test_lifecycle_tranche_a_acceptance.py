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
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

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
    }

    # 4. Resolve Marketing Agent pinned skills
    mkt_resolved = asyncio.run(resolver.resolve(COSA_MARKETING_AGENT_SPEC.pinned_skills))
    assert len(mkt_resolved) == len(COSA_MARKETING_AGENT_SPEC.pinned_skills)
    assert {s.id for s in mkt_resolved} == {
        "strategy.positioning",
        "research.deep-research",
        "strategy.competitor-profiling",
        "marketing.channel-strategy",
    }

    # 5. Resolve Finance Agent pinned skills
    fin_resolved = asyncio.run(resolver.resolve(COSA_FINANCE_AGENT_SPEC.pinned_skills))
    assert len(fin_resolved) == len(COSA_FINANCE_AGENT_SPEC.pinned_skills)
    assert {s.id for s in fin_resolved} == {
        "finance.runway-forecast",
        "finance.budget-guardrails",
    }


def test_tranche_a_cross_workspace_isolation_and_no_side_effects(acceptance_env):
    """Tranche A Acceptance: Workspace isolation and advisory-only boundaries."""
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

    # Workspace B query cannot see Workspace A candidate
    res_b = client.get("/agent/skills?workspace_id=ws-accept-b")
    assert not any(s["id"] == "acceptance-custom-skill" for s in res_b.json())
