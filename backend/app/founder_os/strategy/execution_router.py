from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.snowflake import generate_snowflake_id

from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import (
    WorkspaceMember, TwelveWeekCycle, WeeklyPlan, WeeklyCommitment, Brain,
    CycleContract, CycleStage, Milestone, MilestoneEvidence, GateDecision
)
from app.founder_os.strategy.cycle_governance_service import CycleGovernanceService
from app.founder_os.strategy.planning_compiler_service import PlanningCompilerService
from app.founder_os.strategy.review_service import ReviewAndTransitionService
from app.founder_os.strategy.timeline_service import StrategicTimelineService
from app.core.feature_flags import (
    require_flag,
    FLAG_CYCLE_13WEEK_V12,
    FLAG_MILESTONES_GATES_V12,
    FLAG_WEEKLY_MISSIONS_V12,
)

router = APIRouter()




def _serialize_twelve_week_cycle(c: TwelveWeekCycle, db: Optional[Session] = None) -> dict:
    stages_count = 0
    milestones_count = 0
    has_contract = c.cycle_contract_id is not None
    if db:
        stages_count = db.query(CycleStage).filter(CycleStage.cycle_id == c.id).count()
        milestones_count = db.query(Milestone).filter(Milestone.cycle_id == c.id).count()

    return {
        "id": str(c.id),
        "theme": c.theme,
        "project_id": str(c.project_id) if c.project_id else None,
        "duration_weeks": c.duration_weeks or 13,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "end_date": c.end_date.isoformat() if c.end_date else None,
        "okr_cycle_id": str(c.okr_cycle_id) if c.okr_cycle_id else None,
        "cycle_contract_id": str(c.cycle_contract_id) if c.cycle_contract_id else None,
        "has_contract": has_contract,
        "stages_count": stages_count,
        "milestones_count": milestones_count,
        "commitment_level": c.commitment_level,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_weekly_plan(p: WeeklyPlan) -> dict:
    start_dt = p.start_date
    end_dt = getattr(p, "end_date", None)
    if not end_dt and start_dt:
        from datetime import timedelta
        end_dt = start_dt + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return {
        "id": str(p.id),
        "cycle_id": str(p.cycle_id),
        "week_no": p.week_no,
        "week_number": p.week_no,
        "start_date": start_dt.isoformat() if start_dt else None,
        "end_date": end_dt.isoformat() if end_dt else None,
        "focus": p.focus,
        "theme": p.focus,
        "mission": p.mission,
        "success_criteria": p.success_criteria,
        "stage_id": str(p.stage_id) if p.stage_id else None,
        "outcome_score": p.outcome_score,
        "execution_score": p.execution_score,
        "blockers": p.blockers_jsonb,
        "reflection": p.reflection,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }



def _serialize_weekly_commitment(c: WeeklyCommitment) -> dict:
    return {
        "id": str(c.id),
        "weekly_plan_id": str(c.weekly_plan_id),
        "initiative_id": str(c.initiative_id) if c.initiative_id else None,
        "title": c.title,
        "status": c.status,
        "planned_effort": c.planned_effort,
        "commitment_owner_type": c.commitment_owner_type or "FOUNDER",
        "execution_mode": c.execution_mode or "MANUAL",
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }



# ==========================================
# 12-Week Cycles
# ==========================================

class TwelveWeekCycleCreate(BaseModel):
    theme: str
    project_id: Optional[int] = None
    duration_weeks: Optional[int] = 13
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    okr_cycle_id: Optional[int] = None
    commitment_level: Optional[str] = "high"
    status: Optional[str] = "active"


class TwelveWeekCycleUpdate(BaseModel):
    theme: Optional[str] = None
    project_id: Optional[int] = None
    duration_weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    okr_cycle_id: Optional[int] = None
    commitment_level: Optional[str] = None
    status: Optional[str] = None


@router.get("/twelve-week-cycles")
def list_twelve_week_cycles(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    cycles = db.query(TwelveWeekCycle).filter(TwelveWeekCycle.workspace_id == workspace_id).order_by(TwelveWeekCycle.created_at.desc()).all()
    return {"cycles": [_serialize_twelve_week_cycle(c) for c in cycles]}


@router.post("/twelve-week-cycles")
def create_twelve_week_cycle(
    workspace_id: int,
    data: TwelveWeekCycleCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    from datetime import timedelta
    start_dt = data.start_date or datetime.utcnow()
    # Align to Monday
    monday_start = (start_dt - timedelta(days=start_dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    dur_weeks = data.duration_weeks or 13
    end_dt = data.end_date or (monday_start + timedelta(weeks=dur_weeks) - timedelta(seconds=1))

    cycle = TwelveWeekCycle(
        workspace_id=workspace_id,
        brain_id=brain.id if brain else generate_snowflake_id(),
        project_id=data.project_id,
        duration_weeks=dur_weeks,
        theme=data.theme,
        start_date=monday_start,
        end_date=end_dt,
        okr_cycle_id=data.okr_cycle_id,
        commitment_level=data.commitment_level or "high",
        status=data.status or "active",
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return _serialize_twelve_week_cycle(cycle)


# ==========================================
# Weekly Plans
# ==========================================

class WeeklyPlanCreate(BaseModel):
    cycle_id: Optional[int] = None
    week_no: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    focus: Optional[str] = None
    execution_score: Optional[float] = 0.0
    blockers: Optional[dict] = None
    reflection: Optional[str] = None


class WeeklyPlanUpdate(BaseModel):
    focus: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    execution_score: Optional[float] = None
    blockers: Optional[dict] = None
    reflection: Optional[str] = None


@router.get("/weekly-plans")
def list_weekly_plans(
    workspace_id: int,
    cycle_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    query = db.query(WeeklyPlan).filter(WeeklyPlan.workspace_id == workspace_id)
    if cycle_id:
        query = query.filter(WeeklyPlan.cycle_id == cycle_id)
    plans = query.order_by(WeeklyPlan.week_no.asc()).all()
    return {"plans": [_serialize_weekly_plan(p) for p in plans]}


@router.post("/weekly-plans")
def create_weekly_plan(
    workspace_id: int,
    data: WeeklyPlanCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    target_cycle_id = data.cycle_id
    from datetime import timedelta
    if not target_cycle_id:
        active_cycle = db.query(TwelveWeekCycle).filter(TwelveWeekCycle.workspace_id == workspace_id).order_by(TwelveWeekCycle.created_at.desc()).first()
        if active_cycle:
            target_cycle_id = active_cycle.id
        else:
            brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
            now = datetime.utcnow()
            monday_now = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            new_cycle = TwelveWeekCycle(
                workspace_id=workspace_id,
                brain_id=brain.id if brain else generate_snowflake_id(),
                theme="Default Execution Cycle",
                start_date=monday_now,
                end_date=monday_now + timedelta(weeks=13) - timedelta(seconds=1),
                status="active"
            )
            db.add(new_cycle)
            db.flush()
            target_cycle_id = new_cycle.id

    start_dt = data.start_date
    end_dt = data.end_date
    if not start_dt:
        cycle = db.query(TwelveWeekCycle).filter(TwelveWeekCycle.id == target_cycle_id).first()
        if cycle and cycle.start_date:
            cycle_monday = (cycle.start_date - timedelta(days=cycle.start_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = cycle_monday + timedelta(weeks=data.week_no - 1)
        else:
            now = datetime.utcnow()
            monday_now = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = monday_now + timedelta(weeks=data.week_no - 1)

    if not end_dt and start_dt:
        end_dt = start_dt + timedelta(days=6, hours=23, minutes=59, seconds=59)

    plan = WeeklyPlan(
        workspace_id=workspace_id,
        cycle_id=target_cycle_id,
        week_no=data.week_no,
        start_date=start_dt,
        end_date=end_dt,
        focus=data.focus,
        execution_score=data.execution_score or 0.0,
        blockers_jsonb=data.blockers or {},
        reflection=data.reflection,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_weekly_plan(plan)


@router.put("/weekly-plans/{plan_id}")
def update_weekly_plan(
    plan_id: int,
    workspace_id: int,
    data: WeeklyPlanUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id, WeeklyPlan.workspace_id == workspace_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    if data.focus is not None:
        plan.focus = data.focus
    if data.execution_score is not None:
        plan.execution_score = data.execution_score
    if data.blockers is not None:
        plan.blockers_jsonb = data.blockers
    if data.reflection is not None:
        plan.reflection = data.reflection

    db.commit()
    db.refresh(plan)
    return _serialize_weekly_plan(plan)


# ==========================================
# Weekly Commitments
# ==========================================

class WeeklyCommitmentCreate(BaseModel):
    weekly_plan_id: int
    initiative_id: Optional[int] = None
    title: str
    planned_effort: Optional[str] = "medium"
    status: Optional[str] = "todo"
    commitment_owner_type: Optional[str] = "FOUNDER"
    execution_mode: Optional[str] = "MANUAL"


class WeeklyCommitmentUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    planned_effort: Optional[str] = None
    commitment_owner_type: Optional[str] = None
    execution_mode: Optional[str] = None


@router.get("/weekly-commitments")
def list_weekly_commitments(
    workspace_id: int,
    weekly_plan_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    query = db.query(WeeklyCommitment).filter(WeeklyCommitment.workspace_id == workspace_id)
    if weekly_plan_id:
        query = query.filter(WeeklyCommitment.weekly_plan_id == weekly_plan_id)
    commitments = query.order_by(WeeklyCommitment.created_at.asc()).all()
    return {"commitments": [_serialize_weekly_commitment(c) for c in commitments]}


@router.post("/weekly-commitments")
def create_weekly_commitment(
    workspace_id: int,
    data: WeeklyCommitmentCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == data.weekly_plan_id, WeeklyPlan.workspace_id == workspace_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    commitment = WeeklyCommitment(
        workspace_id=workspace_id,
        weekly_plan_id=data.weekly_plan_id,
        initiative_id=data.initiative_id,
        title=data.title,
        planned_effort=data.planned_effort or "medium",
        status=data.status or "todo",
        commitment_owner_type=data.commitment_owner_type or "FOUNDER",
        execution_mode=data.execution_mode or "MANUAL",
    )
    db.add(commitment)
    db.commit()
    db.refresh(commitment)
    return _serialize_weekly_commitment(commitment)


@router.put("/weekly-commitments/{commitment_id}")
def update_weekly_commitment(
    commitment_id: int,
    workspace_id: int,
    data: WeeklyCommitmentUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    commitment = db.query(WeeklyCommitment).filter(WeeklyCommitment.id == commitment_id, WeeklyCommitment.workspace_id == workspace_id).first()
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    if data.title is not None:
        commitment.title = data.title
    if data.status is not None:
        commitment.status = data.status
    if data.planned_effort is not None:
        commitment.planned_effort = data.planned_effort
    if data.commitment_owner_type is not None:
        commitment.commitment_owner_type = data.commitment_owner_type
    if data.execution_mode is not None:
        commitment.execution_mode = data.execution_mode

    db.commit()
    db.refresh(commitment)
    return _serialize_weekly_commitment(commitment)


@router.delete("/weekly-commitments/{commitment_id}")
def delete_weekly_commitment(
    commitment_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    commitment = db.query(WeeklyCommitment).filter(WeeklyCommitment.id == commitment_id, WeeklyCommitment.workspace_id == workspace_id).first()
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    db.delete(commitment)
    db.commit()
    return {"status": "deleted", "id": str(commitment_id)}


# ==========================================
# mCOSA V12 — 13-Week Execution & Governance (Sprint 3)
# ==========================================

# --- Cycle Stages ---

class CycleStageCreate(BaseModel):
    name: str
    start_week: int
    end_week: int
    order_no: int
    purpose: Optional[str] = None
    expected_outcomes: Optional[dict] = None


class CycleStageUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    start_week: Optional[int] = None
    end_week: Optional[int] = None
    status: Optional[str] = None
    expected_outcomes: Optional[dict] = None


@router.get("/twelve-week-cycles/{cycle_id}/stages")
def list_cycle_stages(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return {"stages": service.list_stages(cycle_id)}


@router.post("/twelve-week-cycles/{cycle_id}/stages")
def create_cycle_stage(
    cycle_id: int,
    workspace_id: int,
    data: CycleStageCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.create_stage(
        cycle_id=cycle_id,
        name=data.name,
        start_week=data.start_week,
        end_week=data.end_week,
        order_no=data.order_no,
        purpose=data.purpose,
        expected_outcomes=data.expected_outcomes,
    )


@router.post("/twelve-week-cycles/{cycle_id}/stages/generate-standard")
def generate_standard_cycle_stages(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return {"stages": service.generate_standard_stages(cycle_id)}


@router.put("/stages/{stage_id}")
def update_cycle_stage(
    stage_id: int,
    workspace_id: int,
    data: CycleStageUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.update_stage(
        stage_id=stage_id,
        name=data.name,
        purpose=data.purpose,
        start_week=data.start_week,
        end_week=data.end_week,
        status_val=data.status,
        expected_outcomes=data.expected_outcomes,
    )


@router.delete("/stages/{stage_id}")
def delete_cycle_stage(
    stage_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    service.delete_stage(stage_id)
    return {"status": "deleted", "id": str(stage_id)}


# --- Milestones & Evidence ---

class MilestoneCreate(BaseModel):
    name: str
    cycle_id: Optional[int] = None
    stage_id: Optional[int] = None
    project_id: Optional[int] = None
    description: Optional[str] = None
    due_week: Optional[int] = None
    due_date: Optional[datetime] = None
    required_artifacts: Optional[dict] = None
    required_metrics: Optional[dict] = None
    acceptance_criteria: Optional[str] = None


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    due_week: Optional[int] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    required_artifacts: Optional[dict] = None
    required_metrics: Optional[dict] = None
    acceptance_criteria: Optional[str] = None


@router.get("/milestones")
def list_milestones(
    workspace_id: int,
    cycle_id: Optional[int] = None,
    stage_id: Optional[int] = None,
    project_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return {"milestones": service.list_milestones(cycle_id, stage_id, project_id)}


@router.post("/milestones")
def create_milestone(
    workspace_id: int,
    data: MilestoneCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.create_milestone(
        name=data.name,
        cycle_id=data.cycle_id,
        stage_id=data.stage_id,
        project_id=data.project_id,
        description=data.description,
        due_week=data.due_week,
        due_date=data.due_date,
        required_artifacts=data.required_artifacts,
        required_metrics=data.required_metrics,
        acceptance_criteria=data.acceptance_criteria,
    )


@router.put("/milestones/{milestone_id}")
def update_milestone(
    milestone_id: int,
    workspace_id: int,
    data: MilestoneUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.update_milestone(
        milestone_id=milestone_id,
        name=data.name,
        description=data.description,
        due_week=data.due_week,
        due_date=data.due_date,
        status_val=data.status,
        required_artifacts=data.required_artifacts,
        required_metrics=data.required_metrics,
        acceptance_criteria=data.acceptance_criteria,
    )


@router.delete("/milestones/{milestone_id}")
def delete_milestone(
    milestone_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    service.delete_milestone(milestone_id)
    return {"status": "deleted", "id": str(milestone_id)}


class MilestoneEvidenceLink(BaseModel):
    evidence_id: int
    relevance_note: Optional[str] = None


@router.post("/milestones/{milestone_id}/evidence")
def link_milestone_evidence(
    milestone_id: int,
    workspace_id: int,
    data: MilestoneEvidenceLink,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.link_evidence(milestone_id, data.evidence_id, data.relevance_note)


@router.delete("/milestones/{milestone_id}/evidence/{evidence_id}")
def unlink_milestone_evidence(
    milestone_id: int,
    evidence_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    service.unlink_evidence(milestone_id, evidence_id)
    return {"status": "unlinked", "milestone_id": str(milestone_id), "evidence_id": str(evidence_id)}


# --- Gate Decisions ---

class GateDecisionCreate(BaseModel):
    project_id: int
    decision: str  # GO, ITERATE, HOLD, STOP, PIVOT
    rationale: str
    milestone_id: Optional[int] = None
    stage_id: Optional[int] = None
    evidence_summary: Optional[str] = None
    evidence_refs: Optional[dict] = None
    next_step_instructions: Optional[str] = None


@router.get("/gate-decisions")
def list_gate_decisions(
    workspace_id: int,
    project_id: Optional[int] = None,
    stage_id: Optional[int] = None,
    milestone_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return {"gate_decisions": service.list_gate_decisions(project_id, stage_id, milestone_id)}


@router.post("/gate-decisions")
def record_gate_decision(
    workspace_id: int,
    data: GateDecisionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_MILESTONES_GATES_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.record_gate_decision(
        project_id=data.project_id,
        decision=data.decision,
        rationale=data.rationale,
        milestone_id=data.milestone_id,
        stage_id=data.stage_id,
        evidence_summary=data.evidence_summary,
        evidence_refs=data.evidence_refs,
        next_step_instructions=data.next_step_instructions,
    )


# --- Cycle Contract ---

class CycleContractUpsert(BaseModel):
    success_definition: str
    founder_capacity_per_week: Optional[float] = 40.0
    reserved_buffer_percent: Optional[float] = 20.0
    ai_budget: Optional[float] = 0.0
    operating_budget: Optional[float] = 0.0
    goal_ids: Optional[List[str]] = None
    kr_ids: Optional[List[str]] = None
    risk_constraints: Optional[dict] = None
    status: Optional[str] = "draft"


@router.get("/twelve-week-cycles/{cycle_id}/contract")
def get_cycle_contract(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    contract = service.get_cycle_contract(cycle_id)
    if not contract:
        raise HTTPException(status_code=404, detail="CycleContract not found")
    return contract


@router.post("/twelve-week-cycles/{cycle_id}/contract")
def upsert_cycle_contract(
    cycle_id: int,
    workspace_id: int,
    data: CycleContractUpsert,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CYCLE_13WEEK_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.upsert_cycle_contract(
        cycle_id=cycle_id,
        success_definition=data.success_definition,
        founder_capacity_per_week=data.founder_capacity_per_week,
        reserved_buffer_percent=data.reserved_buffer_percent,
        ai_budget=data.ai_budget,
        operating_budget=data.operating_budget,
        goal_ids=data.goal_ids,
        kr_ids=data.kr_ids,
        risk_constraints=data.risk_constraints,
        status_val=data.status or "draft",
    )


# --- Weekly Mission ---

class WeeklyMissionUpdate(BaseModel):
    mission: Optional[str] = None
    success_criteria: Optional[dict] = None
    stage_id: Optional[int] = None
    outcome_score: Optional[float] = None


@router.put("/weekly-plans/{plan_id}/mission")
def update_weekly_mission(
    plan_id: int,
    workspace_id: int,
    data: WeeklyMissionUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_WEEKLY_MISSIONS_V12, workspace_id)
    service = CycleGovernanceService(db, workspace_id, member.user_id)
    return service.update_weekly_mission(
        plan_id=plan_id,
        mission=data.mission,
        success_criteria=data.success_criteria,
        stage_id=data.stage_id,
        outcome_score=data.outcome_score,
    )


# ==========================================
# mCOSA V12 — Planning Compiler to V10 Runtime (Sprint 4)
# ==========================================

@router.post("/twelve-week-cycles/{cycle_id}/compile")
def compile_twelve_week_cycle(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = PlanningCompilerService(db, workspace_id, member.user_id)
    return service.compile_cycle(cycle_id)


@router.post("/weekly-plans/{plan_id}/compile")
def compile_weekly_plan(
    plan_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = PlanningCompilerService(db, workspace_id, member.user_id)
    return service.compile_weekly_plan(plan_id)


@router.get("/twelve-week-cycles/{cycle_id}/compilation-status")
def get_cycle_compilation_status(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = PlanningCompilerService(db, workspace_id, member.user_id)
    return service.get_compilation_status(cycle_id)


@router.get("/twelve-week-cycles/{cycle_id}/timeline")
def get_cycle_timeline(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = StrategicTimelineService(db, workspace_id, member.user_id)
    return service.get_cycle_timeline(cycle_id)


# ==========================================
# mCOSA V12 — Weekly Review & Week 13 Strategic Transition (Sprint 5)
# ==========================================

class WeeklyReviewCreate(BaseModel):
    weekly_plan_id: int
    execution_score: float
    outcome_score: float
    evidence_learned: Optional[str] = None
    assumptions_confirmed: Optional[dict] = None
    assumptions_invalidated: Optional[dict] = None
    recommendation: Optional[str] = "CONTINUE"
    narrative_summary: Optional[str] = None


@router.post("/twelve-week-cycles/{cycle_id}/weekly-reviews")
def create_or_update_weekly_review(
    cycle_id: int,
    workspace_id: int,
    data: WeeklyReviewCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    return service.create_or_update_weekly_review(
        cycle_id=cycle_id,
        weekly_plan_id=data.weekly_plan_id,
        execution_score=data.execution_score,
        outcome_score=data.outcome_score,
        evidence_learned=data.evidence_learned,
        assumptions_confirmed=data.assumptions_confirmed,
        assumptions_invalidated=data.assumptions_invalidated,
        recommendation=data.recommendation or "CONTINUE",
        narrative_summary=data.narrative_summary,
    )


@router.get("/twelve-week-cycles/{cycle_id}/weekly-reviews")
def list_weekly_reviews(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    return {"weekly_reviews": service.list_weekly_reviews(cycle_id)}


@router.get("/weekly-plans/{plan_id}/review")
def get_weekly_plan_review(
    plan_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    review = service.get_weekly_review(plan_id)
    if not review:
        raise HTTPException(status_code=404, detail="WeeklyReview not found")
    return review


class Week13FinalizeRequest(BaseModel):
    overall_execution_score: float
    overall_outcome_score: float
    okr_achievement_rate: float
    strategic_learnings: Optional[str] = None
    systemic_blockers: Optional[str] = None
    portfolio_adjustments: Optional[dict] = None
    next_cycle_recommendations: Optional[str] = None
    celebration_title: Optional[str] = None
    milestones_achieved: Optional[dict] = None
    top_performers_recognized: Optional[dict] = None
    rewards_or_rituals: Optional[str] = None
    reflection_notes: Optional[str] = None


@router.post("/twelve-week-cycles/{cycle_id}/week13/finalize")
def finalize_week13(
    cycle_id: int,
    workspace_id: int,
    data: Week13FinalizeRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    return service.finalize_week13(
        cycle_id=cycle_id,
        overall_execution_score=data.overall_execution_score,
        overall_outcome_score=data.overall_outcome_score,
        okr_achievement_rate=data.okr_achievement_rate,
        strategic_learnings=data.strategic_learnings,
        systemic_blockers=data.systemic_blockers,
        portfolio_adjustments=data.portfolio_adjustments,
        next_cycle_recommendations=data.next_cycle_recommendations,
        celebration_title=data.celebration_title,
        milestones_achieved=data.milestones_achieved,
        top_performers_recognized=data.top_performers_recognized,
        rewards_or_rituals=data.rewards_or_rituals,
        reflection_notes=data.reflection_notes,
    )


@router.get("/twelve-week-cycles/{cycle_id}/week13/review")
def get_week13_review(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    review = service.get_cycle_review(cycle_id)
    if not review:
        raise HTTPException(status_code=404, detail="CycleReview not found")
    return review


@router.get("/twelve-week-cycles/{cycle_id}/week13/celebration")
def get_week13_celebration(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    celeb = service.get_celebration_record(cycle_id)
    if not celeb:
        raise HTTPException(status_code=404, detail="CelebrationRecord not found")
    return celeb


@router.get("/twelve-week-cycles/{cycle_id}/week13/readiness")
def get_week13_readiness(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    service = ReviewAndTransitionService(db, workspace_id, member.user_id)
    return service.validate_week13_transition_readiness(cycle_id)



