from __future__ import annotations

import asyncio
from pathlib import Path
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

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)
from tests.apps.cosa.worker_test_helpers import drain_worker_queue

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    mock_client.get.return_value = {
        "tasks": [{"id": 1, "title": "Launch Q4 Strategy", "status": "in_progress"}],
        "total": 1,
    }
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        # Wave 7 (durable dispatch/lease) mặc định gọi services/cosa control
        # plane thật qua HTTP — test dùng in-memory tường minh, không có Encore
        # CLI/Postgres trong môi trường phát triển này.
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    asyncio.run(
        seed_cosa_runtime_specs(
            spec_registry=plane.spec_registry,
            capability_registry=plane.capability_registry,
            skillpacks_root=REPO_ROOT / "skillpacks",
        )
    )
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app)
    return app, plane, mock_client


@pytest.mark.asyncio
async def test_vertical_slice_1_read_path(test_app):
    """Vertical Slice 1 (Read Path, Master Guide §40).
    
    Quy trình:
    1. Tạo Conversation qua POST /agent/conversations.
    2. Gửi Message qua POST /agent/conversations/{id}/messages.
    3. Nhận 202 Accepted với run_id duy nhất.
    4. Lắng nghe SSE stream qua GET /agent/runs/{run_id}/events.
    5. Kiểm tra danh mục events: run.started, reasoning.status, message.started, message.delta, run.completed.
    6. Kiểm tra tin nhắn phản hồi đã lưu vào Conversation.
    """
    app, plane, _mock_client = test_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo Conversation
        res_conv = await ac.post("/agent/conversations", json={"title": "Operations Inquiry", "active_agent_profile": "operations"})
        assert res_conv.status_code == 201
        conv_data = res_conv.json()
        conv_id = conv_data["id"]
        assert conv_data["title"] == "Operations Inquiry"

        # 2. Gửi Message kích hoạt Run
        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={
                "content": "Please list all in_progress operations tasks",
                "data_access": {"categories": ["NON_PERSONAL"]},
            },
        )
        assert res_msg.status_code == 202
        run_data = res_msg.json()
        run_id = run_data["run_id"]
        assert run_data["status"] == "RUNNING"
        assert run_id.startswith("run_")

        # Worker durable xử lý task đã schedule (thay asyncio.create_task cũ)
        dispatched = await drain_worker_queue(plane)
        assert dispatched == 1

        # 3. Lấy lại Conversation chi tiết
        res_detail = await ac.get(f"/agent/conversations/{conv_id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert len(detail_data["messages"]) >= 2
        assistant_msgs = [m for m in detail_data["messages"] if m["role"] == "assistant"]
        assert assistant_msgs[0]["status"] == "completed", f"Assistant message status error: {assistant_msgs[0]['content']}"


        # 4. Kiểm tra SSE event stream
        res_events = await ac.get(f"/agent/runs/{run_id}/events")
        assert res_events.status_code == 200
        body = res_events.text
        assert "event: run.started" in body
        assert "event: reasoning.status" in body
        assert "event: message.delta" in body
        assert "event: run.completed" in body
