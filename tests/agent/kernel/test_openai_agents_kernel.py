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
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient


@pytest.mark.asyncio
async def test_kernel_end_to_end_execution_and_event_logging():
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    spec = AgentSpec(
        id="general_assistant",
        instructions="You are a helpful assistant.",
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

    spec = AgentSpec(id="finance_agent", instructions="Handle payouts.")
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

    # 3. Resume với checkpoint_ref
    resumed = await kernel.resume(
        run_id=result.run_id,
        checkpoint_ref=ckpt_ref,
        updates={"approved": True},
    )

    assert resumed.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_kernel_cancellation():
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    spec = AgentSpec(id="long_agent")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Start task"},
    )

    # Tạo run record trước
    res = await kernel.run(request, spec)
    assert res.status == RunStatus.COMPLETED

    # Test cancel
    cancelled = await kernel.cancel(res.run_id, reason="User cancelled")
    assert cancelled is True

    run_rec = await repo.get_run(res.run_id)
    assert run_rec.status == RunStatus.CANCELLED


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

    spec = AgentSpec(id="general_assistant")
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
        def __init__(self, outer: "_CapturingModelClient") -> None:
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
            def __init__(self, outer: "_CapturingModelClient") -> None:
                self.completions = _CapturingModelClient._Completions(outer)

        return _Chat(self)


@pytest.mark.asyncio
async def test_kernel_run_composes_system_prompt_with_locale_policy():
    repo = InMemoryRunRepository()
    client = _CapturingModelClient()
    kernel = ManualToolLoopKernel(repository=repo, model_client=client)

    spec = AgentSpec(id="test.agent.locale_1", version="1.0.0", instructions="Bạn là trợ lý tài chính.")
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

    spec = AgentSpec(id="test.agent.tool_identity_1", version="1.0.0")
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
async def test_kernel_raises_typed_error_when_model_client_not_configured():
    """Không còn silent mock fallback — thiếu model_client phải là RunResult
    FAILED có structured error, không phải response giả (COSA_PRODUCTION_
    RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §3.2)."""
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo)

    spec = AgentSpec(id="general_assistant")
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
