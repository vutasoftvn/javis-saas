"""Task 9 (audit follow-up round 3) — `LangChainKernel` được wire production
qua CÙNG config knob `runtime` (apps/cosa/composition/agent_plane.py:529,
`runtime == "langchain"`) y hệt cách chọn `openai_agents`/`manual_tool_loop` —
KHÔNG phải legacy/dead code. Kernel này tự emit `tool.completed`/
`run.completed`/`message.delta` vào CÙNG bảng `agent.run_events` mà
`CapabilityGateway` ghi, phải redact/hash y hệt.
"""

from __future__ import annotations

import importlib.util
import json

import pytest

if importlib.util.find_spec("langchain_core") is None:
    pytest.skip(
        "langchain_core is not installed — skipping LangChain redaction tests",
        allow_module_level=True,
    )

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.langchain.kernel import LangChainKernel
from langchain_core.messages import AIMessage

PII_EMAIL = "customer@example.com"
PII_SECRET = "Bearer secret-token-should-not-leak"


class _FakeChatModel:
    """Stub tối thiểu cho `BaseChatModel` — chỉ cần `bind_tools()` (trả về
    self) và `ainvoke()` (trả về AIMessage theo kịch bản đã cấu hình), không
    cần LLM thật."""

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    def bind_tools(self, tool_schemas):  # noqa: ANN001 - stub, ký hiệu không quan trọng
        return self

    async def ainvoke(self, messages):  # noqa: ANN001
        resp = self._responses[self._call_count]
        self._call_count += 1
        return resp


def _build_spec(cap_refs: list[str] | None = None) -> AgentSpec:
    return AgentSpec(
        id="test_lc_redaction_agent",
        version="1.0.0",
        instructions="You are a test agent.",
        capability_refs=cap_refs or [],
    ).with_hash()


def _build_request(prompt: str, spec: AgentSpec) -> RunRequest:
    return RunRequest(
        input={"prompt": prompt},
        principal="test-lc-redaction-runner",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_lc_redact",
    )


@pytest.mark.asyncio
async def test_langchain_kernel_tool_completed_event_does_not_leak_raw_pii() -> None:
    """`LangChainKernel._run_reasoning_turns` emit `tool.completed` — output
    thô (PII/secret) của tool call KHÔNG được xuất hiện trong
    RunEventRecord.payload persist Postgres, chỉ được phép có hash."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.customer.lookup",
        description="Lookup customer",
        input_schema={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    )
    registry.register(cap, lambda args: {})

    async def executor(tool_name: str, args: dict) -> dict:
        return {
            "customer_id": args.get("customer_id"),
            "email": PII_EMAIL,
            "auth_header": PII_SECRET,
        }

    call_id = "call_lookup_lc_1"
    chat_model = _FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"id": call_id, "name": "finance.customer.lookup", "args": {"customer_id": "c1"}}
                ],
            ),
            AIMessage(content="Lookup done"),
        ]
    )

    kernel = LangChainKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=executor,
        chat_model=chat_model,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = _build_spec(cap_refs=["finance.customer.lookup"])
    request = _build_request("lookup customer c1", spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED

    events = await repo.list_events(result.run_id)
    completed = [e for e in events if e.event_type == "tool.completed"]
    assert len(completed) == 1
    event = completed[0]

    dumped = json.dumps(event.model_dump(mode="json"))
    assert PII_EMAIL not in dumped
    assert PII_SECRET not in dumped
    assert "secret-token-should-not-leak" not in dumped

    assert "result" not in event.payload
    output_hash = event.payload.get("output_hash")
    assert isinstance(output_hash, str) and len(output_hash) == 64
    assert event.payload.get("output_present") is True


@pytest.mark.asyncio
async def test_langchain_kernel_run_completed_and_message_delta_do_not_leak_raw_content() -> None:
    """`run.completed` và `message.delta` (LangChainKernel._run_reasoning_turns)
    không được ghi nội dung/final_output thô vào audit event."""
    repo = InMemoryRunRepository()
    final_text = f"Here is the contact: {PII_EMAIL}"
    chat_model = _FakeChatModel(responses=[AIMessage(content=final_text)])
    kernel = LangChainKernel(repository=repo, chat_model=chat_model)
    spec = _build_spec()
    request = _build_request("give me contact info", spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED
    # Kênh thật (RunResult.final_output) vẫn giữ nguyên nội dung thô.
    assert PII_EMAIL in str(result.final_output)

    events = await repo.list_events(result.run_id)

    run_completed = [e for e in events if e.event_type == "run.completed"]
    assert len(run_completed) == 1
    dumped_run = json.dumps(run_completed[0].model_dump(mode="json"))
    assert PII_EMAIL not in dumped_run
    assert "final_output" not in run_completed[0].payload
    final_hash = run_completed[0].payload.get("final_output_hash")
    assert isinstance(final_hash, str) and len(final_hash) == 64
    assert run_completed[0].payload.get("final_output_present") is True

    message_delta = [e for e in events if e.event_type == "message.delta"]
    assert len(message_delta) == 1
    dumped_msg = json.dumps(message_delta[0].model_dump(mode="json"))
    assert PII_EMAIL not in dumped_msg
    assert "content" not in message_delta[0].payload
    content_hash = message_delta[0].payload.get("content_hash")
    assert isinstance(content_hash, str) and len(content_hash) == 64
    assert message_delta[0].payload.get("content_present") is True
