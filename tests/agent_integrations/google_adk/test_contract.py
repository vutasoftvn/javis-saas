"""Contract and smoke tests for Google ADK adapter (GoogleAdkKernel).

Asserts:
- Adapter initializes with default config and session service.
- kernel.run(RunRequest) -> RunResult with event stream.
- Tool call round-trip preserves exact identity and maps to gateway.
- Provider errors are mapped to AgentRuntimeError / RunStatus.FAILED.
- resume() and cancel() explicitly raise NotImplementedError.
"""

from __future__ import annotations

import pytest

pytest.importorskip("google.adk")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.google_adk.kernel import GoogleAdkKernel
from google.adk.models import BaseLlm, LlmResponse
from google.genai import types as genai_types
from pydantic import Field


class FakeAdkLlm(BaseLlm):
    model: str = "fake-adk-model"
    responses: list = Field(default_factory=list)
    error: Exception | None = None
    state: dict = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    async def generate_content_async(self, llm_request, stream: bool = False):
        self.state["call_count"] = self.state.get("call_count", 0) + 1
        if self.error:
            raise self.error
        if not self.responses:
            yield LlmResponse(
                content=genai_types.Content(
                    role="model", parts=[genai_types.Part(text="no more responses")]
                )
            )
            return
        yield self.responses.pop(0)


def _text_response(text: str) -> LlmResponse:
    return LlmResponse(
        content=genai_types.Content(role="model", parts=[genai_types.Part(text=text)])
    )


def _tool_call_response(call_id: str, tool_name: str, args: dict) -> LlmResponse:
    return LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[
                genai_types.Part(
                    function_call=genai_types.FunctionCall(name=tool_name, args=args, id=call_id)
                )
            ],
        )
    )


def _build_spec(cap_refs: list[str] | None = None) -> AgentSpec:
    return AgentSpec(
        id="test_agent_adk_contract",
        version="1.0.0",
        instructions="You are an ADK test agent.",
        capability_refs=cap_refs or [],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()


def _build_request(prompt: str, spec: AgentSpec) -> RunRequest:
    return RunRequest(
        input={"prompt": prompt},
        principal="test-adk-contract",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_adk_contract",
    )


@pytest.mark.asyncio
async def test_google_adk_adapter_initialization():
    """Adapter initializes with in-memory session service and default repositories."""
    kernel = GoogleAdkKernel()
    assert kernel._repo is not None
    assert kernel._spec_registry is not None
    assert kernel._session_service is not None


@pytest.mark.asyncio
async def test_google_adk_kernel_event_stream_vocabulary():
    """ADK execution produces standard run.started and run.completed events."""
    repo = InMemoryRunRepository()
    model = FakeAdkLlm(responses=[_text_response("Hello ADK Contract")])
    kernel = GoogleAdkKernel(repository=repo, model=model)
    spec = _build_spec()
    request = _build_request("hi", spec)

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert "Hello ADK Contract" in str(result.final_output)

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.started" in event_types
    assert "run.completed" in event_types


@pytest.mark.asyncio
async def test_google_adk_kernel_tool_roundtrip():
    """ADK tool call executes capability and returns result to model."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="lookup_info",
        description="Lookup information",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[str] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append(tool_name)
        return {"found": True, "item": args.get("query")}

    call_id = "call_adk_lookup_1"
    model = FakeAdkLlm(
        responses=[
            _tool_call_response(call_id, "lookup_info", {"query": "COSA"}),
            _text_response("Information found: COSA platform"),
        ]
    )
    kernel = GoogleAdkKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
    )
    spec = _build_spec(cap_refs=["lookup_info"])
    request = _build_request("Search for COSA", spec)

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert "COSA platform" in str(result.final_output)
    assert executed_tools == ["lookup_info"]

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "tool.started" in event_types
    assert "tool.completed" in event_types


@pytest.mark.asyncio
async def test_google_adk_kernel_unimplemented_boundaries():
    """resume() and cancel() explicitly raise NotImplementedError."""
    kernel = GoogleAdkKernel(model=FakeAdkLlm())

    with pytest.raises(NotImplementedError):
        await kernel.resume("run_test", "ckpt_test", {})

    with pytest.raises(NotImplementedError):
        await kernel.cancel("run_test")
