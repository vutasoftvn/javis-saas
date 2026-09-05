from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from agent.artifacts.repository import InMemoryArtifactRepository
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.engagement_read import create_engagement_thread_read_handler
from apps.cosa.worker.copilot_run import run_customer_support_copilot


@pytest.fixture
def mock_plane():
    plane = MagicMock()
    # spec_registry theo interface thật: get(kind, id, version) -> record có .content
    plane.spec_registry = MagicMock()
    plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(content=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(mode="json"))
    )

    # Capability registry / handlers
    mock_thread_read = AsyncMock(
        return_value={
            "thread": {"id": "t_100", "status": "open", "priority": "urgent"},
            "contactId": "c_200",
            "identityVerified": False,
            "messages": [{"id": "m_1", "body": "Need help with invoice", "visibility": "public"}],
        }
    )
    mock_customer_read = AsyncMock(
        return_value={
            "contact": {"id": "c_200", "name": "Alice"},
            "account": {"id": "a_1", "name": "AliceCorp"},
        }
    )
    mock_draft = AsyncMock(
        return_value={
            "artifact_kind": "message_draft",
            "thread_id": "t_100",
            "draft_body": "Xin chào Alice, tôi có thể hỗ trợ gì cho bạn?",
            "evidence_refs": ["knowledge.billing.policy"],
            "rationale": "Gợi ý phản hồi",
            "delivery": "none",
        }
    )

    cap_registry = MagicMock()
    cap_registry.get_handler.side_effect = lambda cap_id: {
        "engagement.thread.read": mock_thread_read,
        "commercial.customer_360.read": mock_customer_read,
        "engagement.message.draft": mock_draft,
    }.get(cap_id)
    plane.capability_registry = cap_registry

    # Kernel mock
    mock_kernel = MagicMock()
    mock_kernel.run = AsyncMock(
        return_value=RunResult(
            run_id="run_test_123",
            status=RunStatus.COMPLETED,
            final_output={
                "summary": "Khách hàng hỏi về hoá đơn",
                "recommended_response_draft": "Xin chào Alice, tôi có thể hỗ trợ gì cho bạn?",
                "intent": "summarize",
                "missing_info": ["mã hoá đơn"],
                "sales_signal": "Không có",
                "evidence_refs": ["knowledge.billing.policy"],
            },
        )
    )
    plane.kernel = mock_kernel

    # Artifact repo
    plane.artifact_repository = MagicMock()
    plane.artifact_repository.create = AsyncMock()
    plane.artifact_repository.get = AsyncMock(
        return_value=SimpleNamespace(artifact_id="art_mock")
    )

    # Stream event repo
    plane.run_stream_event_repository = MagicMock()
    plane.run_stream_event_repository.append = AsyncMock()

    return plane


@pytest.fixture
def mock_stream_mgr():
    mgr = MagicMock()
    mgr.emit = AsyncMock()
    return mgr


@pytest.mark.asyncio
async def test_copilot_guard_fails_when_spec_has_write_capability(mock_plane, mock_stream_mgr):
    # Spec with forbidden write capability
    bad_spec = AgentSpec(
        id="cosa.agents.customer_support",
        version=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.version,
        autonomy_level=AutonomyLevel.L0_OBSERVE,
        instructions="Bad",
        model_input_capability_ref="model.input.direct-user-message",
        capability_refs=["engagement.thread.read", "message.send"],
        prompt_ref=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.prompt_ref,
        model_policy_ref=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_policy_ref,
    )
    mock_plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(content=bad_spec.model_dump(mode="json"))
    )

    payload = {
        "run_id": "run_bad_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_1"},
        "correlation_id": "corr-1",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)
        # Kernel must not be called
        assert mock_plane.kernel.run.await_count == 0
        # Stream manager emits run.failed
        assert mock_stream_mgr.emit.await_count >= 1
        # Callback company result with failed
        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args[0] == "run_bad_1"
        assert mock_cb.call_args.args[1] == "failed"


@pytest.mark.asyncio
async def test_copilot_fails_closed_when_registered_spec_content_is_invalid(
    mock_plane, mock_stream_mgr
):
    stale_content = COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(
        mode="json", exclude={"id"}
    )
    mock_plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(content=stale_content)
    )
    payload = {
        "run_id": "run_stale_spec_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_1"},
        "correlation_id": "corr-stale",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

    mock_plane.kernel.run.assert_not_awaited()
    assert mock_stream_mgr.emit.call_args.kwargs["event_type"] == "run.failed"
    assert (
        mock_stream_mgr.emit.call_args.kwargs["payload"]["reason_code"]
        == "agent_spec_content_invalid"
    )
    mock_cb.assert_awaited_once()
    assert mock_cb.call_args.args[0] == "run_stale_spec_1"
    assert mock_cb.call_args.args[1] == "failed"


@pytest.mark.asyncio
async def test_copilot_unexpected_error_is_not_sent_to_client(mock_plane, mock_stream_mgr):
    secret_detail = "internal-copilot-secret-detail"
    mock_plane.kernel.run = AsyncMock(side_effect=RuntimeError(secret_detail))

    payload = {
        "run_id": "run_crash_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100", "contact_id": "c_200"},
        "intent": "summarize",
        "identity_verified": False,
        "knowledge_scope": {},
        "correlation_id": "corr-crash",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

    mock_cb.assert_awaited_once()
    assert mock_cb.call_args.args[0] == "run_crash_1"
    assert mock_cb.call_args.args[1] == "failed"
    assert mock_stream_mgr.emit.await_count >= 1
    all_emitted_text = " ".join(
        str(call.kwargs.get("payload", "")) for call in mock_stream_mgr.emit.call_args_list
    )
    assert secret_detail not in all_emitted_text
    call_kwargs = mock_stream_mgr.emit.call_args.kwargs
    assert call_kwargs["event_type"] == "run.failed"
    assert call_kwargs["payload"]["error"] == "internal_error"
    assert call_kwargs["payload"]["reason_code"] == "copilot_unhandled_exception"


@pytest.mark.asyncio
async def test_copilot_happy_path_artifact_persisted_ux_emitted_and_callback_sent(
    mock_plane, mock_stream_mgr
):
    payload = {
        "run_id": "run_good_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100", "contact_id": "c_200"},
        "intent": "summarize",
        "identity_verified": False,
        "knowledge_scope": {},
        "correlation_id": "corr-100",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        # 1. Artifact repository create called
        assert mock_plane.artifact_repository.create.await_count >= 1

        # 2. Stream manager emitted run.completed with evidence_refs
        assert mock_stream_mgr.emit.await_count >= 1
        call_kwargs = mock_stream_mgr.emit.call_args.kwargs
        assert call_kwargs["event_type"] == "run.completed"
        payload_emitted = call_kwargs["payload"]
        assert "evidence_refs" in payload_emitted
        assert payload_emitted["status"] == "completed"

        # 3. Callback Company service with completed
        mock_cb.assert_awaited_once()
        cb_args = mock_cb.call_args.args
        assert cb_args[0] == "run_good_1"
        assert cb_args[1] == "completed"
        assert "artifact_ref" in mock_cb.call_args.kwargs


@pytest.mark.asyncio
async def test_copilot_completes_with_a_real_artifact_repository_not_a_mock(mock_plane, mock_stream_mgr):
    """IA06: dùng InMemoryArtifactRepository THẬT (không phải AsyncMock chấp
    nhận mọi số lượng tham số) — trước đây get_fn(artifact_ref) gọi thiếu
    workspace_id, repository thật raise TypeError, bị nuốt bởi except và báo
    artifact_persisted=False oan cho một artifact ĐÃ create() thành công.
    """
    mock_plane.artifact_repository = InMemoryArtifactRepository()

    payload = {
        "run_id": "run_real_repo_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100", "contact_id": "c_200"},
        "intent": "summarize",
        "identity_verified": False,
        "knowledge_scope": {},
        "correlation_id": "corr-real-repo",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_real_repo_1", "completed")

        # Artifact thực sự nằm trong repository, đọc lại được bằng đúng workspace.
        artifact_ref = mock_cb.call_args.kwargs["artifact_ref"]
        retrieved = await mock_plane.artifact_repository.get("ws_1", artifact_ref)
        assert retrieved is not None


@pytest.mark.asyncio
async def test_copilot_fails_closed_when_no_artifact_repository_is_configured(mock_plane, mock_stream_mgr):
    """IA06: không có artifact_repository nào -> không có nơi nào lưu artifact
    -> phải fail-closed, không được mặc định coi như đã persist."""
    mock_plane.artifact_repository = None

    payload = {
        "run_id": "run_no_repo_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100", "contact_id": "c_200"},
        "intent": "summarize",
        "identity_verified": False,
        "knowledge_scope": {},
        "correlation_id": "corr-no-repo",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args[1] != "completed"


@pytest.mark.asyncio
async def test_copilot_failed_kernel_cannot_complete(mock_plane, mock_stream_mgr):
    """Kernel status=FAILED -> outcome failed, callback company failed."""
    mock_plane.kernel.run = AsyncMock(
        return_value=RunResult(
            run_id="run_fail_kernel",
            status=RunStatus.FAILED,
            errors=["model_overloaded"],
        )
    )
    payload = {
        "run_id": "run_fail_kernel",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100"},
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_fail_kernel", "failed")
        assert mock_cb.call_args.kwargs.get("reason_code") == "kernel_failed"
        assert mock_stream_mgr.emit.call_args.kwargs["event_type"] == "run.failed"


@pytest.mark.asyncio
async def test_copilot_empty_output_fails_run(mock_plane, mock_stream_mgr):
    """Output rỗng ({}) không được coi là success -> failed."""
    mock_plane.kernel.run = AsyncMock(
        return_value=RunResult(
            run_id="run_empty_output",
            status=RunStatus.COMPLETED,
            final_output={},
        )
    )
    payload = {
        "run_id": "run_empty_output",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100"},
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_empty_output", "failed")
        assert mock_cb.call_args.kwargs.get("reason_code") == "invalid_output"
        assert mock_stream_mgr.emit.call_args.kwargs["event_type"] == "run.failed"


@pytest.mark.asyncio
async def test_copilot_artifact_write_error_fails_run(mock_plane, mock_stream_mgr):
    """Artifact repo fail -> run không thể complete."""
    mock_plane.artifact_repository.create = AsyncMock(side_effect=RuntimeError("disk full"))

    payload = {
        "run_id": "run_art_fail",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100"},
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_art_fail", "failed")
        assert mock_cb.call_args.kwargs.get("reason_code") == "missing_artifact"
        assert mock_stream_mgr.emit.call_args.kwargs["event_type"] == "run.failed"


@pytest.mark.asyncio
async def test_copilot_waiting_approval_preserves_checkpoint(mock_plane, mock_stream_mgr):
    """WAITING_APPROVAL không báo failed."""
    mock_plane.kernel.run = AsyncMock(
        return_value=RunResult(
            run_id="run_wait_1",
            status=RunStatus.WAITING_APPROVAL,
            final_output={"summary": "Cần duyệt"},
        )
    )
    payload = {
        "run_id": "run_wait_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100"},
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_wait_1", "waiting_approval")


@pytest.mark.asyncio
async def test_copilot_auth_context_captured():
    """Auth test dùng CompanyServiceClient thật + mock HTTP transport, capture Authorization đúng delegation."""
    captured_headers = {}

    def transport_handler(request: httpx.Request) -> httpx.Response:
        captured_headers["Authorization"] = request.headers.get("Authorization")
        captured_headers["X-Workspace-Id"] = request.headers.get("X-Workspace-Id")
        return httpx.Response(200, json={"thread": {"id": "t_auth_1"}, "messages": []})

    transport = httpx.MockTransport(transport_handler)
    with patch("apps.cosa.capabilities.client.httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        client = CompanyServiceClient(base_url="http://company.internal")
        handler = create_engagement_thread_read_handler(client)
        ctx = {
            "workspace_id": "ws_auth_test",
            "delegation_token": "mock_delegation_jwt_token_123",
        }

        res = await handler({"thread_id": "t_auth_1"}, ctx)
        assert res["thread"]["id"] == "t_auth_1"
        assert captured_headers["Authorization"] == "Bearer mock_delegation_jwt_token_123"
        assert captured_headers["X-Workspace-Id"] == "ws_auth_test"
