from __future__ import annotations

import json

import pytest

from agent.executive_board.models import ExecutiveAnalysisRequest, RolePin
from agent.executive_board.runner import ExecutiveBoardRunner
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response
from apps.cosa.composition.kernel_factory import build_execution_kernel


@pytest.mark.asyncio
async def test_runner_completes_analysis_through_real_kernel_with_fake_model():
    spec_registry = InMemorySpecRegistryRepository()
    await spec_registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.cfo-advisor",
            version="1.0.0",
            definition_hash="hash-cfo-real",
            content={
                "id": "executive.cfo-advisor",
                "version": "1.0.0",
                "instructions": "Đóng vai CFO advisory, chỉ đề xuất, không thực thi.",
            },
            publisher="cosa_built_in",
        )
    )

    fake_output = {
        "conclusion": "Runway 10 tháng nếu không huy động thêm vốn.",
        "options": [{"title": "Cắt giảm chi phí marketing 20%", "trade_off": "Chậm tăng trưởng ngắn hạn"}],
        "evidence_claims": [{"claim": "Cash balance hiện tại", "source_ref": "object://finance/cash-2026-09"}],
        "confidence": 0.75,
    }
    model = FakeSDKModel(responses=[text_response(json.dumps(fake_output))])

    from unittest.mock import MagicMock
    from agent.runs.repository import InMemoryRunRepository

    kernel, _ = build_execution_kernel(
        runtime="openai_agents",
        repository=InMemoryRunRepository(),
        spec_registry=spec_registry,
        capability_registry=MagicMock(),
        gateway=MagicMock(),
        policy_engine=MagicMock(),
        company_client=None,
        model=model,
    )

    runner = ExecutiveBoardRunner(kernel=kernel, spec_registry=spec_registry)
    request = ExecutiveAnalysisRequest(
        workspace_id="ws-1",
        project_id="proj-1",
        deliberation_id="delib-1",
        frame_version=1,
        role_key="cfo",
        question="Runway hiện tại còn bao lâu?",
        role_pin=RolePin(
            role_key="cfo",
            assignment_id="assign-cfo",
            spec_id="cosa.agents.finance",
            spec_version="1.1.0",
            spec_hash="fin-hash",
            skill_pins=("skillpack:executive/cfo-advisor@1.0.0",),
        ),
    )

    outcome = await runner.run(request)

    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == fake_output["conclusion"]
