from core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from founder_os.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyReview,
    CycleReview,
    CelebrationRecord,
    Milestone,
)
from founder_os.strategy.review_service import ReviewAndTransitionService


def test_create_or_update_weekly_review():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Execution Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=3, focus="Week 3 Focus")

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.first.return_value = plan
        elif model == WeeklyReview:
            m.filter.return_value.first.return_value = None
        else:
            m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_mock

    service = ReviewAndTransitionService(db, ws_id, user_id)
    review = service.create_or_update_weekly_review(
        cycle_id=cycle_id,
        weekly_plan_id=plan_id,
        execution_score=0.9,
        outcome_score=0.85,
        evidence_learned="Khách hàng ưa chuộng giao diện tối giản hơn",
        assumptions_confirmed={"pricing_acceptable": True},
        assumptions_invalidated={"onboarding_easy": False},
        recommendation="CONTINUE",
        narrative_summary="Tuần hoàn thành tốt các chỉ số chính",
    )

    assert review["execution_score"] == 0.9
    assert review["outcome_score"] == 0.85
    assert review["recommendation"] == "CONTINUE"
    assert review["evidence_learned"] == "Khách hàng ưa chuộng giao diện tối giản hơn"
    assert db.commit.called


def test_weekly_review_invalid_recommendation():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Execution Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=3, focus="Week 3 Focus")
    db.query.return_value.filter.return_value.first.side_effect = [cycle, plan]

    service = ReviewAndTransitionService(db, ws_id, user_id)
    with pytest.raises(HTTPException) as exc:
        service.create_or_update_weekly_review(
            cycle_id=cycle_id,
            weekly_plan_id=plan_id,
            execution_score=0.9,
            outcome_score=0.85,
            recommendation="INVALID_ACTION",
        )
    assert exc.value.status_code == 422


def test_finalize_week13():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3 Execution", status="active")

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model in (CycleReview, CelebrationRecord):
            m.filter.return_value.first.return_value = None
        else:
            m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_mock

    service = ReviewAndTransitionService(db, ws_id, user_id)
    res = service.finalize_week13(
        cycle_id=cycle_id,
        overall_execution_score=0.88,
        overall_outcome_score=0.92,
        okr_achievement_rate=0.85,
        strategic_learnings="Tập trung vào 1 nhóm khách hàng ngách mang lại ROI cao gấp đôi",
        systemic_blockers="Quy trình thanh toán ngân hàng còn chậm",
        celebration_title="Lễ Tổng Kết & Tôn Vinh Chu Kỳ Q3",
        rewards_or_rituals="Team building và thưởng cổ phần thưởng nóng",
    )

    assert res["cycle_id"] == str(cycle_id)
    assert res["cycle_review"]["overall_execution_score"] == 0.88
    assert res["celebration"]["title"] == "Lễ Tổng Kết & Tôn Vinh Chu Kỳ Q3"
    assert cycle.status == "completed"
    assert db.commit.called


def test_week13_readiness_audit():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3 Execution", status="active")
    plans = [WeeklyPlan(id=generate_snowflake_id(), workspace_id=ws_id, cycle_id=cycle_id, week_no=i, focus=f"W{i}") for i in range(1, 13)]
    reviews = [WeeklyReview(id=generate_snowflake_id(), workspace_id=ws_id, cycle_id=cycle_id, weekly_plan_id=p.id, week_no=p.week_no) for p in plans[:11]]
    milestones = [Milestone(id=generate_snowflake_id(), workspace_id=ws_id, cycle_id=cycle_id, name=f"M{i}", status="completed") for i in range(4)]

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.all.return_value = plans
        elif model == WeeklyReview:
            m.filter.return_value.all.return_value = reviews
        elif model == Milestone:
            m.filter.return_value.all.return_value = milestones
        else:
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_mock

    service = ReviewAndTransitionService(db, ws_id, user_id)
    readiness = service.validate_week13_transition_readiness(cycle_id)

    assert readiness["total_weeks"] == 12
    assert readiness["completed_weekly_reviews"] == 11
    assert readiness["ready_for_week13"] is True
    assert readiness["week13_mandatory"] is True
