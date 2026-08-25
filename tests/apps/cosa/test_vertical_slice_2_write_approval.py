from __future__ import annotations

from unittest.mock import AsyncMock
import httpx
import pytest

from apps.cosa.api.app import create_cosa_app
from apps.cosa.api.routes import set_cosa_plane
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.coordination.scheduler import RunScheduler
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.leases import RunLeaseManager
from agent_core.runs.repository import InMemoryRunRepository
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
    )
    set_cosa_plane(plane)
    app = create_cosa_app()
    override_authenticated_identity(app)
    return app, plane, mock_client


@pytest.mark.asyncio
async def test_vertical_slice_2_write_with_approval_and_resume(test_app):
    """Vertical Slice 2 (Write + Approval + Resume Path, Master Guide §41).
    
    Quy trình:
    1. Tạo Conversation với active_agent_profile: 'finance'.
    2. Gửi Message yêu cầu giải ngân $20,000 tới Acme Corp.
    3. Nhận 202 Accepted với run_id.
    4. Kernel pause và phát sinh approval.required trong SSE stream.
    5. Reviewer gọi POST /agent/approvals/{approval_id}/decision (approved=True).
    6. System phát tán approval.resolved và kích hoạt resume thành công.
    7. SSE stream nhận run.completed và hoàn tất quy trình.
    """
    app, plane, mock_client = test_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo Conversation
        res_conv = await ac.post("/agent/conversations", json={"title": "Finance Wire Payout", "active_agent_profile": "finance"})
        assert res_conv.status_code == 201
        conv_id = res_conv.json()["id"]

        # 2. Gửi Message yêu cầu chuyển tiền (High Risk write)
        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "Execute wire payout $20,000 to Acme Corp"},
        )
        assert res_msg.status_code == 202
        run_id = res_msg.json()["run_id"]

        # Worker durable xử lý "run" task đã schedule.
        assert await drain_worker_queue(plane) == 1

        # 3. Kiểm tra SSE event stream ban đầu -> Phải có approval.required
        res_events_1 = await ac.get(f"/agent/runs/{run_id}/events")
        assert res_events_1.status_code == 200
        body_1 = res_events_1.text
        assert "event: approval.required" in body_1

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
