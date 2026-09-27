"""Run đầy đủ qua Runner của SDK (model giả): một tool lỗi backend không làm run thất bại;
lỗi liên tiếp quá giới hạn thì run FAILED với lỗi phân loại được là tool_backend_error."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("agents")

from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import CapabilityRisk, ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_integrations.openai_agents_sdk.tool_args import MAX_CONSECUTIVE_TOOL_ERRORS
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response

CAP = CapabilitySpec(
    id="business.probe",
    description="probe",
    risk=CapabilityRisk.LOW,
    input_schema={"type": "object", "properties": {}},
)


class _CompanyError(Exception):
    def __init__(self) -> None:
        super().__init__("Company Service Error (401): invalid token")
        self.status_code = 401


def _spec() -> AgentSpec:
    return AgentSpec(
        id="probe_agent",
        version="1.0.0",
        instructions="probe",
        capability_refs=[CAP.id],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()


async def _run(failing_calls: int, final_text: str = "Đã trả lời bằng dữ liệu còn lại.") -> Any:
    calls = {"n": 0}

    def handler(payload: dict[str, Any], ctx: Any) -> Any:
        calls["n"] += 1
        raise _CompanyError()

    registry = CapabilityRegistry()
    registry.register(CAP, handler)
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repo)
    responses = [tool_call_response(f"call_{i}", CAP.id) for i in range(failing_calls)]
    responses.append(text_response(final_text))
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        model=FakeSDKModel(responses=responses),
        capability_executor=gateway.execute,
    )
    spec = _spec()
    result = await kernel.run(
        RunRequest(
            input={"prompt": "tình hình thế nào?"},
            principal="u1",
            root_executable_ref=spec.to_pinned_identity(),
            execution_mode=ExecutionMode.AGENT,
            workspace_id="ws_probe",
            metadata={"policy_snapshot": {"company_status": "active"}},
        ),
        spec,
    )
    return result, calls["n"]


@pytest.mark.asyncio
async def test_single_backend_error_does_not_fail_run() -> None:
    result, calls = await _run(failing_calls=1)
    assert calls == 1
    assert result.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_repeated_backend_errors_stop_the_run() -> None:
    from apps.cosa.worker.provider_errors import classify_run_error

    result, calls = await _run(failing_calls=MAX_CONSECUTIVE_TOOL_ERRORS + 1)
    assert calls == MAX_CONSECUTIVE_TOOL_ERRORS + 1
    assert result.status == RunStatus.FAILED
    assert classify_run_error(" ".join(result.errors)).code == "tool_backend_error"
