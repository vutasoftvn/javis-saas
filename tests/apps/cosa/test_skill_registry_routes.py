from __future__ import annotations

from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.identity import PinnedSkillRef
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_core.skills.candidate_store import InMemorySkillCandidateStore
from agent_core.skills.resolver import SkillResolver
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {}
    client.post.return_value = {}
    return client


@pytest.fixture
def setup_env(mock_company_client):
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
        principal_id="user:founder",
        platform_user_id="founder",
        workspace_id="ws-1",
    )
    client = TestClient(application)
    return {
        "app": application,
        "plane": plane,
        "client": client,
    }


def test_skill_registry_lifecycle_and_sync(setup_env):
    """Verify complete Skill Registry lifecycle: list -> sync-built-in -> candidate -> evaluate -> promote -> deprecate."""
    client: TestClient = setup_env["client"]

    # 1. Initial GET /agent/skills is empty
    res = client.get("/agent/skills?workspace_id=ws-1")
    assert res.status_code == 200
    assert res.json() == []

    # 2. POST /agent/skills/sync-built-in
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-1")
    assert res.status_code == 200
    sync_data = res.json()
    assert sync_data["synced_count"] >= 18
    assert len(sync_data["skills"]) == sync_data["synced_count"]
    sample_skill = sync_data["skills"][0]
    assert "skill_id" in sample_skill
    assert "definition_hash" in sample_skill
    assert sample_skill["published"] is True

    # 3. Second sync-built-in is idempotent
    res2 = client.post("/agent/skills/sync-built-in?workspace_id=ws-1")
    assert res2.status_code == 200
    assert res2.json()["synced_count"] == sync_data["synced_count"]

    # 4. GET /agent/skills after sync returns published skills
    res_list = client.get("/agent/skills?workspace_id=ws-1")
    assert res_list.status_code == 200
    skills = res_list.json()
    assert len(skills) >= 18
    mkt_positioning = next((s for s in skills if s["id"] == "marketing.positioning"), None)
    assert mkt_positioning is not None
    assert mkt_positioning["status"] == "PUBLISHED"
    assert mkt_positioning["domain"] == "marketing"
    assert mkt_positioning["definition_hash"] != ""

    # 5. Create Candidate
    cand_payload = {
        "name": "Custom Email Drafter",
        "domain": "marketing",
        "instructions": "Draft cold outbound emails following B2B SaaS best practices.",
        "description": "Cold email generation candidate.",
        "tool_permissions": ["web.search"],
        "workspace_id": "ws-1",
    }
    res_cand = client.post("/agent/skills/candidates", json=cand_payload)
    assert res_cand.status_code == 201
    cand_data = res_cand.json()
    assert cand_data["skill_id"] == "custom-email-drafter"
    assert cand_data["status"] == "CANDIDATE"

    # 6. Evaluate Candidate
    res_eval = client.post(
        "/agent/skills/custom-email-drafter/evaluate",
        json={"eval_score": 0.92, "eval_details": {"tests_passed": 12, "total": 12}},
    )
    assert res_eval.status_code == 200
    assert res_eval.json()["eval_score"] == 0.92
    assert res_eval.json()["status"] == "EVALUATED"

    # 7. Promote without approved_by or approval_reason fails with 422
    res_promote_fail = client.post(
        "/agent/skills/custom-email-drafter/promote",
        json={"approved_by": "", "approval_reason": ""},
    )
    assert res_promote_fail.status_code == 422

    # 8. Promote with approval succeeds
    res_promote = client.post(
        "/agent/skills/custom-email-drafter/promote",
        json={
            "approved_by": "founder_admin",
            "approval_reason": "Evaluated at 92% benchmark, passed cold outbound quality test",
        },
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["status"] == "PUBLISHED"
    assert res_promote.json()["approved_by"] == "founder_admin"

    # 9. Deprecate Skill
    res_dep = client.post(
        "/agent/skills/custom-email-drafter/deprecate",
        json={"reason": "Superceded by v2"},
    )
    assert res_dep.status_code == 200
    assert res_dep.json()["status"] == "RETIRED"

    # 10. Record Feedback
    res_fb = client.post(
        "/agent/skills/custom-email-drafter/feedback",
        json={"success": True, "rating": 5, "notes": "Great copy generated"},
    )
    assert res_fb.status_code == 200
    assert res_fb.json()["recorded"] is True


def test_skill_candidate_workspace_isolation(setup_env):
    """Verify that candidates created in workspace-A are isolated from workspace-B."""
    client: TestClient = setup_env["client"]

    # Create candidate in workspace-A
    res = client.post(
        "/agent/skills/candidates",
        json={
            "name": "Secret Strategy Pack",
            "domain": "strategy",
            "instructions": "Confidential playbook.",
            "workspace_id": "workspace-A",
        },
    )
    assert res.status_code == 201

    # Workspace-A sees it
    res_a = client.get("/agent/skills?workspace_id=workspace-A")
    assert any(s["id"] == "secret-strategy-pack" for s in res_a.json())

    # Workspace-B does not see it
    res_b = client.get("/agent/skills?workspace_id=workspace-B")
    assert not any(s["id"] == "secret-strategy-pack" for s in res_b.json())


@pytest.mark.asyncio
async def test_skill_resolver_against_synced_skills(setup_env):
    """Verify that SkillResolver.resolve works with definition_hash pinning on synced skills."""
    client: TestClient = setup_env["client"]
    plane = setup_env["plane"]

    # Sync built-in skills
    res = client.post("/agent/skills/sync-built-in?workspace_id=ws-1")
    assert res.status_code == 200

    # Get marketing.positioning spec record from registry
    record = await plane.spec_registry.get("skill", "marketing.positioning", "1.1.0")
    assert record is not None

    resolver = SkillResolver(plane.spec_registry)

    # 1. Resolve with correct definition_hash succeeds
    pinned_ref = PinnedSkillRef(
        skill_id="marketing.positioning",
        version="1.1.0",
        definition_hash=record.definition_hash,
    )
    resolved = await resolver.resolve([pinned_ref])
    assert len(resolved) == 1
    assert resolved[0].id == "marketing.positioning"

    # 2. Resolve with forged / wrong definition_hash raises SKILL_RESOLUTION_ERROR
    bad_ref = PinnedSkillRef(
        skill_id="marketing.positioning",
        version="1.1.0",
        definition_hash="tampered_hash_value_123456",
    )
    with pytest.raises(AgentRuntimeError) as exc_info:
        await resolver.resolve([bad_ref])
    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR
