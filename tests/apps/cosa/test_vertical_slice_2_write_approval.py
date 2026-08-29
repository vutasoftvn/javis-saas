from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
import httpx
import pytest

from apps.cosa.api.app import create_cosa_app
from apps.cosa.agents.seed import seed_cosa_agent_specs
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client
from tests.apps.cosa.worker_test_helpers import drain_worker_queue


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    mock_client.post.return_value = {
        "payout_id": "po_slice2_777",
        "status": "committed",
        "transaction_ref": "tx_slice2_888",
    }
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
        model=FakeSDKModel(
            responses=[
                tool_call_response(
                    "call_slice2_tx",
                    "finance.transaction.record",
                    arguments='{"workspace_id": "1", "amount": 60000, "direction": "OUT", "description": "High-value server purchase"}',
                ),
                text_response("Transaction recorded"),
            ]
        ),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app)
    return app, plane, mock_client


@pytest.mark.asyncio
async def test_vertical_slice_2_write_with_approval_and_resume(test_app):
    """Vertical Slice 2 (Write + Approval + Resume Path, Master Guide §41).
    
    Quy trình:
    1. Tạo Conversation với active_agent_profile: 'finance'.
    2. Gửi Message yêu cầu ghi nhận giao dịch lớn $60,000 (CFO review required).
    3. Nhận 202 Accepted với run_id.
    4. Kernel pause và phát sinh approval.required trong SSE stream.
    5. Reviewer gọi POST /agent/approvals/{approval_id}/decision (approved=True).
    6. System phát tán approval.resolved và kích hoạt resume thành công.
    7. SSE stream nhận run.completed và hoàn tất quy trình.
    """
    app, plane, mock_client = test_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo Conversation
        res_conv = await ac.post("/agent/conversations", json={"title": "Finance Transaction Record", "active_agent_profile": "finance"})
        assert res_conv.status_code == 201
        conv_id = res_conv.json()["id"]

        # 2. Gửi Message yêu cầu ghi nhận giao dịch lớn (CFO review approval required)
        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "Record high-value transaction of $60,000 for server purchase"},
        )
        assert res_msg.status_code == 202
        run_id = res_msg.json()["run_id"]

        # Worker durable xử lý "run" task đã schedule.
        assert await drain_worker_queue(plane) == 1

        # 3. Kiểm tra event approval.required đã persist durable. Run đang
        # WAITING_APPROVAL (không phải terminal) nên GET /events qua HTTP sẽ
        # KHÔNG tự đóng stream (đúng thiết kế heartbeat §7.3) — httpx
        # ASGITransport trong môi trường test này buffer toàn bộ response tới
        # khi generator kết thúc (không hỗ trợ true incremental streaming),
        # nên không thể assert qua HTTP cho stream chưa terminal mà không
        # treo test. Verify trực tiếp qua durable repository — chính xác hơn
        # cho việc "event đã emit" (SSE wire-format cho case terminal đã test
        # ở bước 6 dưới, nơi ASGITransport hoạt động bình thường).
        events = await plane.stream_event_repository.list_since(run_id)
        assert any(e.event_type == "approval.required" for e in events)

        # 4. Tìm kiếm approval record trong pending
        pending_approvals = await plane.approval_service.list_pending_approvals()
        matching_approvals = [a for a in pending_approvals if a.run_id == run_id]
        assert len(matching_approvals) >= 1
        approval_id = matching_approvals[0].approval_id

        # 5. Reviewer gửi quyết định phê duyệt qua API
        res_decide = await ac.post(
            f"/agent/approvals/{approval_id}/decision",
            json={"approved": True, "reason": "Verified purchase order PO-12345"},
        )
        assert res_decide.status_code == 200
        decide_data = res_decide.json()
        assert decide_data["status"] == "approved"

        # Worker durable xử lý "resume" task đã schedule.
        assert await drain_worker_queue(plane) == 1

        # 6. Kiểm tra lại SSE event stream -> Phải có approval.resolved và run.completed
        res_events_2 = await ac.get(f"/agent/runs/{run_id}/events")
        assert res_events_2.status_code == 200
        body_2 = res_events_2.text
        assert "event: approval.resolved" in body_2
        assert "event: run.completed" in body_2


@pytest.fixture
def test_app_for_payload_shape():
    """Separate fixture cho payload shape test để tránh conflict với
    drain_worker_queue() của main flow test."""
    mock_client = AsyncMock(spec=CompanyServiceClient)
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
        model=FakeSDKModel(responses=[text_response("OK")]),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app)
    return app, plane


@pytest.mark.asyncio
async def test_scheduled_task_payload_never_contains_raw_bearer_token(test_app_for_payload_shape):
    """§6.2: token dài hạn của user thật không được nằm ở rest trong
    scheduled_tasks.input_payload — chỉ delegation_token ngắn hạn."""
    app, plane = test_app_for_payload_shape

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        res_conv = await ac.post("/agent/conversations", json={"title": "Payload Shape Check", "active_agent_profile": "finance"})
        conv_id = res_conv.json()["id"]
        await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "Execute wire payout $500 to Vendor X"},
        )

    tasks = await plane.scheduler.poll_due_tasks()
    assert len(tasks) == 1
    payload = tasks[0].input_payload
    assert "bearer_token" not in payload
    assert "delegation_token" in payload
    assert payload["delegation_token"] != "test-bearer-token"  # not the raw override_authenticated_identity() token
