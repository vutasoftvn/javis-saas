"""Workspace isolation cho skill workspace_custom (Task 9).

Kiểm tra:
- Skill custom đã promote của ws-a KHÔNG hiển thị với ws-b (không publish vào
  shared registry — không leak qua catalogue built-in).
- Client không được tự ghi eval_score (evaluation phải server-attested).
- Founder không được promote candidate tham chiếu capability chưa đăng ký.
"""

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

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.api.app import create_cosa_app
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


@pytest.fixture
def app():
    company_client = AsyncMock(spec=CompanyServiceClient)
    company_client.get.return_value = {}
    company_client.post.return_value = {}
    plane = build_cosa_agent_plane(
        company_client=company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    application = create_cosa_app(plane=plane)
    application.state.skill_candidate_store = InMemorySkillCandidateStore()
    return application


def _authenticate(application, workspace_id: str) -> None:
    override_authenticated_identity(
        application,
        principal_id=f"user:{workspace_id}",
        platform_user_id=f"founder-{workspace_id}",
        workspace_id=workspace_id,
        role_id="founder",
    )


def _create_and_promote(client: TestClient, workspace_id: str, skill_name: str) -> str:
    res = client.post(
        "/agent/skills/candidates",
        json={
            "name": skill_name,
            "domain": "sales",
            "instructions": "Draft outreach for the workspace.",
            "workspace_id": workspace_id,
        },
    )
    assert res.status_code == 201, res.text
    skill_id = res.json()["skill_id"]

    res_eval = client.post(f"/agent/skills/{skill_id}/evaluate", json={})
    assert res_eval.status_code == 200, res_eval.text
    assert res_eval.json()["eval_score"] == 1.0

    res_promote = client.post(
        f"/agent/skills/{skill_id}/promote",
        json={"approved_by": "founder", "approval_reason": "server-attested pass"},
    )
    assert res_promote.status_code == 200, res_promote.text
    return skill_id


def _contains_skill(client: TestClient, workspace_id: str, skill_id: str) -> bool:
    res = client.get(f"/agent/skills?workspace_id={workspace_id}")
    assert res.status_code == 200, res.text
    return any(item["id"] == skill_id for item in res.json())


def test_promoted_workspace_custom_skill_is_invisible_to_another_workspace(app) -> None:
    client = TestClient(app)

    _authenticate(app, "ws-a")
    skill_id = _create_and_promote(client, "ws-a", "A-only skill")

    _authenticate(app, "ws-b")
    assert not _contains_skill(client, "ws-b", skill_id)

    _authenticate(app, "ws-a")
    assert _contains_skill(client, "ws-a", skill_id)


def test_client_cannot_set_its_own_passing_eval_score(app) -> None:
    client = TestClient(app)
    _authenticate(app, "ws-a")

    res = client.post(
        "/agent/skills/candidates",
        json={
            "name": "Self Scorer",
            "domain": "sales",
            "instructions": "x",
            "workspace_id": "ws-a",
        },
    )
    assert res.status_code == 201
    skill_id = res.json()["skill_id"]

    res = client.post(
        f"/agent/skills/{skill_id}/evaluate",
        json={"eval_score": 1.0, "eval_details": {"claimed": "pass"}},
    )
    assert res.status_code == 422


def test_founder_cannot_promote_candidate_with_unknown_capability(app) -> None:
    client = TestClient(app)
    _authenticate(app, "ws-a")

    res = client.post(
        "/agent/skills/candidates",
        json={
            "name": "Unknown Cap Skill",
            "domain": "sales",
            "instructions": "x",
            "workspace_id": "ws-a",
            "required_capabilities": ["not-a-real.capability"],
        },
    )
    assert res.status_code == 201
    skill_id = res.json()["skill_id"]

    res_promote = client.post(
        f"/agent/skills/{skill_id}/promote",
        json={"approved_by": "founder", "approval_reason": "try"},
    )
    assert res_promote.status_code == 400
