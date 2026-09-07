"""Integration test for RealOpenAIAgentsSDKKernel checkpoint and resume with real tool schemas.

Covers:
1. Run execution encountering REQUIRE_APPROVAL policy pauses in WAITING_APPROVAL.
2. Checkpoint and RunApprovalRecord are stored with correct approval_id (`appr_{run_id}_{tool_call_id}`).
3. Resume with approved=True executes the tool and completes the run.
4. Resume with approved=False rejects the interruption and finishes/handles gracefully without crash.
5. Optional live DeepSeek test when DEEPSEEK_API_KEY is available.
"""

from __future__ import annotations

import json
import os

import pytest

pytest.importorskip("agents")

from agent.capabilities.gateway import GatewayExecutionRequest, GatewayExecutionResult
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import (
    FakeSDKModel,
    text_response,
    tool_call_response,
)


def _build_finance_spec() -> AgentSpec:
    return AgentSpec(
        id="finance_payout_agent",
        version="1.0.0",
        instructions="You are an authorized finance disbursement agent.",
        capability_refs=["finance.payout.execute"],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()


def _build_request(
    prompt: str = "Disburse payout $500", spec: AgentSpec | None = None
) -> RunRequest:
    s = spec or _build_finance_spec()
    return RunRequest(
        input={"prompt": prompt},
        principal="test-finance-lead",
        root_executable_ref=s.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_finance_test",
        metadata={"policy_snapshot": {"company_status": "active"}},
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_resume_approval_approved_path():
    """Checkpoint and resume on approved tool call."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}, "vendor": {"type": "string"}},
            "required": ["amount", "vendor"],
        },
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid", "transaction_ref": "tx_999"}

    call_id = "call_payout_chk_1"
    model = FakeSDKModel(
        responses=[
            tool_call_response(
                call_id,
                "finance.payout.execute",
                arguments='{"amount": 500, "vendor": "Acme Corp"}',
            ),
            text_response("Payout of $500 to Acme Corp successfully executed."),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    request = _build_request(spec=spec)

    # 1. First invocation pauses on approval
    result = await kernel.run(request, spec)

    assert result.status == RunStatus.WAITING_APPROVAL
    assert len(executed_tools) == 0
    assert result.interruptions_waits is not None
    assert len(result.interruptions_waits) == 1

    wait_desc = result.interruptions_waits[0]
    expected_appr_id = f"appr_{result.run_id}_{call_id}"
    assert wait_desc.related_ref == expected_appr_id

    # Verify saved checkpoint in repo
    checkpoint = await repo.get_checkpoint(wait_desc.checkpoint_ref)
    assert checkpoint is not None
    assert checkpoint.run_id == result.run_id

    # Verify approval record in repo
    approval = await repo.get_approval(expected_appr_id)
    assert approval is not None
    assert approval.status == "pending"
    assert approval.action == "finance.payout.execute"
    assert approval.tool_call_id == call_id

    # 2. Resume with approval
    resumed = await kernel.resume(
        result.run_id,
        wait_desc.checkpoint_ref,
        {"approved": True, "approved_tool_calls": {call_id: True}},
    )

    assert resumed.status == RunStatus.COMPLETED
    assert len(executed_tools) == 1
    assert executed_tools[0]["args"] == {"amount": 500, "vendor": "Acme Corp"}
    assert "Acme Corp" in str(resumed.final_output)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_resume_approval_rejected_path():
    """Checkpoint and resume on rejected tool call."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}, "vendor": {"type": "string"}},
            "required": ["amount", "vendor"],
        },
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid"}

    call_id = "call_payout_chk_reject"
    model = FakeSDKModel(
        responses=[
            tool_call_response(
                call_id,
                "finance.payout.execute",
                arguments='{"amount": 500, "vendor": "Acme Corp"}',
            ),
            text_response("Payout was rejected by finance lead."),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    request = _build_request(spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    wait_desc = result.interruptions_waits[0]

    # Resume with rejection — approved_tool_calls (per-call_id) là API duy nhất
    # có hiệu lực từ Bug 1.2 fix; field "approved": True/False blanket đã bị bỏ.
    resumed = await kernel.resume(
        result.run_id,
        wait_desc.checkpoint_ref,
        {"approved_tool_calls": {call_id: False}},
    )

    # Tool handler must NOT have been executed
    assert len(executed_tools) == 0
    # Status completed with graceful rejection acknowledgment
    assert resumed.status == RunStatus.COMPLETED
    assert "rejected" in str(resumed.final_output).lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_resume_fails_closed_when_pinned_spec_is_missing():
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            id="finance.payout.execute",
            description="Execute financial payout",
            input_schema={"type": "object", "properties": {}},
        ),
        lambda args: {},
    )
    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid"}

    call_id = "call_payout_missing_spec"
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=FakeSDKModel(
            responses=[
                tool_call_response(
                    call_id,
                    "finance.payout.execute",
                    arguments='{"amount": 500, "vendor": "Acme Corp"}',
                )
            ]
        ),
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    result = await kernel.run(_build_request(), _build_finance_spec())
    assert result.status == RunStatus.WAITING_APPROVAL

    kernel._spec_registry = InMemorySpecRegistryRepository()
    resumed = await kernel.resume(
        result.run_id,
        result.interruptions_waits[0].checkpoint_ref,
        {"approved": True, "approved_tool_calls": {call_id: True}},
    )

    assert resumed.status == RunStatus.FAILED
    assert resumed.errors == ["PINNED_AGENT_SPEC_NOT_FOUND"]
    assert executed_tools == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_resume_fails_closed_when_pinned_spec_content_is_stale():
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            id="finance.payout.execute",
            description="Execute financial payout",
            input_schema={"type": "object", "properties": {}},
        ),
        lambda args: {},
    )
    call_id = "call_payout_stale_spec"
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        model=FakeSDKModel(
            responses=[
                tool_call_response(
                    call_id,
                    "finance.payout.execute",
                    arguments='{"amount": 500, "vendor": "Acme Corp"}',
                )
            ]
        ),
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    result = await kernel.run(_build_request(spec=spec), spec)
    assert result.status == RunStatus.WAITING_APPROVAL

    stale_registry = InMemorySpecRegistryRepository()
    await stale_registry.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id=spec.id,
            version=spec.version,
            definition_hash=spec.definition_hash or spec.compute_hash(),
            # "id" là field bắt buộc duy nhất không có default trên AgentSpec
            # (model_input_capability_ref đã là str | None = None nên loại nó
            # ra không còn tạo ValidationError) — exclude "id" để content thật
            # sự thiếu field bắt buộc, mô phỏng đúng kịch bản stale/corrupt.
            content=spec.model_dump(mode="json", exclude={"id"}),
            status="published",
        )
    )
    kernel._spec_registry = stale_registry

    resumed = await kernel.resume(
        result.run_id,
        result.interruptions_waits[0].checkpoint_ref,
        {"approved_tool_calls": {call_id: True}},
    )

    assert resumed.status == RunStatus.FAILED
    assert resumed.errors == ["PINNED_AGENT_SPEC_INVALID"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_run_fails_closed_when_gateway_denies_instead_of_fake_success():
    """Bug 1.1: khi capability_executor thật (chữ ký GatewayExecutionRequest ->
    GatewayExecutionResult, đường mà production dùng qua CapabilityGateway) trả
    status != "completed" (denied/waiting_approval/failed), kernel KHÔNG được
    fabricate {"status": "success", ...} — phải fail closed."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}, "vendor": {"type": "string"}},
            "required": ["amount", "vendor"],
        },
    )
    registry.register(cap, lambda args: {})

    async def capability_executor(req: GatewayExecutionRequest) -> GatewayExecutionResult:
        # Chữ ký chỉ nhận 1 GatewayExecutionRequest -> gọi kiểu (tool_name, args,
        # inv_ctx) và (tool_name, args) đều TypeError, buộc kernel rơi vào nhánh
        # gateway thật (kernel.py dòng ~307-324) thay vì nhánh shim 2-arg.
        return GatewayExecutionResult(
            tool_call_id=req.tool_call_id,
            status="denied",
            error_message="blocked by ambient governance",
        )

    call_id = "call_payout_denied_1"
    model = FakeSDKModel(
        responses=[
            tool_call_response(
                call_id,
                "finance.payout.execute",
                arguments='{"amount": 500, "vendor": "Acme Corp"}',
            ),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = _build_finance_spec()
    request = _build_request(spec=spec)

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.final_output is None or "success" not in json.dumps(result.final_output)
    run_record = await repo.get_run(result.run_id)
    assert run_record.status == RunStatus.FAILED


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resume_does_not_approve_other_pending_tool_call_in_same_checkpoint():
    """Bug 1.2: 1 turn sinh 2 tool call cùng cần approval, cùng checkpoint_ref.
    Duyệt tool call 1 KHÔNG được tự động chạy luôn tool call 2 chưa từng được
    reviewer quyết định."""
    from agents.models.interface import ModelResponse
    from agents.usage import Usage
    from openai.types.responses import ResponseFunctionToolCall

    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}, "vendor": {"type": "string"}},
        },
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid"}

    call_id_1 = "call_multi_1"
    call_id_2 = "call_multi_2"
    two_calls_response = ModelResponse(
        output=[
            ResponseFunctionToolCall(
                id="fc_1", call_id=call_id_1, name="finance.payout.execute",
                arguments='{"amount": 100, "vendor": "Vendor A"}', type="function_call", status="completed",
            ),
            ResponseFunctionToolCall(
                id="fc_2", call_id=call_id_2, name="finance.payout.execute",
                arguments='{"amount": 200, "vendor": "Vendor B"}', type="function_call", status="completed",
            ),
        ],
        usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15),
        response_id="resp_multi",
    )
    model = FakeSDKModel(responses=[two_calls_response, text_response("both handled")])

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    request = _build_request(spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    assert len(result.interruptions_waits) == 2
    ckpt_ref = result.interruptions_waits[0].checkpoint_ref
    assert result.interruptions_waits[1].checkpoint_ref == ckpt_ref

    # Duyệt CHỈ call_id_1
    resumed = await kernel.resume(
        result.run_id, ckpt_ref, {"approved_tool_calls": {call_id_1: True}}
    )

    assert len(executed_tools) == 1
    assert executed_tools[0]["args"]["vendor"] == "Vendor A"
    # call_id_2 vẫn pending — kernel phải re-interrupt, KHÔNG âm thầm bỏ qua
    # hay tự chạy luôn.
    assert resumed.status == RunStatus.WAITING_APPROVAL
    remaining_call_ids = {w.related_ref for w in resumed.interruptions_waits}
    assert any(f"appr_{result.run_id}_{call_id_2}" in ref for ref in remaining_call_ids)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resume_blanket_approved_flag_does_not_approve_other_pending_call():
    """Bug 1.2 (kernel-level defense-in-depth): kernel.resume() không còn được
    tin field "approved": True mơ hồ như "duyệt hết mọi interruption trong
    checkpoint" — chỉ approved_tool_calls mới có hiệu lực. Gọi kernel.resume
    trực tiếp với {"approved": True} (bỏ qua handlers.py — mô phỏng 1 caller
    khác trong tương lai vô tình gửi field cũ) không được chạy tool call nào
    chưa nằm trong approved_tool_calls."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={"type": "object", "properties": {}},
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid"}

    call_id = "call_blanket_flag_1"
    model = FakeSDKModel(
        responses=[
            tool_call_response(
                call_id, "finance.payout.execute", arguments='{"amount": 500, "vendor": "Acme"}'
            ),
        ]
    )
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    result = await kernel.run(_build_request(spec=spec), spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    wait_desc = result.interruptions_waits[0]

    resumed = await kernel.resume(
        result.run_id, wait_desc.checkpoint_ref, {"approved": True}
    )

    assert len(executed_tools) == 0
    assert resumed.status == RunStatus.WAITING_APPROVAL


DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.live_provider
@pytest.mark.skipif(
    not DEEPSEEK_API_KEY,
    reason="DEEPSEEK_API_KEY not set — skipping live DeepSeek checkpoint/resume tool call test",
)
async def test_openai_agents_sdk_kernel_live_deepseek_tool_call():
    """Live provider test: DeepSeek generates real tool call and completes round-trip."""
    from agents.extensions.models.litellm_model import LitellmModel

    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="calculator_multiply",
        description="Multiply two numbers a and b",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    registry.register(cap, lambda args: {})

    captured: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        captured.append(args)
        return {"result": args.get("a", 0) * args.get("b", 0)}

    model = LitellmModel(
        model="deepseek/deepseek-chat",
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=DEEPSEEK_API_KEY,
    )
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = AgentSpec(
        id="deepseek_live_calc_agent",
        version="1.0.0",
        instructions="You are a helpful assistant. Always use calculator_multiply to multiply numbers.",
        capability_refs=["calculator_multiply"],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()

    request = RunRequest(
        input={"prompt": "Multiply 6 by 7 using calculator_multiply tool."},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_live_test",
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert len(captured) >= 1
    assert "42" in str(result.final_output)
