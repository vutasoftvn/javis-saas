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
