"""Task 9 (audit follow-up) — `RealOpenAIAgentsSDKKernel` là kernel mặc định
production thật (wire tại apps/cosa/composition/agent_plane.py qua
runtime == "openai_agents"), khác với `ManualToolLoopKernel` (legacy,
packages/agent/kernel/openai_agents_kernel.py, opt-in). Kernel này tự emit
`tool.completed`/`run.completed` vào CÙNG bảng `agent.run_events` mà
`CapabilityGateway` ghi — phải redact/hash y hệt, không chỉ vá gateway.py.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("agents")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response

PII_EMAIL = "customer@example.com"
PII_SECRET = "Bearer secret-token-should-not-leak"


def _build_spec(cap_refs: list[str] | None = None) -> AgentSpec:
    return AgentSpec(
        id="test_redaction_agent",
        version="1.0.0",
        instructions="You are a test agent.",
        capability_refs=cap_refs or [],
    ).with_hash()


def _build_request(prompt: str, spec: AgentSpec) -> RunRequest:
    return RunRequest(
        input={"prompt": prompt},
        principal="test-redaction-runner",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_redact",
    )


@pytest.mark.asyncio
async def test_real_sdk_kernel_tool_completed_event_does_not_leak_raw_pii() -> None:
    """`RealOpenAIAgentsSDKKernel._make_tool._on_invoke` emit `tool.completed`
    — output thô (PII/secret) của tool call KHÔNG được xuất hiện trong
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

    call_id = "call_lookup_1"
    model = FakeSDKModel(
        responses=[
            tool_call_response(call_id, "finance.customer.lookup", arguments='{"customer_id": "c1"}'),
            text_response("Lookup done"),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=executor,
        model=model,
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

    assert "output" not in event.payload
    assert "result" not in event.payload
    output_hash = event.payload.get("output_hash")
    assert isinstance(output_hash, str) and len(output_hash) == 64
    assert event.payload.get("output_present") is True


@pytest.mark.asyncio
async def test_real_sdk_kernel_run_completed_event_does_not_leak_raw_final_output() -> None:
    """`run.completed` (RealOpenAIAgentsSDKKernel._invoke_and_translate) không
    được ghi `final_output` thô vào audit event — chỉ hash."""
    repo = InMemoryRunRepository()
    model = FakeSDKModel(responses=[text_response(f"Contact: {PII_EMAIL}")])
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, model=model)
    spec = _build_spec()
    request = _build_request("give me contact info", spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED
    # Kênh thật (RunResult/RunRecord.final_output) vẫn giữ nguyên nội dung thô.
    assert PII_EMAIL in str(result.final_output)

    events = await repo.list_events(result.run_id)
    completed = [e for e in events if e.event_type == "run.completed"]
    assert len(completed) == 1
    event = completed[0]

    dumped = json.dumps(event.model_dump(mode="json"))
    assert PII_EMAIL not in dumped
    assert "final_output" not in event.payload
    final_hash = event.payload.get("final_output_hash")
    assert isinstance(final_hash, str) and len(final_hash) == 64
    assert event.payload.get("final_output_present") is True


@pytest.mark.asyncio
async def test_real_sdk_kernel_run_failed_event_does_not_leak_raw_exception_message() -> None:
    """`run.failed` (nhánh Exception trong `_invoke_and_translate`) không được
    ghi `str(e)` thô — vì exception message có thể echo lại input/output."""
    repo = InMemoryRunRepository()
    model = FakeSDKModel(error=ConnectionResetError(f"Failed for {PII_EMAIL}: {PII_SECRET}"))
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, model=model)
    spec = _build_spec()
    request = _build_request("trigger failure", spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.FAILED
    # RunResult.errors (trả cho caller thật) vẫn giữ message thật để debug.
    assert any(PII_EMAIL in err for err in result.errors)

    events = await repo.list_events(result.run_id)
    failed = [e for e in events if e.event_type == "run.failed"]
    assert len(failed) == 1
    event = failed[0]

    dumped = json.dumps(event.model_dump(mode="json"))
    assert PII_EMAIL not in dumped
    assert PII_SECRET not in dumped
    assert "error" not in event.payload
    assert event.payload.get("error_type") == "ConnectionResetError"
    error_hash = event.payload.get("error_hash")
    assert isinstance(error_hash, str) and len(error_hash) == 64
