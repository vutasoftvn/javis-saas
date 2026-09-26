from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from agent.contracts.run import RunStatus
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository, SpecDependencyMissingError
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.company.project_team_client import (
    ProjectAgentRunAuthority,
    ProjectTeamAuthorityError,
    ProjectTeamClient,
    SpecRef,
)
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError
from apps.cosa.worker.handlers import execute_resume_task, execute_run_task
from tests.apps.cosa.policy_test_helpers import (
    allow_all_policy_snapshot,
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


def _plane():
    # Task 7 (2026-08-30) — CosaDataModelGate.prepare_initial_input giờ gọi
    # thật self._client.resolve_data_use(...) khi có DataAccessClaim (mock
    # compliance resolver trong build_cosa_agent_plane tự gắn 1 claim mặc
    # định tối thiểu — xem _MockComplianceResolverWithDefaultClaim). Không
    # truyền company_client= ở đây sẽ khiến gate dùng CompanyServiceClient()
    # thật và cố gọi network ra http://localhost:4000 — mock rõ ràng để test
    # này không phụ thuộc 1 server Company thật đang chạy.
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    mock_team_client = AsyncMock(spec=ProjectTeamClient)

    async def _mock_get_run_authority(*, workspace_id: str, project_id: str, profile_key: str):
        spec = AGENT_PROFILE_SPECS.get(profile_key)
        if not spec:
            raise ProjectTeamAuthorityError("not found", status_code=404)
        return ProjectAgentRunAuthority(
            projectId=project_id,
            workspaceId=workspace_id,
            profileKey=profile_key,
            assignmentVersion=1,
            agentWorkforceMemberId="wm_mock_1",
            spec=SpecRef(
                id=spec.id,
                version=spec.version,
                hash=spec.compute_hash(),
            ),
            policySnapshot={"knowledge_gate_passed": True},
        )

    mock_team_client.get_run_authority.side_effect = _mock_get_run_authority
    plane.project_team_client = mock_team_client
    return plane


def _payload(**overrides) -> dict:
    base = {
        "run_id": "run_handler_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": "ws_1",
        "project_id": "proj_1",
        "company_id": "test_company_1",
        "delegation_token": "fake-token",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_execute_run_task_fails_gracefully_when_registry_not_seeded():
    plane = _plane()
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert any(m.status == "failed" for m in messages)


@pytest.mark.asyncio
async def test_execute_run_task_resolves_exact_spec_after_seeding():
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert not any(m.status == "failed" for m in messages)
    assert any(m.role == "assistant" and m.status == "completed" for m in messages)


@pytest.mark.asyncio
async def test_goal_like_message_appends_goal_confirm_card():
    """WGA — tin nhắn founder trông như phát biểu mục tiêu tuần -> agent chèn
    thêm 1 structured `goal_confirm` message (JSON) sau câu trả lời."""
    import json as _json

    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    goal_msg = "Tuần này tôi muốn chốt 3 buổi phỏng vấn khách hàng và hoàn thành landing page"
    await execute_run_task(plane, stream_mgr, _payload(user_prompt=goal_msg))

    messages = await plane.conversation_repository.list_messages("conv_1")
    confirm = [
        m
        for m in messages
        if m.role == "assistant"
        and m.content.strip().startswith("{")
        and '"goal_confirm"' in m.content
    ]
    assert len(confirm) == 1
    parsed = _json.loads(confirm[0].content)
    assert parsed["kind"] == "goal_confirm"
    assert "phỏng vấn khách hàng" in parsed["normalized_goal"]


@pytest.mark.asyncio
async def test_non_goal_message_does_not_append_goal_confirm_card():
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(
        plane, stream_mgr, _payload(user_prompt="Ai đang phụ trách task này vậy?")
    )

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert not any("goal_confirm" in m.content for m in messages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agent_profile", "expected_spec_id"),
    [
        ("operations", "cosa.agents.operations"),
        ("finance", "cosa.agents.finance"),
        ("marketing", "cosa.agents.marketing"),
        # Default thật hiện tại của Flutter (chat_controller.dart
        # createNewConversation() không truyền agentProfile) — trỏ tới COSA_COFOUNDER_ASSISTANT_AGENT_SPEC.
        ("founder_assistant", "cosa.agents.founder_assistant"),
    ],
)
async def test_execute_run_task_dispatches_correct_spec_per_agent_profile(
    agent_profile: str, expected_spec_id: str
) -> None:
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(
        plane,
        stream_mgr,
        _payload(agent_profile=agent_profile),
    )

    run = await plane.run_repository.get_run("run_handler_test_1")
    assert run is not None
    assert run.root_executable_id == expected_spec_id


@pytest.mark.asyncio
async def test_execute_run_task_fails_gracefully_when_user_prompt_is_missing():
    """IA24: payload["user_prompt"] trước đây truy cập trực tiếp — thiếu field
    này (payload event-driven chưa được adapter tổng hợp) raise KeyError chưa
    bắt thay vì fail-closed có kiểm soát như đường thiếu delegation_token."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    payload = _payload()
    del payload["user_prompt"]

    await execute_run_task(plane, stream_mgr, payload)

    run = await plane.run_repository.get_run("run_handler_test_1")
    assert run is None
    events = await plane.stream_event_repository.list_since("run_handler_test_1")
    assert any(
        e.event_type == "run.failed" and e.payload.get("error") == "missing_user_prompt"
        for e in events
    )


@pytest.mark.asyncio
async def test_execute_run_task_rejects_unsupported_profile():
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(
        plane,
        stream_mgr,
        _payload(agent_profile="unsupported_profile_xyz"),
    )

    run = await plane.run_repository.get_run("run_handler_test_1")
    assert run is None
    events = await plane.stream_event_repository.list_since("run_handler_test_1")
    assert any(e.event_type == "run.failed" for e in events)


class _SpyComplianceResolver:
    """Ghi lại `RunRequest` thật đã được truyền vào
    `ComplianceResolver.resolve_for_run` (Task 4) — dùng để chứng minh Task 5
    forward đúng `direct_message_data_access` (server-generated
    source_ref/source_hash, không phải nội dung message thô) từ payload đã
    schedule vào `RunRequest.metadata`, mà không cần mock lại toàn bộ resolver
    thật."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.request = None

    async def resolve_for_run(self, request, spec):
        self.request = request
        return await self._inner.resolve_for_run(request, spec)


async def _all_client_visible_text(plane, *, run_id: str, conversation_id: str) -> str:
    """Gom mọi text mà client CÓ THỂ nhìn thấy — conversation message content
    + payload của mọi stream event đã emit cho run này. Dùng để chứng minh
    lỗi runtime không bị leak ra ngoài (không chỉ kiểm tra 1 chỗ)."""
    messages = await plane.conversation_repository.list_messages(conversation_id)
    events = await plane.stream_event_repository.list_since(run_id)
    parts = [m.content or "" for m in messages]
    parts.extend(str(event.payload) for event in events)
    return " ".join(parts)


@pytest.mark.asyncio
async def test_unexpected_worker_error_is_not_sent_to_client():
    """Task 6 — lỗi runtime bất ngờ (vd. exception nội bộ có thể chứa pin/
    secret) KHÔNG được forward nguyên văn cho client qua message hay stream
    event; chỉ log server-side kèm run_id."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    plane.kernel.run = AsyncMock(side_effect=RuntimeError("internal-pin-and-secret"))

    payload = _payload()
    await execute_run_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert "internal-pin-and-secret" not in visible_text
    assert "internal_error" in visible_text


@pytest.mark.asyncio
async def test_tenant_policy_error_is_not_sent_to_client():
    """Task 6 review finding — CosaTenantPolicyError (thất bại resolve
    PolicySnapshot từ Company) trước đây bị interpolate nguyên văn `{exc}`
    vào message/event client-facing. Giờ chỉ mã lỗi ổn định
    `policy_snapshot_unavailable` được forward, exception thật chỉ log
    server-side."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    secret_detail = "internal-policy-store-dsn-leak-detail"
    plane.tenant_policy_client.get_snapshot = AsyncMock(
        side_effect=CosaTenantPolicyError(secret_detail)
    )

    payload = _payload()
    await execute_run_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
    assert "policy_snapshot_unavailable" in visible_text


@pytest.mark.asyncio
async def test_resume_scopes_approval_to_tool_call_id_not_blanket():
    """Bug 1.2: trước fix, execute_resume_task luôn gửi {"approved": True} vô
    điều kiện xuống kernel.resume — approve chéo MỌI tool call khác đang
    pending trong cùng checkpoint, không chỉ tool call vừa được duyệt. Payload
    resume phải scope đúng qua approved_tool_calls={tool_call_id: True}.

    Bug 1.3's verify_and_prepare_resume() giờ chạy trước kernel.resume nên cần
    seed Run/ToolCall/Checkpoint/Approval thật (cùng pattern với
    test_resume_blocked_when_tenant_suspended_via_verify_and_prepare_resume)
    để verification không fail-closed vì thiếu record."""
    from agent.runs.models import (
        RunApprovalRecord,
        RunCheckpointRecord,
        RunRecord,
        RunToolCallRecord,
    )

    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    plane.kernel.resume = AsyncMock(
        return_value=SimpleNamespace(
            run_id="run_resume_scoped_1",
            status=RunStatus.COMPLETED,
            final_output=None,
            errors=[],
            usage=None,
        )
    )

    run_id = "run_resume_scoped_1"
    checkpoint_ref = "checkpoint_1"
    tool_call_id = "tc_scoped_call"

    await plane.repository.create_run(
        RunRecord(
            run_id=run_id,
            workspace_id="ws_1",
            principal="user_1",
            root_executable_id="cosa.agents.operations",
        )
    )
    await plane.repository.save_tool_call(
        RunToolCallRecord(
            tool_call_id=tool_call_id,
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            capability_id="finance.accounting_document.confirm",
            payload_hash="hash1",
        )
    )
    await plane.repository.save_checkpoint(
        RunCheckpointRecord(
            checkpoint_ref=checkpoint_ref, run_id=run_id, sequence_no=1, serialized_state={}
        )
    )
    await plane.repository.create_approval(
        RunApprovalRecord(
            approval_id="appr_scoped_1",
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=checkpoint_ref,
            status="approved",
            action="finance.accounting_document.confirm",
        )
    )

    payload = {
        "run_id": run_id,
        "checkpoint_ref": checkpoint_ref,
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "agent_profile": "operations",
        "delegation_token": "fake-token",
        "tool_call_id": tool_call_id,
        "approval_id": "appr_scoped_1",
    }
    await execute_resume_task(plane, stream_mgr, payload)

    plane.kernel.resume.assert_awaited_once()
    call = plane.kernel.resume.await_args
    updates = call.kwargs["updates"]
    assert updates.get("approved_tool_calls") == {"tc_scoped_call": True}
    assert "approved" not in updates


@pytest.mark.asyncio
async def test_resume_fails_closed_when_tool_call_id_missing():
    """Không có tool_call_id trong payload -> KHÔNG được fallback về blanket
    approve; phải fail-closed và không gọi kernel.resume."""
    plane = _plane()
    stream_mgr = CosaEventStreamManager()
    plane.kernel.resume = AsyncMock()

    payload = {
        "run_id": "run_resume_missing_tcid",
        "checkpoint_ref": "checkpoint_1",
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "agent_profile": "operations",
        "delegation_token": "fake-token",
    }
    await execute_resume_task(plane, stream_mgr, payload)

    plane.kernel.resume.assert_not_awaited()


@pytest.mark.asyncio
async def test_resume_blocked_when_tenant_suspended_via_verify_and_prepare_resume():
    """Bug 1.3: DurableApprovalService.verify_and_prepare_resume() (kiểm tenant
    suspend/principal revoked/drift trước resume) trước đây là dead code —
    không ai gọi trên đường resume thật. Dùng service THẬT (không mock) — nếu
    workspace đã bị suspend giữa lúc approve và lúc resume thật sự chạy,
    kernel.resume KHÔNG được gọi."""
    from agent.runs.models import (
        RunApprovalRecord,
        RunCheckpointRecord,
        RunRecord,
        RunToolCallRecord,
    )

    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    plane.kernel.resume = AsyncMock()

    run_id = "run_resume_suspended_1"
    tool_call_id = "tc_suspended_1"
    checkpoint_ref = "ckpt_suspended_1"

    await plane.repository.create_run(
        RunRecord(
            run_id=run_id,
            workspace_id="ws_1",
            principal="user_1",
            root_executable_id="cosa.agents.operations",
        )
    )
    await plane.repository.save_tool_call(
        RunToolCallRecord(
            tool_call_id=tool_call_id,
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            capability_id="finance.accounting_document.confirm",
            payload_hash="hash1",
        )
    )
    await plane.repository.save_checkpoint(
        RunCheckpointRecord(
            checkpoint_ref=checkpoint_ref, run_id=run_id, sequence_no=1, serialized_state={}
        )
    )
    approval = RunApprovalRecord(
        approval_id="appr_suspended_1",
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        status="approved",
        action="finance.accounting_document.confirm",
    )
    await plane.repository.create_approval(approval)

    suspended_snapshot = allow_all_policy_snapshot()
    suspended_snapshot.workspace_status = "suspended"
    plane.tenant_policy_client.get_snapshot = AsyncMock(return_value=suspended_snapshot)

    payload = {
        "run_id": run_id,
        "checkpoint_ref": checkpoint_ref,
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "agent_profile": "operations",
        "delegation_token": "fake-token",
        "tool_call_id": tool_call_id,
        "approval_id": approval.approval_id,
    }
    await execute_resume_task(plane, stream_mgr, payload)

    plane.kernel.resume.assert_not_awaited()
    visible_text = await _all_client_visible_text(
        plane, run_id=run_id, conversation_id=payload["conversation_id"]
    )
    assert "resume_verification_failed" in visible_text


@pytest.mark.asyncio
async def test_resume_tenant_policy_error_is_not_sent_to_client():
    """Final-review Finding 2 — second, structurally identical
    `CosaTenantPolicyError` branch in `execute_resume_task` (resume-after-
    approval flow) had the same raw-exception-interpolation bug as the
    already-fixed branch in `_execute_run_task_inner`. Only the stable code
    `policy_snapshot_unavailable_on_resume` may reach the client."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    secret_detail = "internal-policy-store-dsn-leak-detail-resume"
    plane.tenant_policy_client.get_snapshot = AsyncMock(
        side_effect=CosaTenantPolicyError(secret_detail)
    )

    payload = {
        "run_id": "run_resume_test_1",
        "checkpoint_ref": "checkpoint_1",
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "agent_profile": "operations",
        "delegation_token": "fake-token",
        "tool_call_id": "tc_policy_error_test",
    }
    await execute_resume_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
    assert "policy_snapshot_unavailable_on_resume" in visible_text


@pytest.mark.asyncio
async def test_spec_resolution_error_is_not_sent_to_client():
    """Task 6 review finding — SpecDependencyMissingError (registry chưa
    seed / dependency drift) trước đây leak nguyên văn exception — đúng ví dụ
    "internal pinned-skill detail" constraint plan nêu — ra client. Giờ chỉ
    mã lỗi ổn định `spec_resolution_unavailable` được forward."""
    plane = _plane()
    stream_mgr = CosaEventStreamManager()
    secret_detail = "pinned-skill-internal-fingerprint-detail"

    async def _raise_missing(*_args, **_kwargs):
        raise SpecDependencyMissingError("prompt", secret_detail, "v1", "not_found")

    with patch(
        "apps.cosa.worker.run_core.SpecResolver.resolve_agent_spec_dependencies",
        _raise_missing,
    ):
        payload = _payload()
        await execute_run_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
    assert "spec_resolution_unavailable" in visible_text


@pytest.mark.asyncio
async def test_worker_forwards_server_provenance():
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    resolver = _SpyComplianceResolver(plane.compliance_resolver)
    plane.compliance_resolver = resolver

    payload = _payload(
        direct_message_data_access={
            "categories": ["NON_PERSONAL"],
            "subject_reference": None,
            "source_ref": "conversation_message:msg_123",
            "source_hash": "deadbeef",
        }
    )

    await execute_run_task(plane, stream_mgr, payload)

    assert resolver.request is not None
    context = resolver.request.metadata["direct_message_data_access"]
    assert context["source_ref"] == "conversation_message:msg_123"
    assert context["source_hash"] != "plan next quarter"
    assert "content" not in context


async def _seed_approved_resume(plane, *, run_id: str) -> dict:
    """Seed Run/ToolCall/Checkpoint/Approval đã duyệt để verify_and_prepare_resume
    cho phép resume — trả về payload resume tương ứng."""
    from agent.runs.models import (
        RunApprovalRecord,
        RunCheckpointRecord,
        RunRecord,
        RunToolCallRecord,
    )

    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    checkpoint_ref = f"{run_id}_ckpt"
    tool_call_id = f"{run_id}_tc"
    await plane.repository.create_run(
        RunRecord(
            run_id=run_id,
            workspace_id="ws_1",
            principal="user_1",
            root_executable_id="cosa.agents.operations",
        )
    )
    await plane.repository.save_tool_call(
        RunToolCallRecord(
            tool_call_id=tool_call_id,
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            capability_id="finance.accounting_document.confirm",
            payload_hash="hash1",
        )
    )
    await plane.repository.save_checkpoint(
        RunCheckpointRecord(
            checkpoint_ref=checkpoint_ref, run_id=run_id, sequence_no=1, serialized_state={}
        )
    )
    await plane.repository.create_approval(
        RunApprovalRecord(
            approval_id=f"{run_id}_appr",
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=checkpoint_ref,
            status="approved",
            action="finance.accounting_document.confirm",
        )
    )
    return {
        "run_id": run_id,
        "checkpoint_ref": checkpoint_ref,
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "agent_profile": "operations",
        "delegation_token": "fake-token",
        "tool_call_id": tool_call_id,
        "approval_id": f"{run_id}_appr",
    }


@pytest.mark.asyncio
async def test_resume_that_hits_another_approval_emits_approval_required():
    """Trước đây execute_resume_task chỉ xử lý COMPLETED: nếu bước sau cần duyệt
    tiếp thì không phát event nào và UI kẹt."""
    plane = _plane()
    stream_mgr = CosaEventStreamManager()
    payload = await _seed_approved_resume(plane, run_id="run_resume_wait_1")
    plane.kernel.resume = AsyncMock(
        return_value=SimpleNamespace(
            run_id=payload["run_id"],
            status=RunStatus.WAITING_APPROVAL,
            final_output=None,
            errors=[],
            usage=None,
            interruptions_waits=[
                SimpleNamespace(
                    related_ref="appr_next", checkpoint_ref="ckpt_next", reason="Need approval"
                )
            ],
        )
    )

    await execute_resume_task(plane, stream_mgr, payload)

    events = await plane.stream_event_repository.list_since(payload["run_id"])
    required = [e for e in events if e.event_type == "approval.required"]
    assert len(required) == 1
    assert required[0].payload["approval_id"] == "appr_next"


@pytest.mark.asyncio
async def test_resume_kernel_error_emits_run_failed_without_leaking_detail():
    plane = _plane()
    stream_mgr = CosaEventStreamManager()
    payload = await _seed_approved_resume(plane, run_id="run_resume_boom_1")
    secret_detail = "postgres://internal-host:5432 exploded"
    plane.kernel.resume = AsyncMock(side_effect=RuntimeError(secret_detail))

    await execute_resume_task(plane, stream_mgr, payload)

    events = await plane.stream_event_repository.list_since(payload["run_id"])
    assert any(
        e.event_type == "run.failed" and e.payload.get("error") == "internal_error" for e in events
    )
    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
