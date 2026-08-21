from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_OPPORTUNITY_MANAGEMENT_V13_2, FLAG_SALES_FUNCTION_V13, require_flag
from db.models import WorkspaceMember
from db.session import get_db
from business.sales.models import SalesOpportunity
from business.sales.domain.opportunities import OpportunityService

router = APIRouter()


class OpportunityCreate(BaseModel):
    account_id: int
    cycle_id: Optional[int] = None
    product: Optional[str] = None
    primary_contact_id: Optional[int] = None
    source_lead_id: Optional[int] = None
    estimated_value: Optional[float] = None
    currency: str = "VND"
    expected_close_date: Optional[datetime] = None
    pain_points: Optional[List[str]] = None
    needs: Optional[List[str]] = None
    objections: Optional[List[str]] = None
    competitors: Optional[List[str]] = None


class OpportunityStageChange(BaseModel):
    target_stage: str


class OpportunityWin(BaseModel):
    won_reason: str
    evidence: Optional[str] = None


class OpportunityLose(BaseModel):
    lost_reason: str
    lost_reason_detail: Optional[str] = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, FLAG_OPPORTUNITY_MANAGEMENT_V13_2, workspace_id)


def _serialize_opportunity(opp: SalesOpportunity):
    return {
        "id": str(opp.id),
        "workspace_id": str(opp.workspace_id),
        "cycle_id": str(opp.cycle_id) if opp.cycle_id else None,
        "account_id": str(opp.account_id),
        "primary_contact_id": str(opp.primary_contact_id) if opp.primary_contact_id else None,
        "owner_id": str(opp.owner_id) if opp.owner_id else None,
        "source_lead_id": str(opp.source_lead_id) if opp.source_lead_id else None,
        "product": opp.product,
        "stage": opp.stage,
        "estimated_value": opp.estimated_value,
        "currency": opp.currency,
        "probability": opp.probability,
        "expected_close_date": opp.expected_close_date.isoformat() if opp.expected_close_date else None,
        "pain_points": opp.pain_points,
        "needs": opp.needs,
        "objections": opp.objections,
        "competitors": opp.competitors,
        "next_action": opp.next_action,
        "next_action_due_at": opp.next_action_due_at.isoformat() if opp.next_action_due_at else None,
        "won_reason": opp.won_reason,
        "lost_reason": opp.lost_reason,
        "lost_reason_detail": opp.lost_reason_detail,
        "created_at": opp.created_at.isoformat() if opp.created_at else None,
        "updated_at": opp.updated_at.isoformat() if opp.updated_at else None,
    }


@router.post("/opportunities", status_code=201)
def create_opportunity(
    data: OpportunityCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opp = OpportunityService.create_opportunity(
        db=db,
        workspace_id=workspace_id,
        account_id=data.account_id,
        cycle_id=data.cycle_id,
        product=data.product,
        primary_contact_id=data.primary_contact_id,
        source_lead_id=data.source_lead_id,
        estimated_value=data.estimated_value,
        currency=data.currency,
        expected_close_date=data.expected_close_date,
        owner_id=member.user_id,
        pain_points=data.pain_points,
        needs=data.needs,
        objections=data.objections,
        competitors=data.competitors,
    )
    return _serialize_opportunity(opp)


@router.get("/opportunities")
def list_opportunities(
    workspace_id: int,
    account_id: Optional[int] = None,
    stage: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opps = OpportunityService.list_opportunities(
        db, workspace_id, account_id=account_id, stage=stage, limit=limit, offset=offset
    )
    return {"opportunities": [_serialize_opportunity(o) for o in opps]}


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(
    opportunity_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opp = OpportunityService.get_opportunity(db, workspace_id, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _serialize_opportunity(opp)


@router.post("/opportunities/{opportunity_id}/stage")
def transition_opportunity_stage(
    opportunity_id: int,
    data: OpportunityStageChange,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opp = OpportunityService.transition_stage(
        db=db,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        target_stage=data.target_stage,
        actor_id=member.user_id,
    )
    return _serialize_opportunity(opp)


@router.post("/opportunities/{opportunity_id}/win")
def win_opportunity(
    opportunity_id: int,
    data: OpportunityWin,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opp = OpportunityService.win_opportunity(
        db=db,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        won_reason=data.won_reason,
        evidence=data.evidence,
        actor_id=member.user_id,
    )
    return _serialize_opportunity(opp)


@router.post("/opportunities/{opportunity_id}/lose")
def lose_opportunity(
    opportunity_id: int,
    data: OpportunityLose,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opp = OpportunityService.lose_opportunity(
        db=db,
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        lost_reason=data.lost_reason,
        lost_reason_detail=data.lost_reason_detail,
        actor_id=member.user_id,
    )
    return _serialize_opportunity(opp)
