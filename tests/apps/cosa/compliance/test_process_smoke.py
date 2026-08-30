from __future__ import annotations

import pytest
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.compliance.data_model_gate import CosaDataModelGate
from apps.cosa.compliance.redaction import Redactor


@pytest.mark.asyncio
async def test_suspended_deployment_never_reaches_fake_provider() -> None:
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    gate = CosaDataModelGate(redactor=Redactor())

    kernel = RealOpenAIAgentsSDKKernel(
        model=fake_model,
        model_input_guard=gate,
    )

    spec = AgentSpec(
        id="advisory_agent",
        instructions="Advisory only",
        model_input_capability_ref="model.input.direct-user-message",
    )

    suspended_snapshot = {
        "workspace_id": "ws_1",
        "deployment_id": "dep_1",
        "mode": "ADVISORY_ONLY",
        "status": "SUSPENDED",
        "allowed_capabilities": ["finance.read"],
    }

    request = RunRequest(
        root_executable_ref="agent:advisory_agent",
        workspace_id="ws_1",
        principal="founder_1",
        input={"prompt": "private input"},
        metadata={
            "compliance_snapshot": suspended_snapshot,
            "compliance_snapshot_ref": "sha256:suspended",
        },
    )

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0
    assert any("DEPLOYMENT_NOT_APPROVED" in err for err in result.errors)
