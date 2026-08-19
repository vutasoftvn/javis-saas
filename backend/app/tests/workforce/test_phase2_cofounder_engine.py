"""Unit Tests for Phase 2: Backend Co-Founder Engine & Intent Routing (F4 Spec).

Verifies:
1. IntentRouter with Co-Founder intent classifications (Greeting, Review, Decision, Command, Reflection).
2. CosaCofounderService message handling lifecycle.
3. Challenge Mode (Evidence vs Assumption / Problem-First F1-F3).
4. Cross-domain business synthesis (Marketing ROI + Cashflow Runway + Legal).
5. Company Pulse and Top 3 Next Best Actions aggregation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.workforce.routing.router import IntentRouter
from app.workforce.routing.deterministic import Intent
from app.workforce.orchestrator.cosa_cofounder_service import (
    CosaCofounderService,
    COSA_SYSTEM_PROMPT,
    NextBestActionItem,
    CompanyPulseResponse,
)
from app.workforce.models import FounderDecision


class TestCosaPhase2Engine:
    """Kiểm thử toàn diện cho Co-Founder Engine và Intent Router."""

    @pytest.mark.asyncio
    async def test_intent_router_classifications(self):
        """Kiểm tra IntentRouter phân loại chính xác các loại câu hỏi của Founder."""
        # 1. Greeting
        res = await IntentRouter.route_message("Chào COSA")
        assert res.intent in (Intent.GREETING, Intent.GENERAL_CHAT)
        assert res.target_agent_key == "cosa"

        res_hi = await IntentRouter.route_message("hello")
        assert res_hi.intent in (Intent.GREETING, Intent.GENERAL_CHAT)

        # 2. Founder Review / Focus
        res_review = await IntentRouter.route_message("Hôm nay tôi nên làm gì?")
        assert res_review.intent == Intent.FOUNDER_REVIEW
        assert res_review.target_agent_key == "cosa"

        res_focus = await IntentRouter.route_message("Tuần này tôi nên tập trung vào gì?")
        assert res_focus.intent == Intent.FOUNDER_REVIEW

        # 3. Founder Decision
        res_dec = await IntentRouter.route_message("Có nên tăng ngân sách marketing lên 50 triệu không?")
        assert res_dec.intent == Intent.FOUNDER_DECISION
        assert res_dec.target_agent_key == "cosa"

        # 4. Founder Command
        res_cmd = await IntentRouter.route_message("Tìm cho tôi 20 khách hàng trả tiền trong 30 ngày")
        assert res_cmd.intent == Intent.FOUNDER_COMMAND
        assert res_cmd.target_agent_key == "cosa"

        # 5. Founder Reflection
        res_ref = await IntentRouter.route_message("Tôi đang băn khoăn về định hướng thị trường ngách")
        assert res_ref.intent == Intent.FOUNDER_REFLECTION

        # 6. Specific Domains
        res_sales = await IntentRouter.route_message("Kiểm tra danh sách CRM lead mới")
        assert res_sales.intent == Intent.SALES
        assert res_sales.target_agent_key == "sales"

        res_fin = await IntentRouter.route_message("Báo cáo dòng tiền và sổ cái tháng này")
        assert res_fin.intent == Intent.FINANCE
        assert res_fin.target_agent_key == "finance"

    @pytest.mark.asyncio
    async def test_cofounder_handle_greeting_acceptance(self):
        """Acceptance Test 1 (Mục 58 F4): Câu chào phản hồi thân thiện, không load DB nặng."""
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)

        response = await service.handle_founder_message(
            message="Chào COSA",
            workspace_id=1,
        )

        assert response.intent in (Intent.GREETING.value, Intent.GENERAL_CHAT.value)
        assert "COSA Co-Founder" in response.message
        assert response.routed_domain == "COFOUNDER"
        # Đảm bảo không execute DB query phức tạp cho greeting
        assert db_mock.execute.call_count == 0


    @pytest.mark.asyncio
    async def test_cofounder_handle_founder_review_acceptance(self):
        """Acceptance Test 2 (Mục 58 F4): Hỏi ưu tiên hôm nay -> Trả về Top 3 Next Best Actions."""
        db_mock = AsyncMock()

        # Mock DB returns counts & pending decisions
        mock_res = MagicMock()
        mock_res.scalar.return_value = 2
        mock_res.scalars.return_value.first.return_value = None
        db_mock.execute.return_value = mock_res

        service = CosaCofounderService(db_mock)
        response = await service.handle_founder_message(
            message="Hôm nay tôi nên làm gì?",
            workspace_id=1,
        )

        assert response.intent == Intent.FOUNDER_REVIEW.value
        assert response.pulse is not None
        assert response.next_best_actions is not None
        assert len(response.next_best_actions) >= 2
        assert "Báo cáo trọng tâm hôm nay dành cho Founder" in response.message

    @pytest.mark.asyncio
    async def test_cofounder_challenge_mode_acceptance(self):
        """Acceptance Test 3 (Mục 60 F4 & Problem-First F2): Phản biện ý tưởng chưa có bằng chứng."""
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)

        # Founder muốn code thêm tính năng khi chưa có evidence
        challenge = await service.challenge_assumptions(
            founder_input="Tôi nghĩ nên code thêm tính năng xuất báo cáo PDF nâng cao",
        )

        assert challenge.is_challenged is True
        assert "Problem-First" in challenge.challenge_reasoning
        assert "Phỏng vấn sâu 5 khách hàng" in challenge.recommended_experiment

        # Khi gọi qua handle_founder_message
        res = await service.handle_founder_message(
            message="Tôi muốn code thêm tính năng mới",
            workspace_id=1,
        )
        assert res.challenge_analysis is not None
        assert res.challenge_analysis.is_challenged is True
        assert "Challenge Mode" in res.message

    @pytest.mark.asyncio
    async def test_cofounder_cross_domain_synthesis_acceptance(self):
        """Acceptance Test 4 (Mục 61 F4): Quyết định ngân sách -> Tổng hợp Marketing + Finance."""
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)

        synthesis = await service.synthesize_cross_domain(
            question="Có nên tăng 50 triệu chạy ads?",
            workspace_id=1,
        )

        assert "marketing_perspective" in synthesis
        assert "finance_perspective" in synthesis
        assert "legal_perspective" in synthesis
        assert "Runway" in synthesis["finance_perspective"]["cashflow_impact"]
        assert "founder_recommendation" in synthesis

        # Khi gọi qua handle_founder_message với câu hỏi quyết định
        res = await service.handle_founder_message(
            message="Có nên tăng ngân sách quảng cáo không?",
            workspace_id=1,
        )
        assert res.intent == Intent.FOUNDER_DECISION.value
        assert res.suggested_decisions is not None
        assert "Phân tích đa chiều từ Co-Founder" in res.message
