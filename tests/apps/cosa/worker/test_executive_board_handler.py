"""Advisor overlay chạy qua đường run chung của COSA: compliance gate + model routing."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent.contracts.run import RunRequest
from agent.executive_board.models import ExecutiveAnalysisRequest
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.composition.kernel_factory import build_execution_kernel
from apps.cosa.worker.executive_board_runtime import (
    PlaneRoutedAdvisorKernel,
    build_executive_board_runner,
)
from apps.cosa.worker.run_core import RunCoreError
from tests.agent.executive_board.advisor_support import build_pin, seed_advisor_registry

OUTPUT = {
    "conclusion": "Runway 10 tháng.",
    "options": [{"title": "Giữ nguyên", "trade_off": "An toàn"}],
    "evidence_claims": [{"claim": "Cash", "source_ref": "object://finance/cash"}],
    "confidence": 0.8,
}


class _Compliance:
    def __init__(self) -> None:
        self.calls: list[tuple[RunRequest, object]] = []

    async def resolve_for_run(self, request, spec):
        self.calls.append((request, spec))
        # Giống ComplianceResolver thật: có snapshot nên kernel không resolve lại theo spec overlay.
        return {
            "_company_delegation_token": "tok",
            "compliance_snapshot": {"workspace_id": request.workspace_id, "allowed_capabilities": []},
        }


async def _plane(role_key: str = "cfo"):
    registry = InMemorySpecRegistryRepository()
    await seed_advisor_registry(registry, role_key)
    kernel, _ = build_execution_kernel(
        runtime="openai_agents",
        repository=InMemoryRunRepository(),
        spec_registry=registry,
        capability_registry=MagicMock(),
        gateway=MagicMock(),
        policy_engine=MagicMock(),
        company_client=None,
        model=FakeSDKModel(responses=[text_response(json.dumps(OUTPUT))]),
    )
    compliance = _Compliance()
    plane = SimpleNamespace(
        spec_registry=registry,
        kernel=kernel,
        compliance_resolver=compliance,
    )
    return plane, compliance


def _request(role_key: str = "cfo", **kw) -> ExecutiveAnalysisRequest:
    return ExecutiveAnalysisRequest(
        workspace_id="ws-1",
        project_id="proj-1",
        deliberation_id="delib-1",
        frame_version=1,
        role_key=role_key,
        question="Runway?",
        execution_pin=kw.get("execution_pin") or build_pin(role_key),
    )


@pytest.mark.asyncio
async def test_advisor_run_passes_compliance_for_deployment_spec_with_overlay_capabilities():
    plane, compliance = await _plane()
    runner = build_executive_board_runner(plane)
    pin = build_pin("cfo")

    outcome = await runner.run(_request())

    assert outcome.kind == "executive.analysis.completed.v1"
    (request, compliance_spec), = compliance.calls
    # Compliance gate đánh giá theo spec Project deployment (không có approval riêng cho overlay)...
    assert compliance_spec.id == pin.deployment.spec_id
    # ...nhưng chỉ với capability của overlay (advisory, không tool).
    assert compliance_spec.capability_refs == []
    assert request.workspace_id == "ws-1"
    assert request.run_id.startswith("run_exec_")
    assert request.metadata["_company_delegation_token"] == "tok"
    assert request.metadata["project_id"] == "proj-1"
    assert outcome.deployment_pin_hash == pin.deployment.identity_hash()


@pytest.mark.asyncio
async def test_compliance_denial_blocks_before_any_model_call():
    plane, compliance = await _plane()

    async def deny(request, spec):
        from apps.cosa.compliance.contracts import ComplianceDenied

        raise ComplianceDenied("NO_APPROVED_DEPLOYMENT", "not approved")

    compliance.resolve_for_run = deny
    plane.kernel = MagicMock()
    plane.kernel.run = AsyncMock()
    runner = build_executive_board_runner(plane)

    with pytest.raises(RunCoreError) as exc:
        await runner.run(_request())
    assert exc.value.reason_code == "compliance_denied"
    plane.kernel.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_deployment_drift_in_registry_is_rejected():
    plane, _ = await _plane()
    kernel = PlaneRoutedAdvisorKernel(plane)
    request = RunRequest(
        principal="p",
        workspace_id="ws-1",
        run_id="r1",
        root_executable_ref="x",
        metadata={
            "deployment_spec_id": "cosa.agents.finance",
            "deployment_spec_version": "1.1.0",
            "deployment_spec_hash": "0" * 64,
        },
    )
    with pytest.raises(RunCoreError, match="deployment_pin_drift"):
        await kernel.run(request, MagicMock())
