"""Conformance test cho `GoogleAdkKernel` — PHẠM VI THU HẸP so với
`test_langchain_kernel.py`/`test_openai_agents_sdk_kernel.py`/
`test_pydantic_ai_kernel.py` (chỉ 3/5 test shape, xem docstring
`GoogleAdkKernel` để biết lý do approval-pause/resume + cancellation chưa
implement). Dùng `FakeAdkLlm` (subclass `BaseLlm` thật) — không cần API key
thật."""
from __future__ import annotations

import pytest

pytest.importorskip("google.adk")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent_integrations.google_adk.kernel import GoogleAdkKernel
from google.adk.models import BaseLlm, LlmResponse
from google.genai import types as genai_types


class FakeAdkLlm(BaseLlm):
    """`BaseLlm` là Pydantic model — không gán field ngoài schema được, nên
    dùng dict đóng gói mutable state (`_state`) thay vì instance attribute
    thường (phát hiện lần đầu chạy thật: gán `self.call_count` trực tiếp bị
    Pydantic chặn với `ValueError: object has no field`)."""

    model: str = "fake-adk-model"
    responses: list = []
    error: Exception | None = None
    state: dict = {}

    class Config:
        arbitrary_types_allowed = True

    async def generate_content_async(self, llm_request, stream: bool = False):
        self.state["call_count"] = self.state.get("call_count", 0) + 1
        if self.error:
            raise self.error
        if not self.responses:
            yield LlmResponse(content=genai_types.Content(role="model", parts=[genai_types.Part(text="no more responses")]))
            return
        yield self.responses.pop(0)


def _text_response(text: str) -> LlmResponse:
    return LlmResponse(content=genai_types.Content(role="model", parts=[genai_types.Part(text=text)]))


def _tool_call_response(call_id: str, tool_name: str, args: dict) -> LlmResponse:
    return LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[genai_types.Part(function_call=genai_types.FunctionCall(name=tool_name, args=args, id=call_id))],
        )
    )


def _make_spec(capability_refs: list[str] | None = None) -> AgentSpec:
    spec = AgentSpec(
        id="test_agent_adk",
        version="1.0.0",
        instructions="You are a test agent.",
        capability_refs=capability_refs or [],
    )
    return spec.with_hash()


def _make_request(prompt: str, spec: AgentSpec) -> RunRequest:
    return RunRequest(
        input={"prompt": prompt},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_test",
    )


@pytest.mark.asyncio
async def test_adk_kernel_basic_response():
    model = FakeAdkLlm(responses=[_text_response("Hello from ADK")])
    kernel = GoogleAdkKernel(model=model)
    spec = _make_spec()

    result = await kernel.run(_make_request("hi", spec), spec)

    assert result.status == RunStatus.COMPLETED
    assert "Hello from ADK" in str(result.final_output)


@pytest.mark.asyncio
async def test_adk_kernel_model_provider_failure_is_typed_failed_not_completed():
    model = FakeAdkLlm(error=RuntimeError("simulated provider outage"))
    kernel = GoogleAdkKernel(model=model)
    spec = _make_spec()

    result = await kernel.run(_make_request("hi", spec), spec)

    assert result.status == RunStatus.FAILED
    assert result.errors
    assert "simulated" in result.errors[0] or "outage" in result.errors[0]


@pytest.mark.asyncio
async def test_adk_kernel_tool_call_allow_path_preserves_exact_identity():
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="weather_get", description="Get weather", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    captured: dict[str, str] = {}

    async def capability_executor(tool_name: str, args: dict) -> dict:
        captured["tool_name"] = tool_name
        return {"temp_c": 21}

    call_id = "call_exact_id_adk_1"
    model = FakeAdkLlm(
        responses=[
            _tool_call_response(call_id, "weather_get", {"city": "Hanoi"}),
            _text_response("It is 21C"),
        ]
    )
    kernel = GoogleAdkKernel(model=model, capability_registry=registry, capability_executor=capability_executor)
    spec = _make_spec(capability_refs=["weather_get"])

    result = await kernel.run(_make_request("what is the weather", spec), spec)

    assert result.status == RunStatus.COMPLETED
    assert captured["tool_name"] == "weather_get"


@pytest.mark.asyncio
async def test_adk_kernel_resume_and_cancel_are_explicitly_unimplemented():
    """Xác nhận kernel KHÔNG giả vờ hỗ trợ approval-pause/resume/cancel —
    raise `NotImplementedError` tường minh thay vì âm thầm no-op hoặc trả kết
    quả sai (xem docstring `GoogleAdkKernel` về phạm vi thu hẹp có chủ đích)."""
    kernel = GoogleAdkKernel(model=FakeAdkLlm())

    with pytest.raises(NotImplementedError):
        await kernel.resume("run_x", "ckpt_x", {})

    with pytest.raises(NotImplementedError):
        await kernel.cancel("run_x")
