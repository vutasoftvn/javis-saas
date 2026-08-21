from core.snowflake import generate_snowflake_id
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from core.tenancy import (
    get_project_scoped,
    get_cycle_scoped,
    get_stage_scoped,
    get_milestone_scoped,
    get_cycle_contract_scoped,
    get_gate_decision_scoped,
    get_classification_scoped,
    get_methodology_plan_scoped,
)
from founder_os.strategy.models import (
    Project,
    TwelveWeekCycle,
    WeeklyPlan,
    ProjectClassification,
    MethodologyPlan,
    CycleContract,
    CycleStage,
    Milestone,
    MilestoneEvidence,
    GateDecision,
)


# ===========================================================================
# Model Instantiation and Field Tests
# ===========================================================================

def test_project_model_v12_fields():
    ws_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    owner_id = generate_snowflake_id()
    portfolio_id = generate_snowflake_id()

    proj = Project(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain_id,
        title="mCOSA Platform",
        phase="PLANNING",
        current_gate="GATE_1",
        status="active",
        owner_id=owner_id,
        project_type="STRATEGIC",
        strategic_priority="P0",
        founder_attention_budget=15.5,
        portfolio_id=portfolio_id,
    )

    assert proj.project_type == "STRATEGIC"
    assert proj.strategic_priority == "P0"
    assert proj.founder_attention_budget == 15.5
    assert proj.portfolio_id == portfolio_id


def test_project_classification_model():
    ws_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    classification = ProjectClassification(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        project_id=proj_id,
        project_type="NEW_BUSINESS",
        strategic_depth="high",
        uncertainty_level="high",
        risk_level="medium",
        research_required=True,
        external_evidence_required=True,
        internal_context_required=True,
        recommended_methodologies=["PESTEL", "SWOT", "TOWS", "12WY"],
        human_required_areas=["pricing_decision", "investor_relations"],
        rationale="Entering unknown territory requires full strategic discovery.",
        confidence_score=0.92,
        classified_by=user_id,
    )

    assert classification.project_type == "NEW_BUSINESS"
    assert classification.research_required is True
    assert classification.confidence_score == 0.92
    assert "PESTEL" in classification.recommended_methodologies


def test_methodology_plan_model():
    ws_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    plan = MethodologyPlan(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        project_id=proj_id,
        selected_methodologies=["VISION_MISSION", "PESTEL", "SWOT", "TOWS", "OKR", "12WY"],
        rationale="Standard full strategy cycle.",
        status="active",
        custom_rules={"weekly_checkin_required": True},
        created_by=user_id,
    )

    assert plan.status == "active"
    assert len(plan.selected_methodologies) == 6
    assert plan.custom_rules["weekly_checkin_required"] is True


def test_cycle_contract_and_stage_models():
    ws_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    contract_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    contract = CycleContract(
        id=contract_id,
        workspace_id=ws_id,
        cycle_id=cycle_id,
        success_definition="MVP launched to 10 paying customers with 95% satisfaction.",
        goal_ids=[str(generate_snowflake_id())],
        kr_ids=[str(generate_snowflake_id())],
        founder_capacity_per_week=20.0,
        reserved_buffer_percent=25.0,
        ai_budget=500.0,
        operating_budget=2000.0,
        risk_constraints={"max_weekly_overtime_hours": 5},
        status="approved",
        approved_by=user_id,
        approved_at=datetime.utcnow(),
    )

    cycle = TwelveWeekCycle(
        id=cycle_id,
        workspace_id=ws_id,
        brain_id=generate_snowflake_id(),
        theme="Q3 Growth Sprint",
        status="active",
        cycle_contract_id=contract_id,
    )

    stage = CycleStage(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        cycle_id=cycle_id,
        name="Discovery & Validation",
        purpose="Validate value proposition with 15 customer interviews",
        start_week=1,
        end_week=3,
        order_no=1,
        expected_outcomes=["interview_synthesis", "persona_matrix"],
        status="in_progress",
    )

    assert contract.founder_capacity_per_week == 20.0
    assert cycle.cycle_contract_id == contract_id
    assert stage.start_week == 1
    assert stage.end_week == 3


def test_weekly_plan_v12_fields():
    ws_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    stage_id = generate_snowflake_id()

    weekly_plan = WeeklyPlan(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        cycle_id=cycle_id,
        stage_id=stage_id,
        week_no=3,
        focus="Customer interviews round 2",
        mission="Complete remaining 7 interviews and synthesize signals.",
        success_criteria={"interviews_done": 7, "synthesis_doc_approved": True},
        execution_score=0.88,
        outcome_score=0.94,
    )

    assert weekly_plan.stage_id == stage_id
    assert weekly_plan.mission == "Complete remaining 7 interviews and synthesize signals."
    assert weekly_plan.outcome_score == 0.94


def test_milestone_and_gate_decision_models():
    ws_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    stage_id = generate_snowflake_id()
    evidence_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    milestone_id = generate_snowflake_id()

    milestone = Milestone(
        id=milestone_id,
        workspace_id=ws_id,
        project_id=proj_id,
        cycle_id=cycle_id,
        stage_id=stage_id,
        name="Validation Gate 1",
        description="Core problem validated by target users.",
        due_week=3,
        required_artifacts=["interview_reports", "opportunity_scorecard"],
        required_metrics={"nps_interest": 8.0},
        acceptance_criteria="At least 8/10 interviewed users confirm hair-on-fire pain.",
        status="met",
    )

    join = MilestoneEvidence(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        milestone_id=milestone_id,
        evidence_id=evidence_id,
        relevance_note="Primary customer interview recording and transcript.",
    )

    gate = GateDecision(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        project_id=proj_id,
        milestone_id=milestone_id,
        stage_id=stage_id,
        decision="GO",
        rationale="Strong market demand verified across all 15 customer sessions.",
        evidence_summary="12/15 users confirmed willingness to pre-pay.",
        evidence_refs=[str(evidence_id)],
        next_step_instructions="Proceed to MVP build phase in weeks 4-7.",
        decided_by=user_id,
    )

    assert milestone.status == "met"
    assert join.milestone_id == milestone_id
    assert gate.decision == "GO"
    assert gate.decided_by == user_id


# ===========================================================================
# Zero-Trust Tenancy Scoping Tests
# ===========================================================================

def test_get_project_scoped_success_and_cross_tenant():
    ws_id = generate_snowflake_id()
    other_ws_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    proj = MagicMock(spec=Project)
    proj.id = proj_id
    proj.workspace_id = ws_id

    db = MagicMock()
    # Mock find by matching workspace
    db.query.return_value.filter.return_value.first.side_effect = (
        lambda: proj if db.query.return_value.filter.call_args[0][1].right.value == ws_id else None
    )

    # 1. Matching workspace -> returns project
    res = get_project_scoped(db, proj_id, ws_id)
    assert res == proj

    # 2. Other workspace -> raises 404
    with pytest.raises(HTTPException) as exc:
        get_project_scoped(db, proj_id, other_ws_id)
    assert exc.value.status_code == 404


def test_get_cycle_scoped_cross_tenant():
    ws_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    cycle = MagicMock(spec=TwelveWeekCycle)
    cycle.id = cycle_id
    cycle.workspace_id = ws_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = cycle

    assert get_cycle_scoped(db, cycle_id, ws_id) == cycle

    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_cycle_scoped(db, cycle_id, generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_stage_scoped_cross_tenant():
    ws_id = generate_snowflake_id()
    stage_id = generate_snowflake_id()
    stage = MagicMock(spec=CycleStage)
    stage.id = stage_id
    stage.workspace_id = ws_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = stage
    assert get_stage_scoped(db, stage_id, ws_id) == stage

    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_stage_scoped(db, stage_id, generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_milestone_scoped_cross_tenant():
    ws_id = generate_snowflake_id()
    milestone_id = generate_snowflake_id()
    milestone = MagicMock(spec=Milestone)
    milestone.id = milestone_id
    milestone.workspace_id = ws_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = milestone
    assert get_milestone_scoped(db, milestone_id, ws_id) == milestone

    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_milestone_scoped(db, milestone_id, generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_cycle_contract_scoped_cross_tenant():
    ws_id = generate_snowflake_id()
    contract_id = generate_snowflake_id()
    contract = MagicMock(spec=CycleContract)
    contract.id = contract_id
    contract.workspace_id = ws_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = contract
    assert get_cycle_contract_scoped(db, contract_id, ws_id) == contract

    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_cycle_contract_scoped(db, contract_id, generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_gate_decision_scoped_cross_tenant():
    ws_id = generate_snowflake_id()
    decision_id = generate_snowflake_id()
    decision = MagicMock(spec=GateDecision)
    decision.id = decision_id
    decision.workspace_id = ws_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = decision
    assert get_gate_decision_scoped(db, decision_id, ws_id) == decision

    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_gate_decision_scoped(db, decision_id, generate_snowflake_id())
    assert exc.value.status_code == 404


def test_get_classification_and_methodology_plan_scoped_cross_tenant():
    ws_id = generate_snowflake_id()
    cls_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()

    classification = MagicMock(spec=ProjectClassification)
    classification.id = cls_id
    classification.workspace_id = ws_id

    plan = MagicMock(spec=MethodologyPlan)
    plan.id = plan_id
    plan.workspace_id = ws_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = classification
    assert get_classification_scoped(db, cls_id, ws_id) == classification

    db.query.return_value.filter.return_value.first.return_value = plan
    assert get_methodology_plan_scoped(db, plan_id, ws_id) == plan

    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_classification_scoped(db, cls_id, generate_snowflake_id())
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        get_methodology_plan_scoped(db, plan_id, generate_snowflake_id())
    assert exc.value.status_code == 404
