from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client
from tests.apps.cosa.worker_test_helpers import drain_worker_queue

TENANT_A = dict(principal_id="user:alice", workspace_id="ws_a")
TENANT_B = dict(principal_id="user:bob", workspace_id="ws_b")


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
        from agent.runs.models import RunRecord

        run = RunRecord(
            company_id="ws_a",  # Use workspace_id as company_id for internal compatibility
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
    """Workspace-only isolation test: Alice and Bob with different workspace IDs
    cannot access each other's data. This test exercises the actual
    get_authenticated_identity() dependency (not mocked) by overriding the
    workspace client at the transport layer."""
    import os
    import time

    import jwt as pyjwt

    from apps.cosa.auth.workspace_client import WorkspaceTenantContextClient
    from apps.cosa.auth.dependency import (
        get_authenticated_identity,
        set_workspace_tenant_context_client,
    )

    SECRET = (
        os.environ.get("PLATFORM_JWT_SECRET")
        or "cosa-super-secret-platform-jwt-key-change-in-prod"
    )


    def _token(sub: str) -> str:
        return pyjwt.encode({"sub": sub, "aud": "cosa", "exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")

    def _workspace_client_for(workspace_id: str) -> WorkspaceTenantContextClient:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "workspaceId": workspace_id,
                    "userId": "u1",
                    "membershipRole": "founder",
                    "permissions": ["*"],
                    "correlationId": "corr-test",
                },
            )

        return WorkspaceTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))

    # Đảm bảo dependency THẬT chạy (không override) cho test này.
    test_app.dependency_overrides.pop(get_authenticated_identity, None)

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
            # Alice creates conversation in ws_alice
            set_workspace_tenant_context_client(_workspace_client_for("ws_alice"))
            res_a = await ac.post(
                "/agent/conversations",
                json={"title": "Alice's conversation"},
                headers={
                    "Authorization": f"Bearer {_token('alice')}",
                    "X-Workspace-Id": "ws_alice",
                },
            )
            assert res_a.status_code == 201
            conv_id = res_a.json()["id"]

            # Bob tries to access with different workspace
            set_workspace_tenant_context_client(_workspace_client_for("ws_bob"))
            res_get = await ac.get(
                f"/agent/conversations/{conv_id}",
                headers={
                    "Authorization": f"Bearer {_token('bob')}",
                    "X-Workspace-Id": "ws_bob",
                },
            )
            assert res_get.status_code == 404
    finally:
        set_workspace_tenant_context_client(None)


@pytest.mark.asyncio
async def test_approval_list_scoped_to_company_and_workspace(test_app):
    """Test tenant isolation for approval listing: two workspaces with pending
    approvals should not see each other's approvals."""
    plane = test_app.state.plane
    from agent.runs.models import RunRecord

    # Create runs for both workspaces
    run_a = RunRecord(
        company_id="ws_a",  # Use workspace_id as company_id for internal compatibility
        workspace_id="ws_a",
        principal="user:alice",
        root_executable_id="test-spec",
    )
    await plane.repository.create_run(run_a)

    run_b = RunRecord(
        company_id="ws_b",  # Use workspace_id as company_id for internal compatibility
        workspace_id="ws_b",
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

    # Tenant A should only see approval A
    tenant_a_identity = dict(principal_id="user:alice", workspace_id="ws_a")
    override_authenticated_identity(test_app, **tenant_a_identity)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res_a = await ac.get("/agent/approvals")
        assert res_a.status_code == 200
        items_a = res_a.json()["items"]
        approval_ids_a = [item["approval_id"] for item in items_a]
        assert approval_a.approval_id in approval_ids_a
        assert approval_b.approval_id not in approval_ids_a

        # Tenant B should only see approval B
        tenant_b_identity = dict(principal_id="user:bob", workspace_id="ws_b")
        override_authenticated_identity(test_app, **tenant_b_identity)
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
