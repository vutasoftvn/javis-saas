from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi.testclient import TestClient

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    # Default overview mock returning an active AI_AGENT member 999
    client.get.return_value = {
        "workspaceId": "ws-test",
        "members": [
            {
                "id": "999",
                "memberType": "AI_AGENT",
                "status": "active",
                "roleTitle": "Operations Agent",
            },
            {
                "id": "888",
                "memberType": "HUMAN",
                "status": "active",
                "roleTitle": "Founder",
            },
            {
                "id": "777",
                "memberType": "AI_AGENT",
                "status": "suspended",
                "roleTitle": "Suspended Agent",
            },
        ],
    }
    return client


@pytest.fixture
def app_env(mock_company_client):
    repo = InMemoryWorkforceRepository()
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        workforce_repository=repo,
    )
    application = create_cosa_app(plane=plane)
    client = TestClient(application)
    return {"app": application, "plane": plane, "client": client, "repo": repo, "company": mock_company_client}


def test_assignment_requires_founder_role(app_env):
    client = app_env["client"]
    app = app_env["app"]
    override_authenticated_identity(
        app,
        principal_id="user:member_1",
        platform_user_id="member_1",
        workspace_id="ws-test",
        role_id="member",
    )

    response = client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "campaign_planner", "company_workforce_member_id": "999"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "founder authority required"


def test_assignment_requires_active_company_ai_workforce_member(app_env):
    client = app_env["client"]
    app = app_env["app"]
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )

    # Missing target
    resp_missing = client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "campaign_planner"},
    )
    assert resp_missing.status_code == 422
    assert resp_missing.json()["detail"] == "active AI workforce member is required"

    # Target is HUMAN (888)
    resp_human = client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "campaign_planner", "company_workforce_member_id": "888"},
    )
    assert resp_human.status_code == 422
    assert resp_human.json()["detail"] == "active AI workforce member is required"

    # Target is SUSPENDED (777)
    resp_suspended = client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "campaign_planner", "company_workforce_member_id": "777"},
    )
    assert resp_suspended.status_code == 422
    assert resp_suspended.json()["detail"] == "active AI workforce member is required"

    # Target does not exist (99999)
    resp_not_found = client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "campaign_planner", "company_workforce_member_id": "99999"},
    )
    assert resp_not_found.status_code == 422
    assert resp_not_found.json()["detail"] == "active AI workforce member is required"


def test_assignment_succeeds_with_active_company_ai_member(app_env):
    client = app_env["client"]
    app = app_env["app"]
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )

    response = client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "campaign_planner", "company_workforce_member_id": "999"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["functional_key"] == "campaign_planner"
    assert data["company_workforce_member_id"] == "999"
    assert data["status"] == "ACTIVE"


def test_promote_requests_approval_not_direct_publish(app_env):
    client = app_env["client"]
    app = app_env["app"]
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )

    # 1. Create candidate
    res_c = client.post(
        "/agent/skills/candidates",
        json={
            "name": "Outreach Writer",
            "domain": "sales",
            "instructions": "Write sales outreach",
            "workspace_id": "ws-test",
        },
    )
    assert res_c.status_code == 201
    skill_id = res_c.json()["skill_id"]
    candidate_id = res_c.json()["candidate_id"]

    # 2. Evaluate
    res_e = client.post(f"/agent/skills/{skill_id}/evaluate", json={})
    assert res_e.status_code == 200
    assert res_e.json()["status"] == "EVALUATED"

    # 3. Promote -> returns 202 PENDING_APPROVAL
    res_p = client.post(f"/agent/skills/{skill_id}/promote", json={})
    assert res_p.status_code == 202
    data = res_p.json()
    assert data["status"] == "PENDING_APPROVAL"
    assert data["action"] == "promote_skill_candidate"
    assert data["candidate_id"] == candidate_id
    assert data["definition_hash"].startswith("sha256:")

    # 4. Check candidate status in candidate store is NOT mutated to PUBLISHED
    res_cand = client.get(f"/agent/skills/{skill_id}")
    assert res_cand.status_code == 200
    assert res_cand.json()["status"] == "EVALUATED"


def test_only_founder_decides_promotion(app_env):
    client = app_env["client"]
    app = app_env["app"]
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )

    res_c = client.post(
        "/agent/skills/candidates",
        json={"name": "Auto Close", "domain": "sales", "instructions": "Close deals", "workspace_id": "ws-test"},
    )
    skill_id = res_c.json()["skill_id"]
    client.post(f"/agent/skills/{skill_id}/evaluate", json={})
    res_p = client.post(f"/agent/skills/{skill_id}/promote", json={})
    approval_id = res_p.json()["approval_id"]

    # Repeated request returns the same approval_id
    res_p2 = client.post(f"/agent/skills/{skill_id}/promote", json={})
    assert res_p2.status_code == 202
    assert res_p2.json()["approval_id"] == approval_id

    # Admin cannot decide (403)
    override_authenticated_identity(
        app,
        principal_id="user:admin_1",
        platform_user_id="admin_1",
        workspace_id="ws-test",
        role_id="admin",
    )
    res_dec_admin = client.post(
        f"/agent/workforce/approvals/{approval_id}/decision",
        json={"approved": True},
    )
    assert res_dec_admin.status_code == 403

    # Founder can decide (200)
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )
    res_dec_founder = client.post(
        f"/agent/workforce/approvals/{approval_id}/decision",
        json={"approved": True},
    )
    assert res_dec_founder.status_code == 200
    dec_data = res_dec_founder.json()["data"]
    assert dec_data["status"] == "approved"
    assert dec_data["binding_kind"] == "CHANGE_REQUEST"
    assert dec_data["dispatch_state"] == "outbox_pending"


def test_promote_skill_negatives(app_env):
    client = app_env["client"]
    app = app_env["app"]
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )

    # 1. Foreign workspace 404
    override_authenticated_identity(
        app,
        principal_id="user:founder_other",
        platform_user_id="founder_other",
        workspace_id="ws-other",
        role_id="founder",
    )
    res_foreign = client.post("/agent/skills/non-existent-skill/promote", json={})
    assert res_foreign.status_code == 404

    # Back to ws-test
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-test",
        role_id="founder",
    )

    # 2. Not evaluated candidate returns 400
    res_c = client.post(
        "/agent/skills/candidates",
        json={"name": "Unevaluated Skill", "domain": "sales", "instructions": "x", "workspace_id": "ws-test"},
    )
    cand_id = res_c.json()["skill_id"]
    res_un = client.post(f"/agent/skills/{cand_id}/promote", json={})
    assert res_un.status_code == 400
    assert "chưa được server đánh giá" in res_un.json()["detail"].lower()

    # 3. Request body with extra fields returns 422
    res_422 = client.post(
        f"/agent/skills/{cand_id}/promote",
        json={"approved_by": "founder", "approval_reason": "test"},
    )
    assert res_422.status_code == 422
