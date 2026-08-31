from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
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
        mock_cb.assert_awaited_once_with("run_bad_1", "failed")


@pytest.mark.asyncio
async def test_copilot_fails_closed_when_registered_spec_content_is_invalid(
    mock_plane, mock_stream_mgr
):
    """Simulates registry corruption/drift via a field with no default (`id`) so
    this stays a genuine invalid-content test regardless of which other fields
    later become optional — see the autopilot-copilot-initial-input-unblock plan."""
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
    mock_cb.assert_awaited_once_with("run_stale_spec_1", "failed")


@pytest.mark.asyncio
async def test_copilot_unexpected_error_is_not_sent_to_client(mock_plane, mock_stream_mgr):
    """Final-review Finding 1 — exception thô (vd. secret nội bộ) từ nhánh
    `except Exception` bao trùm KHÔNG được interpolate vào payload SSE
    `run.failed` client-facing; chỉ mã lỗi ổn định `internal_error` được
    forward, exception thật chỉ log server-side (cùng pattern với
    `execute_run_task`'s broad-failure branch trong
    `apps/cosa/worker/handlers.py`)."""
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

    mock_cb.assert_awaited_once_with("run_crash_1", "failed")
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
