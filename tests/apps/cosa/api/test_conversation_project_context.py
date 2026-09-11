"""Task 2 (2026-09-11 Project-scoped Founder Hub) — mọi side effect (lưu
conversation/message, mint delegation, schedule run) phải TUYỆT ĐỐI vắng mặt
khi Project context thiếu/lệch/không được Company xác nhận. Bổ sung cho
`tests/apps/cosa/test_routes.py` (data_access gate) — file này chỉ tập trung
vào gate Project."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.locale_test_helpers import FakeProfileLocaleClient
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    configure_mock_client_project_access,
    fake_active_tenant_policy_client,
)

WORKSPACE_A = "ws_a"


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    configure_mock_client_project_access(mock_client, workspace_id=WORKSPACE_A)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(workspace_id=WORKSPACE_A),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        profile_locale_client=FakeProfileLocaleClient(),
    )
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app, workspace_id=WORKSPACE_A)
    return app, plane, mock_client


@pytest.mark.asyncio
async def test_create_conversation_without_project_id_is_rejected_with_no_side_effect(
    test_app,
) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/agent/conversations",
            json={"title": "Founder Hub", "active_agent_profile": "operations"},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "PROJECT_CONTEXT_REQUIRED"

        conversations, total = await plane.conversation_repository.list_conversations(
            workspace_id=WORKSPACE_A, project_id="proj_a"
        )
        assert (conversations, total) == ([], 0)


@pytest.mark.asyncio
async def test_create_conversation_with_unauthorized_project_returns_404(test_app) -> None:
    """Company không xác nhận được Project (cross-tenant / không tồn tại) —
    404 PROJECT_NOT_FOUND_OR_FORBIDDEN, không lộ chi tiết tồn tại hay không."""
    app, plane, mock_client = test_app
    configure_mock_client_project_access(
        mock_client, workspace_id=WORKSPACE_A, denied_project_ids={"proj_b"}
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/agent/conversations",
            json={
                "title": "Founder Hub",
                "active_agent_profile": "operations",
                "project_id": "proj_b",
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "PROJECT_NOT_FOUND_OR_FORBIDDEN"

        conversations, total = await plane.conversation_repository.list_conversations(
            workspace_id=WORKSPACE_A, project_id="proj_b"
        )
        assert (conversations, total) == ([], 0)


@pytest.mark.asyncio
async def test_message_with_mismatched_project_id_is_rejected_with_no_side_effect(test_app) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            "/agent/conversations",
            json={
                "title": "Founder Hub",
                "active_agent_profile": "operations",
                "project_id": "proj_a",
            },
        )
        assert create_res.status_code == 201
        conv_id = create_res.json()["id"]

        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "ship it",
                "project_id": "proj_b",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "PROJECT_CONTEXT_MISMATCH"

        messages = await plane.conversation_repository.list_messages(conv_id)
        assert messages == []
        tasks = await plane.scheduler.poll_due_tasks()
        assert tasks == []


@pytest.mark.asyncio
async def test_message_without_project_id_is_rejected_with_no_side_effect(test_app) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            "/agent/conversations",
            json={
                "title": "Founder Hub",
                "active_agent_profile": "operations",
                "project_id": "proj_a",
            },
        )
        conv_id = create_res.json()["id"]

        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "ship it", "data_access": {"categories": ["NON_PERSONAL"]}},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "PROJECT_CONTEXT_REQUIRED"

        messages = await plane.conversation_repository.list_messages(conv_id)
        assert messages == []
        tasks = await plane.scheduler.poll_due_tasks()
        assert tasks == []


@pytest.mark.asyncio
async def test_valid_message_with_matching_project_id_is_saved_and_scheduled(test_app) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            "/agent/conversations",
            json={
                "title": "Founder Hub",
                "active_agent_profile": "operations",
                "project_id": "proj_a",
            },
        )
        conv_id = create_res.json()["id"]

        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "ship it",
                "project_id": "proj_a",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert response.status_code == 202

        tasks = await plane.scheduler.poll_due_tasks()
        assert len(tasks) == 1
        assert tasks[0].input_payload["project_id"] == "proj_a"


@pytest.mark.asyncio
async def test_list_conversations_requires_and_verifies_project_id(test_app) -> None:
    app, _, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        missing = await ac.get("/agent/conversations")
        assert missing.status_code == 422
        assert missing.json()["detail"]["code"] == "PROJECT_CONTEXT_REQUIRED"

        scoped = await ac.get("/agent/conversations", params={"project_id": "proj_a"})
        assert scoped.status_code == 200


@pytest.mark.asyncio
async def test_get_conversation_requires_and_verifies_project_id(test_app) -> None:
    app, _, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            "/agent/conversations",
            json={"title": "Founder Hub", "project_id": "proj_a"},
        )
        conv_id = create_res.json()["id"]

        missing = await ac.get(f"/agent/conversations/{conv_id}")
        assert missing.status_code == 422
        assert missing.json()["detail"]["code"] == "PROJECT_CONTEXT_REQUIRED"

        wrong_project = await ac.get(
            f"/agent/conversations/{conv_id}", params={"project_id": "proj_c"}
        )
        assert wrong_project.status_code == 404

        ok = await ac.get(f"/agent/conversations/{conv_id}", params={"project_id": "proj_a"})
        assert ok.status_code == 200
