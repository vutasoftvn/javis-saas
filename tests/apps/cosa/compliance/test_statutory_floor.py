from __future__ import annotations

import pytest
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import PolicyOutcome
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, tool_call_response

from apps.cosa.policies.evaluator import CosaPolicyEngine
from tests.apps.cosa.policy_test_helpers import (
    allow_all_policy_snapshot,
    compliance_snapshot,
)


def test_tenant_allow_cannot_bypass_forbidden_hr_decision() -> None:
    decision = CosaPolicyEngine().evaluate(
        "hr.candidate.rank",
        {},
        context={
            "policy_snapshot": allow_all_policy_snapshot(),
            "compliance_snapshot": compliance_snapshot(
                allowed_capabilities={"hr.candidate.rank"},
                prohibited_purpose=True,
            ),
        },
    )
    assert decision.outcome == PolicyOutcome.DENY
    assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)


@pytest.mark.asyncio
async def test_unbound_capability_is_not_offered_to_sdk_model() -> None:
    model = FakeSDKModel(responses=[tool_call_response("call_1", "finance.transaction.record")])
    kernel = RealOpenAIAgentsSDKKernel(model=model)

    spec_with_unbound = AgentSpec(
        id="finance_agent",
        instructions="Finance only",
        capability_refs=["finance.transaction.record"],
    )

    request = RunRequest(
        root_executable_ref="agent:finance_agent",
        workspace_id="ws_1",
        principal="founder_1",
        input={"prompt": "Record payout"},
        metadata={
            "compliance_snapshot": compliance_snapshot(
                allowed_capabilities={"finance.read"},  # finance.transaction.record is UNBOUND
            )
        },
    )

    result = await kernel.run(request, spec_with_unbound)
    assert result.status == RunStatus.FAILED
    assert model.call_count == 0
