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


async def _create_run(plane, *, run_id: str = "run_project_ctx_1") -> str:
    """Tạo trực tiếp 1 RunRecord thật gắn `project_id="proj_a"` trong
    `plane.repository` — bỏ qua toàn bộ kernel/skill resolution (không liên
    quan tới điều đang test: route cancel/events có enforce đúng
    project_id hay không), cùng pattern với
    `test_tenant_b_cannot_decide_approval_of_tenant_a_run` trong
    test_tenant_isolation.py.

    Cũng append sẵn 1 `run.completed` stream event — GET /runs/{id}/events
    replay từ durable store trước khi live-stream; không có event terminal
    nào sẽ khiến generator treo chờ mãi (chỉ nhả heartbeat) vì run này không
    thực sự chạy qua kernel để tự phát ra run.completed/failed."""
    from agent.runs.models import RunRecord
    from agent.runs.stream_events import RunStreamEventRecord

    conversation_id = "conv_project_ctx_1"
    run = RunRecord(
        run_id=run_id,
        workspace_id=WORKSPACE_A,
        project_id="proj_a",
        conversation_id=conversation_id,
        principal="user:test",
        root_executable_id="test-spec",
    )
    await plane.repository.create_run(run)
    await plane.stream_event_repository.append(
        RunStreamEventRecord(
            run_id=run_id,
            event_type="run.completed",
            payload={"status": "COMPLETED"},
            conversation_id=conversation_id,
            workspace_id=WORKSPACE_A,
            project_id="proj_a",
        )
    )
    return run_id


@pytest.mark.asyncio
async def test_cancel_run_rejects_mismatched_project_id(test_app) -> None:
    """Review Finding 1 — caller khai project_id tường minh trên cancel phải
    được enforce khớp với Project thật của run, không chỉ âm thầm cancel bất
    kể request project_id là gì."""
    app, plane, _ = test_app
    run_id = await _create_run(plane)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        mismatched = await ac.post(f"/agent/runs/{run_id}/cancel", params={"project_id": "proj_b"})
        assert mismatched.status_code == 422
        assert mismatched.json()["detail"]["code"] == "PROJECT_CONTEXT_MISMATCH"

        # Run KHÔNG bị cancel bởi request mismatch ở trên.
        still_running = await plane.repository.get_run(run_id)
        assert still_running is not None
        assert still_running.status.value != "cancelled"

        # project_id khớp thật -> cancel thành công.
        matched = await ac.post(f"/agent/runs/{run_id}/cancel", params={"project_id": "proj_a"})
        assert matched.status_code == 200

        # Không khai project_id vẫn giữ hành vi cũ (idempotent cancel).
        no_project = await ac.post(f"/agent/runs/{run_id}/cancel")
        assert no_project.status_code == 200


@pytest.mark.asyncio
async def test_get_run_events_rejects_mismatched_project_id(test_app) -> None:
    """Review Finding 1 — tương tự cancel_run cho GET /runs/{id}/events."""
    app, plane, _ = test_app
    run_id = await _create_run(plane)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        mismatched = await ac.get(f"/agent/runs/{run_id}/events", params={"project_id": "proj_b"})
        assert mismatched.status_code == 422
        assert mismatched.json()["detail"]["code"] == "PROJECT_CONTEXT_MISMATCH"

        matched = await ac.get(f"/agent/runs/{run_id}/events", params={"project_id": "proj_a"})
        assert matched.status_code == 200

        no_project = await ac.get(f"/agent/runs/{run_id}/events")
        assert no_project.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["cto", "ceo", "chief_of_staff", "kickoff_suggestion", "xyz"])
async def test_create_conversation_rejects_profile_without_chat_authority(test_app, profile) -> None:
    """Chỉ profile của startup team mới chat được; executive/overlay/system không
    có authority Project cho chat — 422 trước mọi side effect."""
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/agent/conversations",
            json={"title": "t", "project_id": "proj_a", "active_agent_profile": profile},
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "AGENT_PROFILE_NOT_CHAT_ELIGIBLE"
    conversations, total = await plane.conversation_repository.list_conversations(
        workspace_id=WORKSPACE_A, project_id="proj_a"
    )
    assert (conversations, total) == ([], 0)


@pytest.mark.asyncio
async def test_update_conversation_rejects_profile_without_chat_authority(test_app) -> None:
    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        created = await ac.post(
            "/agent/conversations",
            json={"title": "t", "project_id": "proj_a", "active_agent_profile": "founder_assistant"},
        )
        assert created.status_code in (200, 201)
        conv_id = created.json()["id"]
        response = await ac.patch(
            f"/agent/conversations/{conv_id}?project_id=proj_a",
            json={"active_agent_profile": "cto"},
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "AGENT_PROFILE_NOT_CHAT_ELIGIBLE"
    stored = await plane.conversation_repository.get_conversation(conv_id)
    assert stored.active_agent_profile == "founder_assistant"


@pytest.mark.asyncio
async def test_get_run_events_for_run_not_yet_picked_up_by_worker(test_app) -> None:
    """RunRecord chỉ có khi worker bắt đầu chạy; client mở SSE ngay sau POST
    message. Trước fix route trả 404 -> chat báo "Luồng phản hồi đóng trước khi
    COSA trả lời". Giờ chứng minh sở hữu qua conversation + message có run_id."""
    from agent.runs.stream_events import RunStreamEventRecord

    app, plane, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        conv_id = (
            await ac.post(
                "/agent/conversations",
                json={"title": "Hub", "active_agent_profile": "operations", "project_id": "proj_a"},
            )
        ).json()["id"]
        run_id = (
            await ac.post(
                f"/agent/conversations/{conv_id}/messages",
                json={
                    "content": "hi",
                    "project_id": "proj_a",
                    "data_access": {"categories": ["NON_PERSONAL"]},
                },
            )
        ).json()["run_id"]
        assert await plane.repository.get_scoped_run(run_id=run_id, workspace_id=WORKSPACE_A) is None

        # Worker (tiến trình khác) sau đó ghi event terminal vào durable store.
        await plane.stream_event_repository.append(
            RunStreamEventRecord(
                run_id=run_id,
                event_type="run.completed",
                payload={"output": "xin chào"},
                conversation_id=conv_id,
                workspace_id=WORKSPACE_A,
                project_id="proj_a",
            )
        )

        ok = await ac.get(f"/agent/runs/{run_id}/events", params={"conversation_id": conv_id})
        assert ok.status_code == 200
        assert "event: run.completed" in ok.text

        # Thiếu conversation_id, hoặc conversation không chứa run này -> 404.
        assert (await ac.get(f"/agent/runs/{run_id}/events")).status_code == 404
        other_conv = (
            await ac.post(
                "/agent/conversations",
                json={"title": "Other", "active_agent_profile": "operations", "project_id": "proj_a"},
            )
        ).json()["id"]
        wrong = await ac.get(f"/agent/runs/{run_id}/events", params={"conversation_id": other_conv})
        assert wrong.status_code == 404
