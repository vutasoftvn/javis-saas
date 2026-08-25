from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.coordination.scheduler import RunScheduler
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.leases import RunLeaseManager
from agent_core.runs.repository import InMemoryRunRepository
from apps.cosa.api.app import create_cosa_app
from apps.cosa.api.routes import set_cosa_plane
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client
from tests.apps.cosa.worker_test_helpers import drain_worker_queue

TENANT_A = dict(principal_id="user:alice", company_id="company_a", workspace_id="ws_a")
TENANT_B = dict(principal_id="user:bob", company_id="company_b", workspace_id="ws_b")


@pytest.fixture
def test_app():
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
    )
    set_cosa_plane(plane)
    app = create_cosa_app()
    return app


@pytest.mark.asyncio
async def test_no_bearer_token_rejected(test_app):
    """Không có Authorization header -> 401, không rơi về identity mặc định
    nào (đúng COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §4.1:
    cấm production default company_1/ws_1/user:default)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post("/agent/conversations", json={"title": "x"})
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_tenant_b_cannot_read_tenant_a_conversation(test_app):
    override_authenticated_identity(test_app, **TENANT_A)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res_create = await ac.post("/agent/conversations", json={"title": "Tenant A secret"})
        assert res_create.status_code == 201
        conv_id = res_create.json()["id"]

        # Chuyển sang tenant B (khác company_id) trên cùng app instance.
        override_authenticated_identity(test_app, **TENANT_B)

        res_get = await ac.get(f"/agent/conversations/{conv_id}")
        assert res_get.status_code == 404

        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "trying to inject into tenant A's conversation"},
        )
        assert res_msg.status_code == 404

        res_patch = await ac.patch(f"/agent/conversations/{conv_id}", json={"title": "hijacked"})
        assert res_patch.status_code == 404


@pytest.mark.asyncio
async def test_list_conversations_scoped_to_own_tenant(test_app):
    override_authenticated_identity(test_app, **TENANT_A)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post("/agent/conversations", json={"title": "A's conversation"})
        assert res.status_code == 201

        override_authenticated_identity(test_app, **TENANT_B)
        res_b_create = await ac.post("/agent/conversations", json={"title": "B's conversation"})
        assert res_b_create.status_code == 201

        res_b_list = await ac.get("/agent/conversations")
        assert res_b_list.status_code == 200
        titles = [c["title"] for c in res_b_list.json()["items"]]
        assert "B's conversation" in titles
        assert "A's conversation" not in titles


@pytest.mark.asyncio
async def test_tenant_b_cannot_cancel_or_read_events_of_tenant_a_run(test_app):
    from apps.cosa.api.routes import get_cosa_plane

    plane = get_cosa_plane()
    override_authenticated_identity(test_app, **TENANT_A)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res_conv = await ac.post("/agent/conversations", json={"title": "A's run holder"})
        conv_id = res_conv.json()["id"]
        res_msg = await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "list tasks"},
        )
        run_id = res_msg.json()["run_id"]

        # Worker durable xử lý task đã schedule -> RunRecord thật tồn tại
        # trong plane.repository trước khi kiểm tra tenant isolation.
        assert await drain_worker_queue(plane) == 1

        override_authenticated_identity(test_app, **TENANT_B)

        res_cancel = await ac.post(f"/agent/runs/{run_id}/cancel")
        assert res_cancel.status_code == 404

        res_events = await ac.get(f"/agent/runs/{run_id}/events")
        assert res_events.status_code == 404


@pytest.mark.asyncio
async def test_tenant_b_cannot_decide_approval_of_tenant_a_run(test_app):
    """approval_id không tự mang tenant scope — phải tra run liên kết trước
    khi cho quyết định (xem _get_owned_run_or_404 trong routes.py)."""
    override_authenticated_identity(test_app, **TENANT_A)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        # Tạo approval trực tiếp qua approval_service (bỏ qua toàn bộ kernel
        # run thật — chỉ cần 1 RunApprovalRecord + RunRecord cùng company_a để
        # test tenant check ở API layer).
        from apps.cosa.api.routes import get_cosa_plane

        plane = get_cosa_plane()
        from agent_core.runs.models import RunRecord

        run = RunRecord(
            company_id="company_a",
            workspace_id="ws_a",
            principal="user:alice",
            root_executable_id="test-spec",
        )
        await plane.repository.create_run(run)

        approval, _wait_desc = await plane.approval_service.create_approval_request(
            run_id=run.run_id,
            tool_call_id="tc_1",
            checkpoint_ref="ckpt_1",
            requirement={"risk_level": "high"},
            requester="user:alice",
            action="finance.wire_payout",
            subject="Acme Corp",
        )

        override_authenticated_identity(test_app, **TENANT_B)
        res_decide = await ac.post(
            f"/agent/approvals/{approval.approval_id}/decision",
            json={"approved": True},
        )
        assert res_decide.status_code == 404
