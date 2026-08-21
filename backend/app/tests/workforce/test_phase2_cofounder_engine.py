"""Unit Tests for Phase 2: Backend Co-Founder Engine & Intent Routing (F4 Spec).

Verifies:
1. IntentRouter with Co-Founder intent classifications (Greeting, Review, Decision, Command, Reflection).
2. CosaCofounderService message handling lifecycle.
3. Challenge Mode (Evidence vs Assumption / Problem-First F1-F3).
4. FOUNDER_DECISION/FOUNDER_COMMAND hand-off into the real ChiefOfStaffOrchestrator (G3 §10.5).
5. Company Pulse and Top 3 Next Best Actions aggregation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.workforce.routing.router import IntentRouter
from app.workforce.routing.deterministic import Intent
from app.workforce.orchestrator.cosa_cofounder_service import (
    CosaCofounderService,
    COSA_SYSTEM_PROMPT,
    NextBestActionItem,
    CompanyPulseResponse,
)
from app.workforce.agents.orchestration.result import ChiefOfStaffResult

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
        """Acceptance Test 2 (Mục 58 F4): Hỏi ưu tiên hôm nay -> Trả về Top 3 Next Best Actions.

        G2 P0.9 / G3 §10.5: get_next_best_action() no longer appends 2 static,
        query-less filler items — the only real signal available in this mock
        is a pending FounderDecision, so exactly 1 honest item is expected
        instead of the old ">= 2" (which used to pass only because of the
        now-removed fabricated items).
        """
        db_mock = AsyncMock()

        pending_decision = MagicMock()
        pending_decision.id = 42
        pending_decision.question = "Có nên tăng ngân sách marketing?"
        pending_decision.domain = "MARKETING"

        # Mock DB returns counts & 1 pending decision for every query except the
        # G3 Phase 1D company_stage lookup, which must stay a real string.
        def execute_side_effect(stmt):
            result = MagicMock()
            if "workspaces.company_stage" in str(stmt).lower():
                result.scalar.return_value = "S1_PROBLEM_VALIDATION"
            else:
                result.scalar.return_value = 2
            result.scalars.return_value.first.return_value = pending_decision
            return result

        db_mock.execute.side_effect = execute_side_effect

        service = CosaCofounderService(db_mock)
        response = await service.handle_founder_message(
            message="Hôm nay tôi nên làm gì?",
            workspace_id=1,
        )

        assert response.intent == Intent.FOUNDER_REVIEW.value
        assert response.pulse is not None
        assert response.next_best_actions is not None
        assert len(response.next_best_actions) == 1
        assert response.next_best_actions[0].category == "DECISION"
        assert "Báo cáo trọng tâm hôm nay dành cho Founder" in response.message

    @pytest.mark.asyncio
    async def test_company_pulse_surfaces_the_real_company_stage(self):
        """G3 Phase 1D / G2 §8.2 'stage-aware Hologram': Company Pulse must expose the
        real, now-transitionable Workspace.company_stage, not omit it."""
        db_mock = AsyncMock()

        def execute_side_effect(stmt):
            result = MagicMock()
            compiled = str(stmt).lower()
            if "workspaces.company_stage" in compiled:
                result.scalar.return_value = "S3_BUSINESS_VALIDATION"
            else:
                result.scalar.return_value = 5
            result.scalars.return_value.first.return_value = None
            return result

        db_mock.execute.side_effect = execute_side_effect
        service = CosaCofounderService(db_mock)

        pulse = await service.get_company_pulse(workspace_id=1)

        assert pulse.company_stage == "S3_BUSINESS_VALIDATION"

    @pytest.mark.asyncio
    async def test_company_pulse_genesis_branch_still_surfaces_company_stage(self):
        db_mock = AsyncMock()

        def execute_side_effect(stmt):
            result = MagicMock()
            compiled = str(stmt).lower()
            if "workspaces.company_stage" in compiled:
                result.scalar.return_value = "S0_GENESIS"
            else:
                result.scalar.return_value = 0  # total_projects == 0 -> Genesis branch
            return result

        db_mock.execute.side_effect = execute_side_effect
        service = CosaCofounderService(db_mock)

        pulse = await service.get_company_pulse(workspace_id=1)

        assert pulse.company_stage == "S0_GENESIS"
        assert pulse.total_active_goals == 0

    @pytest.mark.asyncio
    async def test_build_stage_goal_action_reads_the_real_project_stage(self):
        """G3 Phase 1D (Stage Operating Engine): Top3 must reflect the flagship
        project's REAL project_stage/primary_goal, not a fabricated placeholder."""
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)

        project = MagicMock()
        project.id = 555
        project.title = "Flagship MVP"
        project.project_stage = "S4_GO_TO_MARKET"

        query_result = MagicMock()
        query_result.scalars.return_value.first.return_value = project
        db_mock.execute.return_value = query_result

        item = await service._build_stage_goal_action(workspace_id=1)

        assert item is not None
        assert item.category == "FOUNDER_ACTION"
        assert "S4_GO_TO_MARKET" in item.title
        assert "Flagship MVP" in item.rationale
        assert item.action_payload == {"project_id": 555, "project_stage": "S4_GO_TO_MARKET"}

    @pytest.mark.asyncio
    async def test_build_stage_goal_action_returns_none_without_a_project(self):
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)

        query_result = MagicMock()
        query_result.scalars.return_value.first.return_value = None
        db_mock.execute.return_value = query_result

        assert await service._build_stage_goal_action(workspace_id=1) is None

    @pytest.mark.asyncio
    async def test_next_best_action_fills_remaining_slots_with_the_stage_goal(self):
        """When there's no pending decision at all, Top3 should still surface the
        real stage goal instead of returning an empty list."""
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)

        project = MagicMock()
        project.id = 777
        project.title = "Flagship MVP"
        project.project_stage = "S2_SOLUTION_VALIDATION"

        def execute_side_effect(stmt):
            result = MagicMock()
            compiled = str(stmt)
            if "founder_decisions" in compiled:
                result.scalars.return_value.first.return_value = None
            elif "projects" in compiled and "count" not in compiled.lower():
                result.scalars.return_value.first.return_value = project
            else:
                result.scalar.return_value = 3  # total_projects > 0, skip the Genesis branch
            return result

        db_mock.execute.side_effect = execute_side_effect

        actions = await service.get_next_best_action(workspace_id=1)

        assert len(actions) == 1
        assert actions[0].category == "FOUNDER_ACTION"
        assert "S2_SOLUTION_VALIDATION" in actions[0].title

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
    async def test_cofounder_decision_routes_through_real_orchestrator(self):
        """G2 P0.9 / G3 §10.5: FOUNDER_DECISION used to return
        synthesize_cross_domain() — entirely fabricated numbers with zero DB
        access ("50 triệu/tháng", "7.5→6.2 tháng runway" regardless of
        question/workspace). That method is deleted; FOUNDER_DECISION now
        routes through ChiefOfStaffOrchestrator.orchestrate(), the one engine
        with real Outcome/AgentRun side effects and a real Sales/Finance
        snapshot behind its diagnosis."""
        db_mock = AsyncMock()
        sync_db_mock = MagicMock()
        service = CosaCofounderService(db_mock, sync_db=sync_db_mock)

        fake_result = ChiefOfStaffResult(
            mission_id="999",
            workspace_id="1",
            goal="Có nên tăng ngân sách quảng cáo không?",
            diagnosis="Dựa trên runway thật 7.2 tháng, khuyến nghị thử nghiệm ngân sách nhỏ trước khi scale.",
            specialist_reports={"sales": {}, "finance": {}},
            priorities=["Runway review"],
            action_plan=[],
            required_approvals=[],
            proposals=[],
            status="completed",
        )

        with patch(
            "app.workforce.orchestrator.cosa_cofounder_service.orchestration_service.orchestrate_mission",
            new_callable=AsyncMock,
            return_value=fake_result,
        ) as mock_orchestrate:

            res = await service.handle_founder_message(
                message="Có nên tăng ngân sách quảng cáo không?",
                workspace_id=1,
                user_id=7,
            )

        mock_orchestrate.assert_awaited_once()
        call_kwargs = mock_orchestrate.call_args.kwargs
        assert call_kwargs["db"] is sync_db_mock
        assert call_kwargs["workspace_id"] == 1
        assert call_kwargs["user_id"] == 7
        assert call_kwargs["goal"] == "Có nên tăng ngân sách quảng cáo không?"

        assert res.intent == Intent.FOUNDER_DECISION.value
        assert res.mission_id == "999"
        assert res.mission_status == "completed"
        assert res.message == fake_result.diagnosis
        assert res.suggested_decisions == [fake_result.model_dump()]

    @pytest.mark.asyncio
    async def test_cofounder_command_without_sync_db_reports_honest_failure(self):
        """No orchestrator hand-off possible without a sync Session — must
        say the request failed, never claim a Mission was created."""
        db_mock = AsyncMock()
        service = CosaCofounderService(db_mock)  # sync_db intentionally omitted

        res = await service.handle_founder_message(
            message="Tìm cho tôi 20 khách hàng trong 30 ngày",
            workspace_id=1,
            user_id=7,
        )

        assert res.intent == Intent.FOUNDER_COMMAND.value
        assert res.mission_id is None
        assert "chưa được tạo thành Mission" in res.message

    @pytest.mark.asyncio
    async def test_cofounder_command_without_user_id_reports_honest_failure(self):
        db_mock = AsyncMock()
        sync_db_mock = MagicMock()
        service = CosaCofounderService(db_mock, sync_db=sync_db_mock)

        res = await service.handle_founder_message(
            message="Tìm cho tôi 20 khách hàng trong 30 ngày",
            workspace_id=1,
            user_id=None,
        )

        assert res.intent == Intent.FOUNDER_COMMAND.value
        assert res.mission_id is None
        assert "xác thực Founder" in res.message
