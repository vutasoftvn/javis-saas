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
        model_input_capability_ref="model.input.direct-user-message",
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
async def test_gate_denies_when_claim_missing_and_client_configured_zero_network_calls() -> None:
    """Task 7 audit fix (2026-08-30) — trước đây `CosaDataModelGate` với 1
    client thật (hasattr(client, "resolve_data_use") == False cho
    `CompanyServiceClient` thật) rơi thẳng về `redactor.sanitize()` không
    kiểm tra gì. Giờ: có client cấu hình (đường compliance-gated — con đường
    DUY NHẤT của runtime "openai_agents" production, xem
    `apps/cosa/composition/agent_plane.py`) nhưng KHÔNG có DataAccessClaim
    thật ⇒ phải DENY ngay, và tuyệt đối KHÔNG gọi ra network — không phải
    "vẫn gửi nhưng đã redact".
    """
    mock_client = AsyncMock()
    gate = CosaDataModelGate(client=mock_client)

    run_context = {
        "workspace_id": "ws_1",
        "compliance_snapshot": {"deployment_id": "dep_1", "status": "APPROVED_FOR_USE"},
        # Cố tình KHÔNG có "data_access_claim"/"claim" — mô phỏng đúng thực
        # trạng production hiện tại (chưa có capability/retrieval nào build
        # claim thật).
    }

    with pytest.raises(ComplianceDenied, match="DATA_ACCESS_CLAIM_MISSING"):
        await gate.prepare_initial_input(run_context, "Plan Q4 tasks")

    mock_client.resolve_data_use.assert_not_called()


@pytest.mark.asyncio
async def test_real_company_service_client_denies_via_http_resolve_data_use() -> None:
    """Xác nhận `CompanyServiceClient` (`apps/cosa/capabilities/client.py`) —
    client thật được wire vào `CosaDataModelGate` trong
    `build_cosa_agent_plane` — thật sự gửi request tới
    `POST /finance-legal/ai-compliance/resolve-data-use` với đúng field, và
    gate deny khi Company trả `allowed: false`. Dùng `httpx.MockTransport`
    thật (không phải AsyncMock tự thoả mãn hasattr) để chứng minh đường dây
    HTTP thật hoạt động, không phải chỉ interface trùng tên.
    """
    import httpx

    from apps.cosa.capabilities.client import CompanyServiceClient

    captured: dict[str, Any] = {}

    async def handle_request(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        import json as _json

        captured["body"] = _json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "allowed": False,
                "denialCode": "MODEL_NOT_APPROVED",
                "providerProfileVersion": "v3",
                "dataProfileVersion": "v1",
                "retentionPolicyId": None,
                "minimizationRequired": True,
            },
        )

    transport = httpx.MockTransport(handle_request)
    real_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    import unittest.mock as _mock

    with _mock.patch.object(httpx.AsyncClient, "__init__", patched_init):
        client = CompanyServiceClient(base_url="http://company.internal")
        gate = CosaDataModelGate(client=client)

        claim = confidential_claim("unapproved-model-v99")
        run_context = context_with(claim)
        run_context["_company_delegation_token"] = "fake-delegation-jwt"

        with pytest.raises(ComplianceDenied, match="MODEL_NOT_APPROVED"):
            await gate.prepare_initial_input(run_context, "Q3 financial summary")

    assert captured["path"] == "/finance-legal/ai-compliance/resolve-data-use"
    assert captured["headers"]["x-workspace-id"] == "ws_1"
    assert captured["headers"]["authorization"] == "Bearer fake-delegation-jwt"
    assert captured["body"]["deploymentId"] == "dep_1"
    assert captured["body"]["modelKey"] == "unapproved-model-v99"
    assert captured["body"]["dataCategories"] == ["BUSINESS_CONFIDENTIAL"]


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
