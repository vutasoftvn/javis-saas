from core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from founder_os.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyCommitment,
    CycleContract,
    CycleStage,
    Milestone,
    MilestoneEvidence,
    GateDecision,
    EvidenceItem,
    Project,
)
from founder_os.strategy.cycle_governance_service import CycleGovernanceService


def test_generate_standard_13week_stages():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3 Execution")
    db.query.return_value.filter.return_value.first.return_value = cycle
    db.query.return_value.filter.return_value.all.return_value = []

    service = CycleGovernanceService(db, ws_id, user_id)
    stages = service.generate_standard_stages(cycle_id)

    assert len(stages) == 5
    assert stages[0]["name"] == "Khám phá & Xác định Giả thuyết (Discovery)"
    assert stages[0]["start_week"] == 1
    assert stages[0]["end_week"] == 3
    assert stages[4]["start_week"] == 13
    assert db.commit.called


def test_upsert_cycle_contract():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3 Execution")
    db.query.return_value.filter.return_value.first.side_effect = [cycle, None]

    service = CycleGovernanceService(db, ws_id, user_id)
    contract = service.upsert_cycle_contract(
        cycle_id=cycle_id,
        success_definition="Đạt 50,000 USD ARR và 20 khách hàng",
        founder_capacity_per_week=35.0,
        reserved_buffer_percent=25.0,
        ai_budget=500.0,
        status_val="approved",
    )

    assert contract["success_definition"] == "Đạt 50,000 USD ARR và 20 khách hàng"
    assert contract["founder_capacity_per_week"] == 35.0
    assert contract["status"] == "approved"
    assert contract["approved_by"] == str(user_id)
    assert db.commit.called


def test_create_milestone_and_link_evidence():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    stage_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    ev_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3")
    stage = CycleStage(id=stage_id, workspace_id=ws_id, cycle_id=cycle_id, name="Building", start_week=4, end_week=7)
    proj = Project(id=proj_id, workspace_id=ws_id, title="Main App")
    ev = EvidenceItem(id=ev_id, workspace_id=ws_id, title="Test Report", source_type="doc", reliability="high")

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == CycleStage:
            m.filter.return_value.first.return_value = stage
        elif model == Project:
            m.filter.return_value.first.return_value = proj
        elif model == EvidenceItem:
            m.filter.return_value.first.return_value = ev
        elif model == Milestone:
            ms = Milestone(
                id=generate_snowflake_id(),
                workspace_id=ws_id,
                cycle_id=cycle_id,
                stage_id=stage_id,
                project_id=proj_id,
                name="MVP Launch Alpha",
            )
            m.filter.return_value.first.return_value = ms
            m.filter.return_value.all.return_value = []
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_mock

    service = CycleGovernanceService(db, ws_id, user_id)
    ms = service.create_milestone(
        name="MVP Launch Alpha",
        cycle_id=cycle_id,
        stage_id=stage_id,
        project_id=proj_id,
        due_week=7,
        acceptance_criteria="5 active alpha testers",
    )

    assert ms["name"] == "MVP Launch Alpha"
    assert ms["due_week"] == 7

    # Link evidence
    link = service.link_evidence(
        milestone_id=int(ms["id"]),
        evidence_id=ev_id,
        relevance_note="Báo cáo kiểm thử 5 người dùng đầu tiên",
    )
    assert link["evidence_title"] == "Test Report"
    assert link["relevance_note"] == "Báo cáo kiểm thử 5 người dùng đầu tiên"


def test_record_gate_decision():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()
    proj = Project(id=proj_id, workspace_id=ws_id, title="Expansion MVP", status="Active")
    db.query.return_value.filter.return_value.first.return_value = proj

    service = CycleGovernanceService(db, ws_id, user_id)
    decision = service.record_gate_decision(
        project_id=proj_id,
        decision="GO",
        rationale="Mọi chỉ số kiểm chứng đã vượt mục tiêu đặt ra.",
        evidence_summary="5/5 khách hàng phản hồi tích cực.",
        next_step_instructions="Chuyển sang giai đoạn Tăng trưởng & Scale.",
    )

    assert decision["decision"] == "GO"
    assert decision["rationale"] == "Mọi chỉ số kiểm chứng đã vượt mục tiêu đặt ra."
    assert decision["decided_by"] == str(user_id)
    assert db.commit.called


def test_update_weekly_mission():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()

    db = MagicMock()
    plan = WeeklyPlan(
        id=plan_id,
        workspace_id=ws_id,
        cycle_id=generate_snowflake_id(),
        week_no=5,
        focus="Focus on Onboarding",
    )

    db.query.return_value.filter.return_value.first.return_value = plan
    db.query.return_value.filter.return_value.all.return_value = []

    service = CycleGovernanceService(db, ws_id, user_id)
    updated = service.update_weekly_mission(
        plan_id=plan_id,
        mission="Hoàn thành luồng Onboarding tự động và kiểm thử chuyển đổi",
        success_criteria={"activation_rate": ">60%", "user_tests": 10},
        outcome_score=0.85,
    )

    assert updated["mission"] == "Hoàn thành luồng Onboarding tự động và kiểm thử chuyển đổi"
    assert updated["outcome_score"] == 0.85
    assert db.commit.called
