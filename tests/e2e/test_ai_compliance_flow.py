from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.compliance.data_model_gate import CosaDataModelGate
from apps.cosa.compliance.redaction import Redactor


@pytest.mark.asyncio
async def test_full_ai_compliance_lifecycle_flow() -> None:
    # 1. Approved deployment executes successfully with PII redaction
    fake_model = FakeSDKModel(responses=[text_response("Analysis complete: advisory only.")])
    gate = CosaDataModelGate(redactor=Redactor())
    kernel = RealOpenAIAgentsSDKKernel(
        model=fake_model,
        model_input_guard=gate,
    )

    spec = AgentSpec(
        id="finance_advisor",
        instructions="Advisory only",
    )

    approved_snapshot = {
        "workspace_id": "ws_1",
        "deployment_id": "dep_1",
        "mode": "ADVISORY_ONLY",
        "status": "APPROVED_FOR_USE",
        "allowed_capabilities": ["finance.read"],
    }

    request = RunRequest(
        root_executable_ref="agent:finance_advisor",
        workspace_id="ws_1",
        principal="founder_1",
        input={"prompt": "Contact CEO at ceo@example.com for review"},
        metadata={
            "compliance_snapshot": approved_snapshot,
            "compliance_snapshot_ref": "sha256:approved",
        },
    )

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED
    assert fake_model.call_count == 1

    # 2. Suspended deployment prevents any further execution
    suspended_model = FakeSDKModel(responses=[text_response("unreachable")])
    suspended_kernel = RealOpenAIAgentsSDKKernel(
        model=suspended_model,
        model_input_guard=gate,
    )

    suspended_request = RunRequest(
        root_executable_ref="agent:finance_advisor",
        workspace_id="ws_1",
        principal="founder_1",
        input={"prompt": "Another review"},
        metadata={
            "compliance_snapshot": {
                **approved_snapshot,
                "status": "SUSPENDED",
            },
            "compliance_snapshot_ref": "sha256:suspended",
        },
    )

    suspended_result = await suspended_kernel.run(suspended_request, spec)
    assert suspended_result.status == RunStatus.FAILED
    assert suspended_model.call_count == 0
