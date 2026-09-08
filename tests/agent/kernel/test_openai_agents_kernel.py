from __future__ import annotations

import pytest
from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import RuntimeErrorCode
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import CapabilityRisk
from agent.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent.runs.models import RunRecord
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient


@pytest.mark.asyncio
async def test_kernel_end_to_end_execution_and_event_logging():
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    spec = AgentSpec(
        id="general_assistant",
        instructions="You are a helpful assistant.",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Hello world"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert "Processed: Hello world" in str(result.final_output)

    # Verify event ledger
    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.started" in event_types
    assert "message.delta" in event_types
    assert "run.completed" in event_types


@pytest.mark.asyncio
async def test_kernel_approval_pause_and_resume():
    repo = InMemoryRunRepository()

    def mock_executor(tool_name, args):
        return {"payout_id": "po_999", "status": "sent"}

    kernel = ManualToolLoopKernel(
        repository=repo,
        capability_executor=mock_executor,
        model_client=MockToolLoopModelClient(),
    )

    spec = AgentSpec(
        id="finance_agent",
        instructions="Handle payouts.",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="finance_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Transfer $1,000 to vendor_1"},
    )

    # 1. Chạy lần đầu -> phát hiện transfer -> pause WAITING_APPROVAL
    result = await kernel.run(request, spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    assert len(result.interruptions_waits) == 1

    wait = result.interruptions_waits[0]
    ckpt_ref = wait.checkpoint_ref
    appr_id = wait.related_ref

    # Verify approval record created in repository
    appr_record = await repo.get_approval(appr_id)
    assert appr_record is not None
    assert appr_record.status == "pending"

    # 2. Decide approval
    await repo.decide_approval(appr_id, reviewer="founder_1", approved=True)

    # 3. Resume với checkpoint_ref — approved_tool_calls (per-call_id) là API
    # duy nhất có hiệu lực từ Bug 1.2 fix; field "approved": True blanket đã
    # bị bỏ (approve chéo mọi pending call khác trong cùng checkpoint).
    call_id = appr_record.tool_call_id
    resumed = await kernel.resume(
        run_id=result.run_id,
        checkpoint_ref=ckpt_ref,
        updates={"approved_tool_calls": {call_id: True}},
    )

    assert resumed.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_kernel_resume_fails_closed_instead_of_crashing_when_gateway_denies():
    """Bug 1.1 (resume path): resume()'s tool-execution loop (dòng ~280) trước
    đây KHÔNG bọc try/except AgentRuntimeError như _execute_reasoning_loop —
    một gateway denial trong lúc resume làm crash cả task thay vì trả về
    RunResult FAILED có cấu trúc."""
    repo = InMemoryRunRepository()

    registry = CapabilityRegistry()
    payout_spec = CapabilitySpec(
        id="finance.payout.execute",
        risk=CapabilityRisk.HIGH,
        input_schema={"type": "object", "properties": {}},
    )

    def failing_handler(payload, ctx):
        raise RuntimeError("connector grant revoked between approval and resume")

    registry.register(payout_spec, failing_handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    kernel = ManualToolLoopKernel(
        repository=repo, capability_executor=gateway.execute, model_client=MockToolLoopModelClient()
    )

    spec = AgentSpec(
        id="finance_agent_resume_denied",
        instructions="Handle payouts.",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="finance_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Transfer $1,000 to vendor_1"},
    )

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    wait = result.interruptions_waits[0]
    tool_calls = await repo.list_tool_calls(result.run_id)
    call_id = tool_calls[0].tool_call_id

    resumed = await kernel.resume(
        run_id=result.run_id,
        checkpoint_ref=wait.checkpoint_ref,
        updates={"approved_tool_calls": {call_id: True}},
    )

    assert resumed.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_kernel_resume_does_not_cross_approve_other_pending_call():
    """Bug 1.2 (ManualToolLoopKernel): 2 tool call cùng pending trong 1
    checkpoint. Duyệt call_1 KHÔNG được tự động chạy luôn call_2 (trước đây
    `updates.get("approved") is True` là blanket, approve mọi pending call)."""
    from agent.kernel.openai_agents_kernel import KernelRunState
    from agent.runs.models import RunApprovalRecord, RunCheckpointRecord, RunRecord

    repo = InMemoryRunRepository()

    executed: list[dict] = []

    async def capability_executor(tool_name, args, ctx=None):
        executed.append({"tool": tool_name, "args": args})
        return {"status": "success"}

    kernel = ManualToolLoopKernel(
        repository=repo, capability_executor=capability_executor, model_client=MockToolLoopModelClient()
    )

    run_id = "run_multi_pending_1"
    await repo.create_run(
        RunRecord(
            run_id=run_id,
            principal="test_user",
            root_executable_id="test.agent.multi_pending",
            root_executable_version="1.0.0",
        )
    )

    call_id_1, call_id_2 = "call_p_1", "call_p_2"
    state = KernelRunState(
        run_id=run_id,
        messages=[{"role": "user", "content": "do two things"}],
        pending_tool_calls=[
            {"id": call_id_1, "name": "finance.payout.execute", "arguments": '{"vendor": "A"}'},
            {"id": call_id_2, "name": "finance.payout.execute", "arguments": '{"vendor": "B"}'},
        ],
        completed_tool_calls=[],
        context={},
        step_index=1,
    )
    ckpt_ref = f"ckpt_{run_id}_1"
    await repo.save_checkpoint(
        RunCheckpointRecord(checkpoint_ref=ckpt_ref, run_id=run_id, sequence_no=1, serialized_state=state.to_dict())
    )
    for cid in (call_id_1, call_id_2):
        await repo.create_approval(
            RunApprovalRecord(
                approval_id=f"appr_{run_id}_{cid}",
                run_id=run_id,
                tool_call_id=cid,
                checkpoint_ref=ckpt_ref,
                status="pending",
                action="finance.payout.execute",
            )
        )

    resumed = await kernel.resume(
        run_id=run_id, checkpoint_ref=ckpt_ref, updates={"approved_tool_calls": {call_id_1: True}}
    )

    assert len(executed) == 1
    assert executed[0]["args"]["vendor"] == "A"
    assert resumed.status == RunStatus.WAITING_APPROVAL
    remaining_call_ids = {w.related_ref for w in resumed.interruptions_waits}
    assert f"appr_{run_id}_{call_id_2}" in remaining_call_ids

    appr_2 = await repo.get_approval(f"appr_{run_id}_{call_id_2}")
    assert appr_2.status == "pending"


@pytest.mark.asyncio
async def test_kernel_resume_blanket_approved_flag_does_not_approve_other_pending_call():
    """Bug 1.2 (ManualToolLoopKernel, defense-in-depth — đồng bộ với
    RealOpenAIAgentsSDKKernel): kernel.resume() không còn được tin field
    "approved": True mơ hồ như "duyệt hết mọi pending call trong checkpoint" —
    chỉ approved_tool_calls mới có hiệu lực. Gọi kernel.resume trực tiếp với
    {"approved": True} (mô phỏng 1 caller khác trong tương lai vô tình gửi
    field cũ) không được chạy tool call nào chưa nằm trong approved_tool_calls."""
    from agent.kernel.openai_agents_kernel import KernelRunState
    from agent.runs.models import RunApprovalRecord, RunCheckpointRecord, RunRecord

    repo = InMemoryRunRepository()

    executed: list[dict] = []

    async def capability_executor(tool_name, args, ctx=None):
        executed.append({"tool": tool_name, "args": args})
        return {"status": "success"}

    kernel = ManualToolLoopKernel(
        repository=repo, capability_executor=capability_executor, model_client=MockToolLoopModelClient()
    )

    run_id = "run_blanket_flag_1"
    await repo.create_run(
        RunRecord(
            run_id=run_id,
            principal="test_user",
            root_executable_id="test.agent.blanket_flag",
            root_executable_version="1.0.0",
        )
    )

    call_id = "call_blanket_1"
    state = KernelRunState(
        run_id=run_id,
        messages=[{"role": "user", "content": "do one thing"}],
        pending_tool_calls=[
            {"id": call_id, "name": "finance.payout.execute", "arguments": '{"vendor": "A"}'},
        ],
        completed_tool_calls=[],
        context={},
        step_index=1,
    )
    ckpt_ref = f"ckpt_{run_id}_1"
    await repo.save_checkpoint(
        RunCheckpointRecord(checkpoint_ref=ckpt_ref, run_id=run_id, sequence_no=1, serialized_state=state.to_dict())
    )
    await repo.create_approval(
        RunApprovalRecord(
            approval_id=f"appr_{run_id}_{call_id}",
            run_id=run_id,
            tool_call_id=call_id,
            checkpoint_ref=ckpt_ref,
            status="pending",
            action="finance.payout.execute",
        )
    )

    resumed = await kernel.resume(run_id=run_id, checkpoint_ref=ckpt_ref, updates={"approved": True})

    assert len(executed) == 0
    assert resumed.status == RunStatus.WAITING_APPROVAL


@pytest.mark.asyncio
async def test_kernel_cancellation():
    repo = InMemoryRunRepository()
    # Prompt "Start task" khớp keyword "task" trong MockToolLoopModelClient
    # -> phát sinh 1 tool_call thật (operations.task.list). Kernel không còn
    # fallback "success" giả khi thiếu capability_executor (P0.3) nên test
    # này — vốn chỉ quan tâm cancel() sau khi run hoàn tất, không quan tâm
    # nội dung tool call — phải tự inject 1 executor giả tường minh.
    kernel = ManualToolLoopKernel(
        repository=repo,
        model_client=MockToolLoopModelClient(),
        capability_executor=lambda name, args: {"status": "success", "executed_tool": name},
    )

    spec = AgentSpec(
        id="long_agent",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Start task"},
    )

    # Tạo run record trước
    res = await kernel.run(request, spec)
    assert res.status == RunStatus.COMPLETED

    # Task 5 fix: cancel() trên 1 run ĐÃ terminal (COMPLETED) phải là no-op —
    # trước đây cancel() luôn unconditionally ghi CANCELLED đè lên bất kỳ
    # status nào (kể cả COMPLETED) và luôn trả True, khiến 1 cancel muộn có
    # thể "hồi sinh" 1 run đã xong việc thành CANCELLED (nói dối). Bây giờ
    # cancel_run là CAS atomic — COMPLETED/FAILED không nằm trong from_statuses
    # nên cancel() trả False và run giữ nguyên COMPLETED.
    cancelled = await kernel.cancel(res.run_id, reason="User cancelled")
    assert cancelled is False

    run_rec = await repo.get_run(res.run_id)
    assert run_rec.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_cancel_reason_not_clobbered_by_kernel_fast_path_cancel():
    """Regression test cho fix review Task 5: HTTP route (apps/cosa/api/routes.py)
    gọi repository.cancel_run(reason=<lý do có định danh principal>) rồi NGAY
    SAU ĐÓ gọi plane.kernel.cancel(run_id) như 1 fast-path để dừng reasoning
    loop in-process. Vì `cancel_run` cho phép CAS CANCELLED->CANCELLED
    (idempotent), lệnh gọi kernel.cancel() thứ hai — dù không đổi status —
    vẫn tự ghi lại error_details của riêng nó. Trước fix, route không truyền
    `reason` cho kernel.cancel() nên nó dùng fallback generic "Cancelled by
    user", âm thầm đè mất lý do có định danh đã ghi ở lệnh gọi đầu. Test này
    mô phỏng đúng trình tự gọi của route và khẳng định error_details cuối
    cùng vẫn là lý do gốc (route phải truyền CÙNG reason cho cả 2 lệnh gọi)."""
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    run = RunRecord(
        workspace_id="ws_1",
        principal="test_user",
        root_executable_id="general_assistant",
    )
    await repo.create_run(run)
    await repo.transition_run_status(
        run.run_id,
        from_statuses={RunStatus.PENDING},
        to_status=RunStatus.RUNNING,
    )

    identity_reason = "Cancelled via HTTP API by user_123"

    # Trình tự đúng như apps/cosa/api/routes.py::cancel_run: repository trước
    # (authority), kernel.cancel() sau (fast-path in-process), CÙNG 1 reason.
    cancelled_record = await repo.cancel_run(run.run_id, reason=identity_reason)
    assert cancelled_record is not None
    assert cancelled_record.status == RunStatus.CANCELLED

    kernel_result = await kernel.cancel(run.run_id, reason=identity_reason)
    # CANCELLED -> CANCELLED vẫn là 1 CAS "thành công" (idempotent).
    assert kernel_result is True

    final_record = await repo.get_run(run.run_id)
    assert final_record.status == RunStatus.CANCELLED
    assert final_record.error_details == {"reason": identity_reason}


class _RaisingModelClient:
    """Mock provider client mô phỏng lỗi network/API — dùng để chứng minh kernel
    không còn convert provider failure thành assistant content COMPLETED
    (Blueprint V2 §56 anti-pattern; xem ADR-RUNTIME-001, Wave 1 C.3)."""

    class _RaisingCompletions:
        async def create(self, **kwargs):
            raise ConnectionError("simulated provider outage")

    @property
    def chat(self):
        class _Chat:
            completions = _RaisingModelClient._RaisingCompletions()

        return _Chat()


@pytest.mark.asyncio
async def test_kernel_model_provider_failure_is_typed_failed_not_completed():
    """Provider exception phải map thành RunResult FAILED có structured error_details
    (code=MODEL_PROVIDER_ERROR), run.failed event, và RunRecord.status=FAILED durable
    — không được trở thành RunResult COMPLETED với final_output chứa text lỗi."""
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=_RaisingModelClient())

    spec = AgentSpec(
        id="general_assistant",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "trigger provider failure"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.final_output is None
    assert result.errors and "simulated provider outage" in result.errors[0]

    run_rec = await repo.get_run(result.run_id)
    assert run_rec.status == RunStatus.FAILED
    assert run_rec.error_details is not None
    assert run_rec.error_details["code"] == RuntimeErrorCode.MODEL_PROVIDER_ERROR.value

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.failed" in event_types
    assert "message.delta" not in event_types
    assert "run.completed" not in event_types


class _CapturingModelClient:
    """Mock provider client ghi lại `messages` gửi tới model — dùng để verify
    PromptBundle (platform policy + agent instructions + locale policy) thực sự
    được compose vào system message (Wave 3 — Blueprint V2 §68)."""

    def __init__(self) -> None:
        self.captured_messages: list[dict] = []

    class _Completions:
        def __init__(self, outer: _CapturingModelClient) -> None:
            self._outer = outer

        async def create(self, model="deepseek-chat", messages=None, temperature=0.0, **kwargs):
            self._outer.captured_messages = messages or []

            class _Msg:
                content = "OK"
                tool_calls: list = []

            class _Choice:
                message = _Msg()

            class _Resp:
                choices = [_Choice()]
                usage = None

            return _Resp()

    @property
    def chat(self):
        class _Chat:
            def __init__(self, outer: _CapturingModelClient) -> None:
                self.completions = _CapturingModelClient._Completions(outer)

        return _Chat(self)


@pytest.mark.asyncio
async def test_kernel_run_composes_system_prompt_with_locale_policy():
    repo = InMemoryRunRepository()
    client = _CapturingModelClient()
    kernel = ManualToolLoopKernel(repository=repo, model_client=client)

    spec = AgentSpec(
        id="test.agent.locale_1",
        version="1.0.0",
        instructions="Bạn là trợ lý tài chính.",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Xin chào"},
        locale="en-US",
    )

    await kernel.run(request, spec)

    system_msg = client.captured_messages[0]
    assert system_msg["role"] == "system"
    assert "Bạn là trợ lý tài chính." in system_msg["content"]
    assert "preferred locale is en-US" in system_msg["content"]
    assert "COSA" in system_msg["content"]  # platform policy luôn có mặt


@pytest.mark.asyncio
async def test_kernel_allow_path_tool_execution_preserves_real_run_and_tool_call_id():
    """Trước fix: nhánh fallback GatewayExecutionRequest trong _execute_tool() tự
    sinh run_id/tool_call_id NGẪU NHIÊN MỚI thay vì dùng đúng identity của lần gọi
    đang xử lý — phá vỡ invariant exact (run_id, tool_call_id) xuyên suốt
    kernel→gateway (Blueprint V2 §8.2) và sẽ gây lỗi FK trên Postgres thật (run_id
    giả không tồn tại trong agent.runs). InMemoryRunRepository không phát hiện
    vì không có FK — test này verify trực tiếp giá trị run_id trong ledger, không
    dựa vào FK enforcement."""
    repo = InMemoryRunRepository()

    registry = CapabilityRegistry()
    read_spec = CapabilitySpec(
        id="operations.task.list",
        risk=CapabilityRisk.LOW,
        input_schema={"type": "object", "properties": {}},
    )

    def list_handler(payload, ctx):
        return {"tasks": [], "total": 0}

    registry.register(read_spec, list_handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    # capability_executor=gateway.execute là hàm 1 tham số (GatewayExecutionRequest)
    # -> gọi 2 tham số (tool_name, args) sẽ raise TypeError -> rơi vào nhánh fallback
    # đang được fix trong test này.
    kernel = ManualToolLoopKernel(repository=repo, capability_executor=gateway.execute, model_client=MockToolLoopModelClient())

    spec = AgentSpec(
        id="test.agent.tool_identity_1",
        version="1.0.0",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "List operations tasks please"},  # kích hoạt mock tool call
    )

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED

    tool_calls = await repo.list_tool_calls(result.run_id)
    assert len(tool_calls) == 1
    assert tool_calls[0].run_id == result.run_id  # KHÔNG phải "run_tool_xxxxxxxx" ngẫu nhiên
    assert tool_calls[0].status == "completed"


@pytest.mark.asyncio
async def test_kernel_fails_closed_when_gateway_denies_instead_of_fake_success():
    """Bug 1.1 (ManualToolLoopKernel): policy_evaluator/decision ở kernel là ALLOW
    (LOW risk, không cần approval), nhưng CapabilityGateway THẬT lại từ chối/thất
    bại khi thực thi — trước fix, _execute_tool trả res.output_payload nguyên
    trạng (None nếu handler raise, không set) mà không kiểm res.status, khiến
    reasoning loop tưởng tool đã chạy thành công."""
    repo = InMemoryRunRepository()

    registry = CapabilityRegistry()
    read_spec = CapabilitySpec(
        id="operations.task.list",
        risk=CapabilityRisk.LOW,
        input_schema={"type": "object", "properties": {}},
    )

    def failing_handler(payload, ctx):
        raise RuntimeError("connector grant revoked")

    registry.register(read_spec, failing_handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    kernel = ManualToolLoopKernel(
        repository=repo, capability_executor=gateway.execute, model_client=MockToolLoopModelClient()
    )

    spec = AgentSpec(
        id="test.agent.gateway_denied_1",
        version="1.0.0",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "List operations tasks please"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    tool_calls = await repo.list_tool_calls(result.run_id)
    assert tool_calls[0].status == "failed"


@pytest.mark.asyncio
async def test_kernel_raises_typed_error_when_model_client_not_configured():
    """Không còn silent mock fallback — thiếu model_client phải là RunResult
    FAILED có structured error, không phải response giả (COSA_PRODUCTION_
    RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §3.2)."""
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo)

    spec = AgentSpec(
        id="general_assistant",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Hello world"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.errors and "model_client" in result.errors[0]

    run_rec = await repo.get_run(result.run_id)
    assert run_rec.error_details["code"] == RuntimeErrorCode.MODEL_PROVIDER_ERROR.value


@pytest.mark.asyncio
async def test_kernel_output_schema_validation_success():
    """Kernel run với output_schema được set thành công validate valid JSON output."""
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    spec = AgentSpec(
        id="validator_agent",
        instructions="Validate and return structured output.",
        model_input_capability_ref="model.input.direct-user-message",
        output_schema={
            "type": "object",
            "required": ["score", "verdict"],
            "properties": {
                "score": {"type": "integer"},
                "verdict": {"type": "string"},
            },
        },
    )

    # Mock client sẽ return JSON output without tool calls
    class _OutputSchemaMockClient:
        class _Completions:
            async def create(self, **kwargs):
                class _Msg:
                    content = '{"score": 95, "verdict": "pass"}'
                    tool_calls = []

                class _Choice:
                    message = _Msg()

                class _Resp:
                    choices = [_Choice()]
                    usage = None

                return _Resp()

        @property
        def chat(self):
            class _Chat:
                completions = _OutputSchemaMockClient._Completions()

            return _Chat()

    kernel_with_mock = ManualToolLoopKernel(
        repository=repo, model_client=_OutputSchemaMockClient()
    )

    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Validate this"},
    )

    result = await kernel_with_mock.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert isinstance(result.final_output, dict)
    assert result.final_output["score"] == 95
    assert result.final_output["verdict"] == "pass"

    # Verify event was logged
    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.completed" in event_types
    assert "run.failed" not in event_types


@pytest.mark.asyncio
async def test_kernel_output_schema_validation_failure():
    """Kernel run với output_schema detect invalid JSON output và fail run."""
    repo = InMemoryRunRepository()

    spec = AgentSpec(
        id="validator_agent_fail",
        instructions="Validate and return structured output.",
        model_input_capability_ref="model.input.direct-user-message",
        output_schema={
            "type": "object",
            "required": ["score", "verdict"],
            "properties": {
                "score": {"type": "integer"},
                "verdict": {"type": "string"},
            },
        },
    )

    # Mock client returns output that fails schema validation
    class _FailingOutputSchemaMockClient:
        class _Completions:
            async def create(self, **kwargs):
                class _Msg:
                    # Missing 'verdict' field — validation should fail
                    content = '{"score": "not_a_number"}'
                    tool_calls = []

                class _Choice:
                    message = _Msg()

                class _Resp:
                    choices = [_Choice()]
                    usage = None

                return _Resp()

        @property
        def chat(self):
            class _Chat:
                completions = _FailingOutputSchemaMockClient._Completions()

            return _Chat()

    kernel = ManualToolLoopKernel(
        repository=repo, model_client=_FailingOutputSchemaMockClient()
    )

    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "This should fail validation"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.errors
    assert any("validation" in err.lower() for err in result.errors)
    # final_output ở đây sẽ là ValidationFailure dict (có is_valid=False)
    assert result.final_output is not None
    assert result.final_output.get("is_valid") is False

    # Verify run record was marked FAILED
    run_rec = await repo.get_run(result.run_id)
    assert run_rec.status == RunStatus.FAILED

    # Verify event was logged
    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.failed" in event_types
    assert "run.completed" not in event_types


@pytest.mark.asyncio
async def test_kernel_output_schema_skip_when_not_set():
    """Kernel run không có output_schema ignore validation và complete normally."""
    repo = InMemoryRunRepository()

    spec = AgentSpec(
        id="no_schema_agent",
        instructions="Just return text.",
        model_input_capability_ref="model.input.direct-user-message",
        # Deliberately NO output_schema set
    )

    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Hello"},
    )

    result = await kernel.run(request, spec)

    # Should complete successfully without validation since no schema
    assert result.status == RunStatus.COMPLETED
    assert "Processed: Hello" in str(result.final_output)


@pytest.mark.asyncio
async def test_kernel_output_schema_with_markdown_code_block():
    """Kernel extract JSON từ markdown code block khi validate schema."""
    repo = InMemoryRunRepository()

    spec = AgentSpec(
        id="markdown_schema_agent",
        instructions="Return JSON in markdown code block.",
        model_input_capability_ref="model.input.direct-user-message",
        output_schema={
            "type": "object",
            "required": ["status"],
            "properties": {"status": {"type": "string"}},
        },
    )

    # Mock client returns JSON wrapped in markdown code block
    class _MarkdownOutputMockClient:
        class _Completions:
            async def create(self, **kwargs):
                class _Msg:
                    content = '```json\n{"status": "ok"}\n```'
                    tool_calls = []

                class _Choice:
                    message = _Msg()

                class _Resp:
                    choices = [_Choice()]
                    usage = None

                return _Resp()

        @property
        def chat(self):
            class _Chat:
                completions = _MarkdownOutputMockClient._Completions()

            return _Chat()

    kernel = ManualToolLoopKernel(
        repository=repo, model_client=_MarkdownOutputMockClient()
    )

    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Get status"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert isinstance(result.final_output, dict)
    assert result.final_output["status"] == "ok"
