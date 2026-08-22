"""End-to-End (E2E) Integration Tests for Phase 5: COSA Co-Founder System (F4 Spec).

Verifies the complete unified lifecycle:
1. Morning Founder Routine: Query pulse & Top 3 Focus.
2. Cross-domain strategic decision proposal & resolution into Decision Memory.
3. Mission shaping and multi-agent domain dispatch (Sales + Marketing + Tech).
4. Work product quality gate evaluation via Cross-cutting QualityGatePolicy.
5. Shared Capability 'investigate' supplying evidence.
6. Optional Packs Store toggle and runtime registry reflection.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from workforce.orchestrator.cosa_cofounder_service import CosaCofounderService
from workforce.agents.orchestration.result import ChiefOfStaffResult

from workforce.routing.router import IntentRouter
from workforce.routing.deterministic import Intent
from workforce.governance.founder_decision_service import FounderDecisionService
from workforce.governance.quality_gate_policy import QualityGatePolicy
from workforce.work_product.work_product_service import WorkProductService
from workforce.capabilities.investigate_service import InvestigateService
from workforce.schemas.decision_schemas import (
    FounderDecisionCreate,
    FounderDecisionResolveRequest,
    DecisionStatusEnum,
    DecisionDomainEnum,
    DecisionOption,
)
from founder_os.tasks.models import Task


class TestCosaE2EWorkflow:
    """Kiểm thử luồng E2E tích hợp toàn diện theo F4 Spec."""

    @pytest.mark.asyncio
    async def test_full_cofounder_lifecycle_e2e(self):
        """
        Kịch bản E2E hoàn chỉnh:
        Founder hỏi ưu tiên -> COSA phân tích nhịp tim & Top 3 ->
        Founder tham vấn quyết định ngân sách -> COSA tổng hợp Marketing + Finance ->
        Founder chốt quyết định -> Ghi nhận Evidence & điều phối Domain Workforce ->
        Domain Agent hoàn thành Work Product qua Quality Gate.
        """
        db_mock = AsyncMock()

        # Mock DB queries. G3 Phase 1D adds a real Workspace.company_stage lookup
        # inside get_company_pulse() - must stay a string, not the blanket scalar=1
        # every other count query in this scenario returns.
        def execute_side_effect(stmt):
            result = MagicMock()
            if "workspaces.company_stage" in str(stmt).lower():
                result.scalar.return_value = "S1_PROBLEM_VALIDATION"
            else:
                result.scalar.return_value = 1
            result.scalars.return_value.first.return_value = None
            return result

        db_mock.execute.side_effect = execute_side_effect

        # -------------------------------------------------------------
        # BƯỚC 1: Founder hỏi ưu tiên buổi sáng ("Hôm nay tôi nên làm gì?")
        # -------------------------------------------------------------
        # G2 P0.9 / G3 §10.5: không còn 2 item tĩnh không backing bởi query
        # nào — với mock này (không có pending decision), danh sách trung
        # thực là rỗng thay vì luôn >= 2 như trước.
        sync_db_mock = MagicMock()
        cofounder = CosaCofounderService(db_mock, sync_db=sync_db_mock)
        morning_res = await cofounder.handle_founder_message(
            message="Hôm nay tôi nên làm gì?",
            workspace_id=1,
        )

        assert morning_res.intent == Intent.FOUNDER_REVIEW.value
        assert morning_res.pulse is not None
        assert morning_res.next_best_actions == []
        assert "Báo cáo trọng tâm hôm nay dành cho Founder" in morning_res.message

        # -------------------------------------------------------------
        # BƯỚC 2: Founder tham vấn quyết định chiến lược ("Có nên tăng 50 triệu chạy ads?")
        # -------------------------------------------------------------
        # G2 P0.9 / G3 §10.5: FOUNDER_DECISION giờ đi qua
        # ChiefOfStaffOrchestrator.orchestrate() thật (mocked ở đây) thay vì
        # synthesize_cross_domain() bịa số liệu — mission_id/mission_status
        # phản ánh kết quả orchestrator thật.
        fake_orchestrator_result = ChiefOfStaffResult(
            mission_id="777",
            workspace_id="1",
            goal="Có nên tăng ngân sách quảng cáo lên 50 triệu không?",
            diagnosis="Dựa trên runway thật hiện tại, khuyến nghị thử nghiệm ngân sách nhỏ trước khi scale.",
            specialist_reports={"sales": {}, "finance": {}},
            priorities=[],
            action_plan=[],
            required_approvals=[],
            proposals=[],
            status="completed",
        )
        with patch(
            "workforce.orchestrator.cosa_cofounder_service.orchestration_service.orchestrate_mission",
            new_callable=AsyncMock,
            return_value=fake_orchestrator_result,
        ):

            decision_consult = await cofounder.handle_founder_message(
                message="Có nên tăng ngân sách quảng cáo lên 50 triệu không?",
                workspace_id=1,
                user_id=1,
            )

        assert decision_consult.intent == Intent.FOUNDER_DECISION.value
        assert decision_consult.mission_id == "777"
        assert decision_consult.mission_status == "completed"
        assert decision_consult.suggested_decisions == [fake_orchestrator_result.model_dump()]

        # -------------------------------------------------------------
        # BƯỚC 3: Tạo và Chốt Quyết định chiến lược (Founder Decision Service)
        # -------------------------------------------------------------
        decision_service = FounderDecisionService(db_mock)
        created_decision = await decision_service.create_decision(
            FounderDecisionCreate(
                workspace_id=1,
                domain=DecisionDomainEnum.MARKETING,
                question="Có nên tăng ngân sách Marketing lên 50 triệu/tháng?",
                context_summary="CMO đề xuất mở rộng acquisition.",
                options_jsonb=[
                    DecisionOption(id="OPTION_A", title="Tăng toàn bộ 50tr", description="Scale nhanh nhưng giảm Runway"),
                    DecisionOption(id="OPTION_B", title="Thử nghiệm 15tr trong 2 tuần", description="Kiểm chứng CAC trước khi scale"),
                ],
                evidence_ids=["evi_market_01", "evi_tt58_cashflow"],
            )
        )

        assert created_decision.status == DecisionStatusEnum.PENDING.value
        assert len(created_decision.evidence_ids) == 2

        # Founder chọn Option B (Thử nghiệm 15tr)
        mock_get_dec = MagicMock()
        mock_get_dec.scalars.return_value.first.return_value = created_decision
        db_mock.execute.side_effect = [mock_get_dec]

        resolved_decision = await decision_service.resolve_decision(
            decision_id=created_decision.id,
            resolve_data=FounderDecisionResolveRequest(
                decision_made="OPTION_B",
                founder_notes="Đồng ý thử nghiệm 15 triệu trong 2 tuần để kiểm chứng CAC.",
                status=DecisionStatusEnum.DECIDED,
            ),
            user_id=1,
            workspace_id=1,
        )

        assert resolved_decision is not None
        assert resolved_decision.status == DecisionStatusEnum.DECIDED.value
        assert resolved_decision.decision_made == "OPTION_B"

        # -------------------------------------------------------------
        # BƯỚC 4: Shared Capability 'investigate' tra cứu số liệu bổ trợ
        # -------------------------------------------------------------
        investigate_service = InvestigateService(db_mock)
        inv_res = await investigate_service.investigate(
            query="Báo cáo dòng tiền kế toán TT58 và CAC khảo sát khách hàng",
            sources=["web", "memory"],
            workspace_id=1,
            caller_agent_key="cmo_agent",
        )

        assert len(inv_res.evidence_items) > 0
        assert len(inv_res.facts) > 0

        # -------------------------------------------------------------
        # BƯỚC 5: Domain Agent sinh Work Product & Thẩm định Quality Gate
        # -------------------------------------------------------------
        wp_service = WorkProductService(db_mock)
        task = Task(id=501, title="Triển khai chiến dịch thử nghiệm 15 triệu", workspace_id=1)

        raw_output = (
            "Báo cáo phân bổ ngân sách 15 triệu cho chiến dịch thử nghiệm 2 tuần: "
            "Dự kiến tiếp cận 5,000 khách hàng tiềm năng, thu về 40 qualified leads. "
            "Chi phí CAC mục tiêu: 375,000 VNĐ / lead. "
            "Các bước hành động tiếp theo: "
            "1. Thiết lập quảng cáo Facebook & Google Search. "
            "2. Gắn tracking chuyển đổi về CRM."
        )

        wp = await wp_service.create_from_execution(
            task=task,
            agent_key="marketing",
            raw_content=raw_output,
            workspace_id=1,
        )

        assert wp.status == "DRAFT"
        assert wp.metadata_jsonb is not None
        assert "quality_gate" in wp.metadata_jsonb
        qg = wp.metadata_jsonb["quality_gate"]
        assert qg["passed"] is True
        assert qg["quality_score"] >= 70.0
        assert qg["is_evidence_backed"] is True
        assert qg["is_actionable"] is True
