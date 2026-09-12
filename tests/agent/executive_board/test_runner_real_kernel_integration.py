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


@pytest.mark.asyncio
async def test_runner_completes_coo_analysis_through_real_kernel_with_fake_model():
    spec_registry = InMemorySpecRegistryRepository()
    await spec_registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.coo-advisor",
            version="1.0.0",
            definition_hash="hash-coo-real",
            content={
                "id": "executive.coo-advisor",
                "version": "1.0.0",
                "instructions": "Đóng vai COO advisory, tối ưu vận hành và quy trình.",
            },
            publisher="cosa_built_in",
        )
    )

    fake_output = {
        "conclusion": "Cần tối ưu nhịp sprint 2 tuần để giảm tắc nghẽn bàn giao.",
        "options": [{"title": "Tách team phụ trách release độc lập", "trade_off": "Tăng thêm chi phí quản lý"}],
        "evidence_claims": [{"claim": "Lead time hiện tại là 14 ngày", "source_ref": "object://ops/delivery-cadence-2026-09"}],
        "confidence": 0.85,
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
        role_key="coo",
        question="Làm sao giải quyết tắc nghẽn delivery hiện tại?",
        role_pin=RolePin(
            role_key="coo",
            assignment_id="assign-ops",
            spec_id="cosa.agents.operations",
            spec_version="1.3.0",
            spec_hash="ops-hash",
            skill_pins=("skillpack:executive/coo-advisor@1.0.0",),
        ),
    )

    outcome = await runner.run(request)

    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == fake_output["conclusion"]


@pytest.mark.asyncio
async def test_runner_completes_chief_of_staff_analysis_through_real_kernel_with_fake_model():
    spec_registry = InMemorySpecRegistryRepository()
    await spec_registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.board-protocol",
            version="1.0.0",
            definition_hash="hash-board-protocol-real",
            content={
                "id": "executive.board-protocol",
                "version": "1.0.0",
                "instructions": "Đóng vai board protocol, tổng hợp các góc nhìn executive.",
            },
            publisher="cosa_built_in",
        )
    )
    await spec_registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.chief-of-staff",
            version="1.0.0",
            definition_hash="hash-chief-of-staff-real",
            content={
                "id": "executive.chief-of-staff",
                "version": "1.0.0",
                "instructions": "Đóng vai Chief of Staff, điều phối liên chức năng và khung quyết định.",
            },
            publisher="cosa_built_in",
        )
    )

    fake_output = {
        "conclusion": "Đề xuất đồng bộ quyết định giữa Tài chính và Vận hành trước phiên họp Ban cố vấn.",
        "options": [{"title": "Thiết lập pre-deliberation brief", "trade_off": "Cần thêm 1 ngày chuẩn bị"}],
        "evidence_claims": [{"claim": "Chưa có văn bản thống nhất chỉ số runway", "source_ref": "object://delib/pre-brief-alignment"}],
        "confidence": 0.90,
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
        role_key="chief_of_staff",
        question="Làm sao chuẩn bị khung thảo luận cho đợt review tuần này?",
        role_pin=RolePin(
            role_key="chief_of_staff",
            assignment_id="assign-ops",
            spec_id="cosa.agents.operations",
            spec_version="1.3.0",
            spec_hash="ops-hash",
            skill_pins=(
                "skillpack:executive/board-protocol@1.0.0",
                "skillpack:executive/chief-of-staff@1.0.0",
            ),
        ),
    )

    outcome = await runner.run(request)

    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == fake_output["conclusion"]
