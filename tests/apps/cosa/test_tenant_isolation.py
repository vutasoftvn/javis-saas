from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.coordination.scheduler import RunScheduler
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.leases import RunLeaseManager
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.api.app import create_cosa_app
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
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    app = create_cosa_app(plane=plane)
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
    plane = test_app.state.plane
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
        plane = test_app.state.plane
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


@pytest.mark.asyncio
async def test_workspace_id_collision_across_companies_does_not_leak(test_app):
    """Company A và Company B trùng workspace_id (vd do migration/seed data
    tình cờ) — server-side workspace resolve PHẢI trả về workspace thật
    thuộc company đang xác thực, không phải blindly trust client header, nên
    A và B (dù cùng gửi X-Workspace-Id: ws_shared) vẫn không nhìn thấy
    conversation của nhau. Test này KHÔNG dùng override_authenticated_identity()
    — nó chạy qua get_authenticated_identity() THẬT (JWT thật + HTTP header
    thật), chỉ mock ở biên httpx transport, để thực sự exercise code path
    resolve workspace (khác với unit test trực tiếp trong test_dependency.py)."""
    import time

    import jwt as pyjwt

    from apps.cosa.auth.company_client import CompanyTenantContextClient
    from apps.cosa.auth.cosa_client import CosaControlPlaneAuthClient
    from apps.cosa.auth.dependency import (
        get_authenticated_identity,
        set_company_tenant_context_client,
        set_cosa_auth_client,
    )

    SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"

    def _token(sub: str) -> str:
        return pyjwt.encode({"sub": sub, "aud": "cosa", "exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")

    def _cosa_client_for(company_id: str) -> CosaControlPlaneAuthClient:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"companies": [{"company_id": company_id, "name": "x", "role_id": "founder"}]}
            )

        return CosaControlPlaneAuthClient(base_url="http://test", transport=httpx.MockTransport(handler))

    def _tenant_client_for(company_id: str) -> CompanyTenantContextClient:
        def handler(request: httpx.Request) -> httpx.Response:
            # Trích workspace_id từ request body để server có thể resolve và verify
            body = request.content
            import json
            req_data = json.loads(body.decode()) if body else {}
            return httpx.Response(
                200,
                json={
                    "companyId": company_id,
                    "workspaceId": "ws_shared",
                    "userId": "u1",
                    "membershipRole": "founder",
                    "permissions": ["*"],
                    "correlationId": "corr-collision-test",
                },
            )

        return CompanyTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))

    # Đảm bảo dependency THẬT chạy (không override) cho test này.
    test_app.dependency_overrides.pop(get_authenticated_identity, None)

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
            # Alice (company_a) và Bob (company_b) đều gửi CÙNG X-Workspace-Id
            # header ("ws_shared"), nhưng server resolve ra 2 workspace THẬT
            # khác nhau — đây chính là cơ chế Task 2 thêm vào.
            set_cosa_auth_client(_cosa_client_for("company_a"))
            set_company_tenant_context_client(_tenant_client_for("company_a"))
            res_a = await ac.post(
                "/agent/conversations",
                json={"title": "A's conversation, collided workspace_id"},
                headers={
                    "Authorization": f"Bearer {_token('alice')}",
                    "X-Company-Id": "company_a",
                    "X-Workspace-Id": "ws_shared",
                },
            )
            assert res_a.status_code == 201
            conv_id = res_a.json()["id"]

            set_cosa_auth_client(_cosa_client_for("company_b"))
            set_company_tenant_context_client(_tenant_client_for("company_b"))
            res_get = await ac.get(
                f"/agent/conversations/{conv_id}",
                headers={
                    "Authorization": f"Bearer {_token('bob')}",
                    "X-Company-Id": "company_b",
                    "X-Workspace-Id": "ws_shared",
                },
            )
            assert res_get.status_code == 404
    finally:
        set_cosa_auth_client(None)
        set_company_tenant_context_client(None)


@pytest.mark.asyncio
async def test_approval_list_scoped_to_company_and_workspace(test_app):
    """Test tenant isolation for approval listing: two companies with pending
    approvals should not see each other's approvals even if they share workspace_id."""
    plane = test_app.state.plane
    from agent_core.runs.models import RunRecord

    # Create runs for both companies in SAME workspace (collision test)
    run_a = RunRecord(
        company_id="company_a",
        workspace_id="ws_shared",
        principal="user:alice",
        root_executable_id="test-spec",
    )
    await plane.repository.create_run(run_a)

    run_b = RunRecord(
        company_id="company_b",
        workspace_id="ws_shared",
        principal="user:bob",
        root_executable_id="test-spec",
    )
    await plane.repository.create_run(run_b)

    # Create approvals for both companies
    approval_a, _ = await plane.approval_service.create_approval_request(
        run_id=run_a.run_id,
        tool_call_id="tc_a",
        checkpoint_ref="ckpt_a",
        requirement={"risk_level": "high"},
        requester="user:alice",
        action="finance.wire_payout",
        subject="Acme Corp",
    )

    approval_b, _ = await plane.approval_service.create_approval_request(
        run_id=run_b.run_id,
        tool_call_id="tc_b",
        checkpoint_ref="ckpt_b",
        requirement={"risk_level": "high"},
        requester="user:bob",
        action="finance.wire_payout",
        subject="Beta Inc",
    )

    # Tenant A should only see approval A (using TENANT_A identity but with shared workspace)
    tenant_a_shared = dict(principal_id="user:alice", company_id="company_a", workspace_id="ws_shared")
    override_authenticated_identity(test_app, **tenant_a_shared)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res_a = await ac.get("/agent/approvals")
        assert res_a.status_code == 200
        items_a = res_a.json()["items"]
        approval_ids_a = [item["approval_id"] for item in items_a]
        assert approval_a.approval_id in approval_ids_a
        assert approval_b.approval_id not in approval_ids_a

        # Tenant B should only see approval B (using TENANT_B identity but with shared workspace)
        tenant_b_shared = dict(principal_id="user:bob", company_id="company_b", workspace_id="ws_shared")
        override_authenticated_identity(test_app, **tenant_b_shared)
        res_b = await ac.get("/agent/approvals")
        assert res_b.status_code == 200
        items_b = res_b.json()["items"]
        approval_ids_b = [item["approval_id"] for item in items_b]
        assert approval_b.approval_id in approval_ids_b
        assert approval_a.approval_id not in approval_ids_b


@pytest.mark.asyncio
async def test_tenant_b_cannot_read_tenant_a_session_timeline(test_app):
    """Test tenant isolation on GET /agent/sessions/{conversation_id}: tenant B
    cannot read tenant A's session view even with scoped conversation lookup."""
    override_authenticated_identity(test_app, **TENANT_A)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res_conv = await ac.post("/agent/conversations", json={"title": "A's session"})
        assert res_conv.status_code == 201
        conv_id = res_conv.json()["id"]

        res_session_a = await ac.get(f"/agent/sessions/{conv_id}")
        assert res_session_a.status_code == 200

        override_authenticated_identity(test_app, **TENANT_B)
        res_session_b = await ac.get(f"/agent/sessions/{conv_id}")
        assert res_session_b.status_code == 404
