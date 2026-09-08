from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from agent.artifacts.repository import InMemoryArtifactRepository
from agent.capabilities.gateway import GatewayExecutionResult
from agent.contracts.run import RunResult, RunStatus
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
        return_value=SimpleNamespace(
            content=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(mode="json")
        )
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

    handlers_by_capability = {
        "engagement.thread.read": mock_thread_read,
        "commercial.customer_360.read": mock_customer_read,
        "engagement.message.draft": mock_draft,
    }

    cap_registry = MagicMock()
    cap_registry.get_handler.side_effect = handlers_by_capability.get
    plane.capability_registry = cap_registry

    # IA25 phần 2 — copilot_run.py giờ gọi capability qua plane.gateway.execute()
    # (CapabilityGateway thật trong production, xem agent_plane.py) thay vì
    # gọi handler trực tiếp. Stub gateway ở boundary đúng chỗ nó thật sự nằm
    # (execute()), không mock sâu hơn vào bên trong gateway — vẫn dispatch
    # tới đúng mock handler theo capability_id để giữ nguyên hành vi/assertion
    # của các test hiện có.
    async def _fake_gateway_execute(req):
        handler = handlers_by_capability.get(req.capability_id)
        if handler is None:
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="failed",
                error_message=f"Capability '{req.capability_id}' not found in registry",
            )
        output = await handler(req.input_payload, req.context)
        return GatewayExecutionResult(
            tool_call_id=req.tool_call_id, status="completed", output_payload=output
        )

    plane.gateway = MagicMock()
    plane.gateway.execute = AsyncMock(side_effect=_fake_gateway_execute)

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
    plane.artifact_repository.get = AsyncMock(return_value=SimpleNamespace(artifact_id="art_mock"))

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

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
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
    stale_content = COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(mode="json", exclude={"id"})
    mock_plane.spec_registry.get = AsyncMock(return_value=SimpleNamespace(content=stale_content))
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
        "delegation_token": "test-delegation-token",
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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
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
async def test_copilot_completes_with_a_real_artifact_repository_not_a_mock(
    mock_plane, mock_stream_mgr
):
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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_real_repo_1", "completed")

        # Artifact thực sự nằm trong repository, đọc lại được bằng đúng workspace.
        artifact_ref = mock_cb.call_args.kwargs["artifact_ref"]
        retrieved = await mock_plane.artifact_repository.get("ws_1", artifact_ref)
        assert retrieved is not None


@pytest.mark.asyncio
async def test_copilot_fails_closed_when_no_artifact_repository_is_configured(
    mock_plane, mock_stream_mgr
):
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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args[1] != "completed"
        assert mock_cb.call_args.kwargs.get("reason_code") != "missing_delegation_token"


@pytest.mark.asyncio
async def test_copilot_fails_closed_when_delegation_token_is_missing_instead_of_self_minting(
    mock_plane, mock_stream_mgr
):
    """IA25: trước đây thiếu delegation_token thì tự mint bằng
    mint_company_delegation() dưới actor giả "0" — nhưng token đó ký sai
    định dạng cho đích thật (route Copilot gọi xác thực bằng verifyAccessToken/
    JWT_SECRET, không phải company delegation/COSA_COMPANY_DELEGATION_SECRET),
    nên luôn fail xác thực dù có "vẻ" như đã xử lý. Giờ phải fail-closed ngay,
    không tự mint bất kỳ token nào, và không được gọi capability nào cả."""
    payload = {
        "run_id": "run_no_token_1",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_100", "contact_id": "c_200"},
        "intent": "summarize",
        "identity_verified": False,
        "knowledge_scope": {},
        "correlation_id": "corr-no-token",
        # delegation_token intentionally omitted
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
        await run_customer_support_copilot(mock_plane, mock_stream_mgr, payload)

        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_no_token_1", "failed")
        assert mock_cb.call_args.kwargs.get("reason_code") == "missing_delegation_token"
        assert (
            mock_stream_mgr.emit.call_args.kwargs["payload"]["error"] == "missing_delegation_token"
        )

        # No capability was ever executed (via the gateway) with a bogus token.
        mock_plane.gateway.execute.assert_not_called()
        assert mock_plane.kernel.run.await_count == 0


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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
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
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
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
    with patch(
        "apps.cosa.capabilities.client.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
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


@pytest.mark.asyncio
async def test_copilot_reads_go_through_a_real_capability_gateway_with_audit_trail(mock_stream_mgr):
    """IA25 phần 2 — chứng minh copilot_run.py thực sự đi qua
    CapabilityGateway THẬT (không chỉ gọi 1 mock giống hình dạng gateway):
    dùng CapabilityRegistry + CapabilityGateway + InMemoryRunRepository THẬT
    (spec risk=LOW/approval_policy=NEVER thật của engagement.thread.read),
    xác nhận sau khi chạy có 1 tool_call record status=completed thật trong
    repository — audit trail mà đường gọi handler trực tiếp cũ KHÔNG BAO GIỜ
    tạo ra được."""
    from agent.capabilities.gateway import CapabilityGateway
    from agent.capabilities.registry import CapabilityRegistry
    from agent.runs.repository import InMemoryRunRepository

    from apps.cosa.capabilities.engagement_message_draft import ENGAGEMENT_MESSAGE_DRAFT_SPEC
    from apps.cosa.capabilities.engagement_read import ENGAGEMENT_THREAD_READ_SPEC

    registry = CapabilityRegistry()
    received_calls = []

    async def real_thread_read_handler(payload, ctx):
        received_calls.append((payload, ctx))
        return {
            "thread": {"id": payload["thread_id"], "status": "open", "priority": "normal"},
            "contactId": None,
            "identityVerified": False,
            "messages": [],
        }

    async def real_draft_handler(payload, ctx):
        return {"artifact_kind": "message_draft", "draft_body": payload.get("draft_body", "")}

    registry.register(ENGAGEMENT_THREAD_READ_SPEC, real_thread_read_handler)
    registry.register(ENGAGEMENT_MESSAGE_DRAFT_SPEC, real_draft_handler)
    repository = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repository)

    plane = MagicMock()
    plane.spec_registry = MagicMock()
    plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(
            content=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(mode="json")
        )
    )
    plane.gateway = gateway
    plane.capability_registry = registry
    plane.kernel = MagicMock()
    plane.kernel.run = AsyncMock(
        return_value=RunResult(
            run_id="run_real_gateway_1",
            status=RunStatus.COMPLETED,
            final_output={
                "summary": "Đã đọc thread qua gateway thật",
                "evidence_refs": ["thread.context"],
            },
        )
    )
    plane.artifact_repository = MagicMock()
    plane.artifact_repository.create = AsyncMock()
    plane.artifact_repository.get = AsyncMock(return_value=SimpleNamespace(artifact_id="art_mock"))
    plane.run_stream_event_repository = MagicMock()
    plane.run_stream_event_repository.append = AsyncMock()

    payload = {
        "run_id": "run_real_gateway_1",
        "workspace_id": "ws_real_gateway",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_real_1"},
        "intent": "summarize",
        "correlation_id": "corr-real-gateway",
        "delegation_token": "test-delegation-token",
    }

    with patch(
        "apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock
    ) as mock_cb:
        await run_customer_support_copilot(plane, mock_stream_mgr, payload)
        mock_cb.assert_awaited_once()
        assert mock_cb.call_args.args == ("run_real_gateway_1", "completed")

    # Handler thật đã được gọi đúng payload/context qua gateway.
    assert len(received_calls) == 1
    call_payload, call_ctx = received_calls[0]
    assert call_payload == {"thread_id": "t_real_1"}
    assert call_ctx.get("delegation_token") == "test-delegation-token"

    # Audit trail thật: gateway đã tự lưu 1 tool_call record status=completed
    # cho capability engagement.thread.read — đường gọi handler trực tiếp cũ
    # (bị thay thế ở IA25 phần 2) không bao giờ tạo ra bản ghi này.
    tool_calls = [
        tc
        for tc in repository._tool_calls.values()  # type: ignore[attr-defined]
        if tc.capability_id == "engagement.thread.read"
    ]
    assert len(tool_calls) == 1
    assert tool_calls[0].status == "completed"


@pytest.mark.asyncio
async def test_copilot_run_locale_provenance_from_profile(mock_plane, mock_stream_mgr):
    plane = mock_plane
    mock_locale_client = AsyncMock()
    from apps.cosa.policies.profile_locale_client import ProfileLocaleSnapshot

    mock_locale_client.get_snapshot.return_value = ProfileLocaleSnapshot(
        workspace_id="ws_copilot_loc",
        preferred_locale="en-US",
    )
    plane.profile_locale_client = mock_locale_client

    payload = {
        "run_id": "run_copilot_loc_1",
        "workspace_id": "ws_copilot_loc",
        "principal": "user:123",
        "delegation_token": "delegation-token-en",
        "thread_ref": {"thread_id": "t_loc_1"},
        "intent": "summarize",
        "correlation_id": "corr-loc-1",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock):
        await run_customer_support_copilot(plane, mock_stream_mgr, payload)

    run_req = plane.kernel.run.call_args[0][0]
    assert run_req.locale == "en-US"
    assert run_req.metadata["locale"] == "en-US"
    assert run_req.metadata["locale_source"] == "profile"
    assert "Analyze thread t_loc_1" in run_req.input["prompt"]


@pytest.mark.asyncio
async def test_copilot_run_fails_closed_when_user_principal_profile_locale_fails(
    mock_plane, mock_stream_mgr
):
    plane = mock_plane
    mock_locale_client = AsyncMock()
    from apps.cosa.policies.profile_locale_client import ProfileLocaleUnavailable

    mock_locale_client.get_snapshot.side_effect = ProfileLocaleUnavailable("control plane 503")
    plane.profile_locale_client = mock_locale_client

    payload = {
        "run_id": "run_copilot_loc_fail",
        "workspace_id": "ws_copilot_loc",
        "principal": "user:123",
        "delegation_token": "delegation-token-err",
        "thread_ref": {"thread_id": "t_loc_2"},
        "intent": "summarize",
        "correlation_id": "corr-loc-2",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock):
        result = await run_customer_support_copilot(plane, mock_stream_mgr, payload)

    assert result["status"] == "failed"
    assert "profile_locale_unavailable" in result["reason"]
    # Verify kernel run was NOT invoked (fail-closed, no silent vi-VN execution)
    plane.kernel.run.assert_not_called()
