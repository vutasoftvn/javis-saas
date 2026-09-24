from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from agent.executive_board.models import ExecutiveAnalysisRequest
from agent.executive_board.runner import ExecutiveBoardRunner
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.agents.advisor_overlay_validation import validate_advisor_overlay
from apps.cosa.composition.kernel_factory import build_execution_kernel
from tests.agent.executive_board.advisor_support import build_pin, seed_advisor_registry

CASES = [
    (
        "cfo",
        "Runway hiện tại còn bao lâu?",
        {
            "conclusion": "Runway 10 tháng nếu không huy động thêm vốn.",
            "options": [
                {"title": "Cắt giảm chi phí marketing 20%", "trade_off": "Chậm tăng trưởng ngắn hạn"}
            ],
            "evidence_claims": [
                {"claim": "Cash balance hiện tại", "source_ref": "object://finance/cash-2026-09"}
            ],
            "confidence": 0.75,
        },
    ),
    (
        "coo",
        "Làm sao giải quyết tắc nghẽn delivery hiện tại?",
        {
            "conclusion": "Cần tối ưu nhịp sprint 2 tuần để giảm tắc nghẽn bàn giao.",
            "options": [
                {"title": "Tách team phụ trách release độc lập", "trade_off": "Tăng chi phí quản lý"}
            ],
            "evidence_claims": [
                {"claim": "Lead time hiện tại là 14 ngày", "source_ref": "object://ops/cadence"}
            ],
            "confidence": 0.85,
        },
    ),
    (
        "chief_of_staff",
        "Khung quyết định cho deliberation tuần này là gì?",
        {
            "conclusion": "Đóng khung theo 2 phương án và 1 tiêu chí kill.",
            "options": [{"title": "Phương án A", "trade_off": "Nhanh nhưng rủi ro"}],
            "evidence_claims": [{"claim": "Ưu tiên tuần", "source_ref": "object://ops/priorities"}],
            "confidence": 0.8,
        },
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("role_key", "question", "fake_output"), CASES)
async def test_runner_completes_analysis_through_real_kernel_with_pinned_overlay(
    role_key, question, fake_output
):
    registry = InMemorySpecRegistryRepository()
    await seed_advisor_registry(registry, role_key)
    model = FakeSDKModel(responses=[text_response(json.dumps(fake_output))])
    run_repo = InMemoryRunRepository()
    kernel, _ = build_execution_kernel(
        runtime="openai_agents",
        repository=run_repo,
        spec_registry=registry,
        capability_registry=MagicMock(),
        gateway=MagicMock(),
        policy_engine=MagicMock(),
        company_client=None,
        model=model,
    )
    runner = ExecutiveBoardRunner(
        kernel=kernel, spec_registry=registry, overlay_validator=validate_advisor_overlay
    )
    pin = build_pin(role_key)

    outcome = await runner.run(
        ExecutiveAnalysisRequest(
            workspace_id="ws-1",
            project_id="proj-1",
            deliberation_id="delib-1",
            frame_version=1,
            role_key=role_key,
            question=question,
            execution_pin=pin,
        )
    )

    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == fake_output["conclusion"]
    # Run durable ghi đúng overlay (id/version/hash) và cả 2 pin trong input_payload.
    run = await run_repo.get_run(outcome.descriptor["run_id"])
    assert run.root_executable_id == pin.overlay.overlay_spec_id
    assert run.root_definition_hash == pin.overlay.overlay_spec_hash
    recorded = run.input_payload["advisor_execution"]
    assert recorded["project_id"] == "proj-1"
    assert recorded["deployment"]["spec_hash"] == pin.deployment.spec_hash
    assert recorded["overlay"]["overlay_spec_hash"] == pin.overlay.overlay_spec_hash
