"""Task 5 — HTTP layer bắt buộc khai báo `data_access` khi gửi tin nhắn trực
tiếp, và server phải tự tính source_ref/source_hash từ nội dung ĐÃ LƯU (không
phải input thô) trước khi forward vào RunRequest.metadata (Task 4)."""

from __future__ import annotations

import asyncio
import hashlib
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

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app)
    return app, plane, mock_client


async def _create_conversation(ac: httpx.AsyncClient) -> str:
    res = await ac.post(
        "/agent/conversations",
        json={"title": "T", "active_agent_profile": "operations"},
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_message_without_data_access_is_rejected_before_dispatch(test_app) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        conv_id = await _create_conversation(ac)
        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "plan next quarter"},
        )
        assert response.status_code == 422

        # Không lưu message, không schedule task — reject trước khi đụng vào
        # side effect nào.
        messages = await plane.conversation_repository.list_messages(conv_id)
        assert messages == []
        tasks = await plane.scheduler.poll_due_tasks()
        assert tasks == []


@pytest.mark.asyncio
async def test_message_from_identity_without_platform_link_is_rejected_cleanly(test_app) -> None:
    """B5 fix — principal chưa từng sync qua platform (thiếu platform_user_id
    thật) không thể mint control-plane delegation. Trước fix, lỗi này raise
    thẳng ở bước schedule (SAU KHI message đã lưu DB) -> 500 thô + message mồ
    côi không bao giờ có run. Giờ chặn TRƯỚC khi lưu message, trả 403 rõ ràng."""
    app, plane, _ = test_app
    override_authenticated_identity(app, resolved_platform_user_id=None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        conv_id = await _create_conversation(ac)
        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "plan next quarter",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert response.status_code == 403

        # Không lưu message mồ côi, không schedule task nào.
        messages = await plane.conversation_repository.list_messages(conv_id)
        assert messages == []
        tasks = await plane.scheduler.poll_due_tasks()
        assert tasks == []


@pytest.mark.asyncio
async def test_message_with_empty_categories_is_rejected(test_app) -> None:
    app, _, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        conv_id = await _create_conversation(ac)
        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "plan next quarter", "data_access": {"categories": []}},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_message_with_personal_category_missing_subject_reference_is_rejected(
    test_app,
) -> None:
    app, _, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        conv_id = await _create_conversation(ac)
        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "customer phone is 0900000000",
                "data_access": {"categories": ["PERSONAL"]},
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_valid_message_is_saved_and_scheduled_with_hashed_context(test_app) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        conv_id = await _create_conversation(ac)
        response = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "plan next quarter",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert response.status_code == 202
        message_id = response.json()["message_id"]

        tasks = await plane.scheduler.poll_due_tasks()
        assert len(tasks) == 1
        payload = tasks[0].input_payload

        # Raw content KHÔNG được lưu lặp lại vào context — chỉ source_ref/hash.
        context = payload["direct_message_data_access"]
        assert context["source_ref"] == f"conversation_message:{message_id}"
        assert context["source_hash"] == hashlib.sha256(b"plan next quarter").hexdigest()
        assert context["categories"] == ["NON_PERSONAL"] or set(context["categories"]) == {
            "NON_PERSONAL"
        }
        assert "content" not in context
        assert "plan next quarter" not in str(context)
