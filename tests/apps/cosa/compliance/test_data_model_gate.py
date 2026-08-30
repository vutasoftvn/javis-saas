from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.data_model_gate import CosaDataModelGate
from apps.cosa.compliance.redaction import Redactor


class DenyingGuard:
    def __init__(self, code: str) -> None:
        self.code = code

    async def prepare_initial_input(self, run_context: Any, raw_input: str) -> str:
        raise ComplianceDenied(self.code)

    async def prepare_tool_output(self, run_context: Any, capability_id: str, output: Any) -> Any:
        return output

    async def assert_before_model_call(self, run_context: Any) -> None:
        raise ComplianceDenied(self.code)


def denying_guard(code: str) -> DenyingGuard:
    return DenyingGuard(code)


def personal_claim(subject_reference: str | None) -> DataAccessClaim:
    return DataAccessClaim(
        workspace_id="ws_1",
        deployment_id="dep_1",
        capability_id="model.input",
        source_ref="doc://contact/1",
        source_hash="sha256:abc",
        categories=frozenset(["PERSONAL"]),
        purpose_id="advisory",
        subject_reference=subject_reference,
        provider_key="deepseek",
        model_key="deepseek-chat",
    )


def confidential_claim(model_key: str) -> DataAccessClaim:
    return DataAccessClaim(
        workspace_id="ws_1",
        deployment_id="dep_1",
        capability_id="model.input",
        source_ref="doc://fin/1",
        source_hash="sha256:def",
        categories=frozenset(["BUSINESS_CONFIDENTIAL"]),
        purpose_id="advisory",
        subject_reference=None,
        provider_key="deepseek",
        model_key=model_key,
    )


def context_with(claim: DataAccessClaim) -> dict[str, Any]:
    return {
        "workspace_id": claim.workspace_id,
        "compliance_snapshot": {"deployment_id": claim.deployment_id, "status": "APPROVED_FOR_USE"},
        "data_access_claim": claim,
    }


@pytest.mark.asyncio
async def test_gate_denies_personal_data_without_subject_reference() -> None:
    gate = CosaDataModelGate()
    with pytest.raises(ComplianceDenied, match="PROCESSING_AUTHORIZATION_MISSING"):
        await gate.prepare_initial_input(context_with(personal_claim(None)), "input")


@pytest.mark.asyncio
async def test_gate_denies_provider_profile_that_excludes_requested_model() -> None:
    mock_client = AsyncMock()
    mock_client.resolve_data_use.return_value = SimpleNamespace(
        allowed=False,
        denial_code="MODEL_NOT_APPROVED",
        provider_profile_version="v1",
        data_profile_version=None,
        retention_policy_id=None,
        minimization_required=True,
    )
    gate = CosaDataModelGate(client=mock_client)
    with pytest.raises(ComplianceDenied, match="MODEL_NOT_APPROVED"):
        await gate.prepare_initial_input(context_with(confidential_claim("other-model")), "input")


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
