"""Conformance test cho LangChainKernel (Wave 4) — theo checklist Blueprint V2 §46/§74:
response cơ bản, single tool call, approval pause/resume, provider failure typed,
cancellation, exact (run_id, tool_call_id) giữ nguyên. Dùng FakeLangChainChatModel
(duck-typed, không cần API key/network) — không test conformance thật với DeepSeek
provider (cần credential thật, ngoài phạm vi test tự động trong môi trường này).
"""
from __future__ import annotations

from typing import Any, Callable, Union

import pytest

# langchain-core/langchain-deepseek là optional adapter dependency (ADR-
# RUNTIME-002 — LangChain không phải runtime chính, agent_core/apps.cosa
# không bắt buộc cài trừ khi thực sự chọn runtime="langchain"). CI job
# `agent-core` chỉ cài packages/agent_core/requirements.txt, không có
# langchain-core — skip module thay vì làm ImportError sập toàn bộ test
# collection của cả job (Phase 6 CI Green Gate).
_langchain_messages = pytest.importorskip("langchain_core.messages")
AIMessage = _langchain_messages.AIMessage
BaseMessage = _langchain_messages.BaseMessage

from agent_core.capabilities.gateway import CapabilityGateway
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import CapabilityRisk
from agent_core.runs.repository import InMemoryRunRepository

from agent_integrations.langchain.kernel import LangChainKernel


class FakeLangChainChatModel:
    """Duck-typed fake cho `BaseChatModel` — chỉ implement `ainvoke`/`bind_tools`,
    đủ cho LangChainKernel, không cần kế thừa lớp trừu tượng đầy đủ của LangChain."""

    def __init__(self, responses: Union[list[AIMessage], Callable[[list[BaseMessage]], AIMessage]]) -> None:
        self._responses = responses
        self._call_index = 0
        self.captured_invocations: list[list[BaseMessage]] = []
        self.bound_tools: list[dict[str, Any]] = []

    def bind_tools(self, tools: list[dict[str, Any]]) -> "FakeLangChainChatModel":
        self.bound_tools = tools
        return self

    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
        self.captured_invocations.append(list(messages))
        if callable(self._responses):
            result = self._responses(messages)
            if hasattr(result, "__await__"):
                result = await result
            return result
        resp = self._responses[self._call_index]
        self._call_index += 1
        return resp


@pytest.mark.asyncio
async def test_langchain_kernel_basic_response():
    fake_model = FakeLangChainChatModel([AIMessage(content="Xin chào, tôi có thể giúp gì?")])
    repo = InMemoryRunRepository()
    kernel = LangChainKernel(repository=repo, chat_model=fake_model)

    spec = AgentSpec(id="test.lc.basic", version="1.0.0", instructions="Bạn là trợ lý.")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Xin chào"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert result.final_output == "Xin chào, tôi có thể giúp gì?"

    # System message phải chứa platform policy + agent instructions + locale policy (PromptBundle)
    system_msg = fake_model.captured_invocations[0][0]
    assert system_msg.type == "system"
    assert "Bạn là trợ lý." in system_msg.content
    assert "preferred locale is vi-VN" in system_msg.content


@pytest.mark.asyncio
async def test_langchain_kernel_model_provider_failure_is_typed_failed_not_completed():
    async def _raise(messages):
        raise ConnectionError("simulated DeepSeek outage")

    fake_model = FakeLangChainChatModel(_raise)
    repo = InMemoryRunRepository()
    kernel = LangChainKernel(repository=repo, chat_model=fake_model)

    spec = AgentSpec(id="test.lc.failure", version="1.0.0")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "trigger failure"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.final_output is None
    assert result.errors and "simulated DeepSeek outage" in result.errors[0]

    run_rec = await repo.get_run(result.run_id)
    assert run_rec.status == RunStatus.FAILED
    assert run_rec.error_details["code"] == "MODEL_PROVIDER_ERROR"

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.failed" in event_types
    assert "run.completed" not in event_types


@pytest.mark.asyncio
async def test_langchain_kernel_tool_call_allow_path_preserves_exact_identity():
    registry = CapabilityRegistry()
    read_spec = CapabilitySpec(
        id="operations.task.list",
        risk=CapabilityRisk.LOW,
        input_schema={"type": "object", "properties": {}},
    )

    def list_handler(payload, ctx):
        return {"tasks": [], "total": 0}

    registry.register(read_spec, list_handler)
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repo)

    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "operations.task.list", "args": {}, "id": "call_lc_1", "type": "tool_call"}],
    )
    final_msg = AIMessage(content="Danh sách task hiện đang trống.")
    fake_model = FakeLangChainChatModel([tool_call_msg, final_msg])

    kernel = LangChainKernel(repository=repo, chat_model=fake_model, capability_executor=gateway.execute)

    spec = AgentSpec(id="test.lc.tool_call", version="1.0.0", capability_refs=["operations.task.list"])
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "List operations tasks"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert result.final_output == "Danh sách task hiện đang trống."

    tool_calls = await repo.list_tool_calls(result.run_id)
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_call_id == "call_lc_1"
    assert tool_calls[0].run_id == result.run_id  # exact identity, không random
    assert tool_calls[0].status == "completed"


@pytest.mark.asyncio
async def test_langchain_kernel_approval_pause_and_resume():
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "finance.payout.execute", "args": {"amount": 5000}, "id": "call_lc_payout_1", "type": "tool_call"}],
    )
    final_msg = AIMessage(content="Đã thực hiện thanh toán.")
    fake_model = FakeLangChainChatModel([tool_call_msg, final_msg])

    repo = InMemoryRunRepository()
    kernel = LangChainKernel(repository=repo, chat_model=fake_model)

    spec = AgentSpec(id="test.lc.approval", version="1.0.0")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Execute payout of 5000"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.WAITING_APPROVAL
    assert result.interruptions_waits
    ckpt_ref = result.interruptions_waits[0].checkpoint_ref

    resumed = await kernel.resume(run_id=result.run_id, checkpoint_ref=ckpt_ref, updates={"approved": True})

    assert resumed.status == RunStatus.COMPLETED
    assert resumed.final_output == "Đã thực hiện thanh toán."


@pytest.mark.asyncio
async def test_langchain_kernel_cancellation():
    fake_model = FakeLangChainChatModel([AIMessage(content="OK")])
    repo = InMemoryRunRepository()
    kernel = LangChainKernel(repository=repo, chat_model=fake_model)

    spec = AgentSpec(id="test.lc.cancel", version="1.0.0")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "start"},
    )
    res = await kernel.run(request, spec)
    assert res.status == RunStatus.COMPLETED

    cancelled = await kernel.cancel(res.run_id, reason="User cancelled")
    assert cancelled is True

    run_rec = await repo.get_run(res.run_id)
    assert run_rec.status == RunStatus.CANCELLED
