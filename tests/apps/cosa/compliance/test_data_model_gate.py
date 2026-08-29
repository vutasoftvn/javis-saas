from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.compliance.data_model_gate import CosaDataModelGate
from apps.cosa.compliance.redaction import Redactor


class DenyingGuard:
    def __init__(self, code: str) -> None:
        self.code = code

    async def prepare_initial_input(self, run_context, raw_input: str) -> str:
        raise ComplianceDenied(self.code)

    async def prepare_tool_output(self, run_context, capability_id: str, output):
        return output

    async def assert_before_model_call(self, run_context) -> None:
        raise ComplianceDenied(self.code)


def denying_guard(code: str) -> DenyingGuard:
    return DenyingGuard(code)


@pytest.mark.asyncio
async def test_withdrawn_authorization_prevents_model_call() -> None:
    model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel = RealOpenAIAgentsSDKKernel(
        model=model,
        model_input_guard=denying_guard("PROCESSING_AUTHORIZATION_WITHDRAWN"),
    )
    advisory_spec = AgentSpec(
        id="advisory_agent",
        instructions="Advisory only",
    )
    request_with_personal_prompt = RunRequest(
        root_executable_ref="agent:advisory_agent",
        workspace_id="ws_1",
        principal="founder_1",
        input={"prompt": "Personal data with withdrawn consent"},
    )
    result = await kernel.run(request_with_personal_prompt, advisory_spec)
    assert result.status == RunStatus.FAILED
    assert model.call_count == 0


@pytest.mark.asyncio
async def test_email_is_redacted_before_provider_input() -> None:
    gate = CosaDataModelGate(redactor=Redactor())
    run_context = {
        "workspace_id": "ws_1",
        "compliance_snapshot": {"deployment_id": "dep_1"},
        "purpose_id": "advisory",
        "provider_key": "deepseek",
    }
    sanitized = await gate.prepare_initial_input(run_context, "Email: a@example.com")
    assert "a@example.com" not in sanitized
    assert "[EMAIL_REDACTED]" in sanitized
