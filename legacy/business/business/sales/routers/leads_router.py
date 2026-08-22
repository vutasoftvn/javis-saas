from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workspace_member
from core.feature_flags import (
    FLAG_LEAD_MANAGEMENT_V13_2,
    FLAG_MARKETING_SALES_HANDOFF_V13_2,
    FLAG_SALES_FUNCTION_V13,
    require_flag,
)
from db.models import WorkspaceMember
from db.session import get_db
from business.sales.models import SalesLead
from business.sales.domain.leads import LeadService

router = APIRouter()


class LeadCreate(BaseModel):
    name: str
    company: Optional[str] = None
    account_id: Optional[int] = None
    contact_id: Optional[int] = None
    key_result_id: Optional[int] = None
    stage: str = "NEW"
    value: Optional[float] = None
    source: Optional[str] = None
    source_campaign_id: Optional[int] = None


class LeadQualify(BaseModel):
    fit: Optional[str] = None
    need: Optional[str] = None
    urgency: Optional[str] = None
    authority: Optional[str] = None
    ability_to_pay: Optional[str] = None
    fit_score: Optional[float] = None
    intent_score: Optional[float] = None
    engagement_score: Optional[float] = None


class LeadConvert(BaseModel):
    product: Optional[str] = None
    estimated_value: Optional[float] = None
    expected_close_date: Optional[datetime] = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session, required_subflag: str = FLAG_LEAD_MANAGEMENT_V13_2) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, required_subflag, workspace_id)


def _serialize_lead(lead: SalesLead):
    return {
        "id": str(lead.id),
        "workspace_id": str(lead.workspace_id),
        "account_id": str(lead.account_id) if lead.account_id else None,
        "contact_id": str(lead.contact_id) if lead.contact_id else None,
        "key_result_id": str(lead.key_result_id) if lead.key_result_id else None,
        "name": lead.name,
        "company": lead.company,
        "stage": lead.stage,
        "value": lead.value,
        "source": lead.source,
        "source_campaign_id": str(lead.source_campaign_id) if lead.source_campaign_id else None,
        "fit_score": lead.fit_score,
        "intent_score": lead.intent_score,
        "engagement_score": lead.engagement_score,
        "qualification_status": lead.qualification_status,
        "disqualification_reason": lead.disqualification_reason,
        "next_action_at": lead.next_action_at.isoformat() if lead.next_action_at else None,
        "next_action_type": lead.next_action_type,
        "owner_id": str(lead.owner_id) if lead.owner_id else None,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


@router.get("/leads")
def list_leads(
    workspace_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    leads = (
        db.query(SalesLead)
        .filter(SalesLead.workspace_id == workspace_id)
        .order_by(SalesLead.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"leads": [_serialize_lead(lead) for lead in leads]}


@router.post("/leads", status_code=201)
def create_lead(
    data: LeadCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    lead = LeadService.create_lead(
        db=db,
        workspace_id=workspace_id,
        name=data.name,
        company=data.company,
        account_id=data.account_id,
        contact_id=data.contact_id,
        key_result_id=data.key_result_id,
        stage=data.stage,
        value=data.value,
        source=data.source,
        source_campaign_id=data.source_campaign_id,
        owner_id=member.user_id,
    )
    return _serialize_lead(lead)


@router.post("/leads/from-handoff/{handoff_id}", status_code=200)
def intake_leads_from_handoff(
    handoff_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db, required_subflag=FLAG_MARKETING_SALES_HANDOFF_V13_2)
    res = LeadService.intake_from_handoff(db, workspace_id, handoff_id)
    return res


@router.post("/leads/{lead_id}/qualify")
def qualify_lead(
    lead_id: int,
    data: LeadQualify,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    lead = LeadService.qualify_lead(
        db=db,
        workspace_id=workspace_id,
        lead_id=lead_id,
        fit=data.fit,
        need=data.need,
        urgency=data.urgency,
        authority=data.authority,
        ability_to_pay=data.ability_to_pay,
        fit_score=data.fit_score,
        intent_score=data.intent_score,
        engagement_score=data.engagement_score,
        actor_id=member.user_id,
    )
    return _serialize_lead(lead)


@router.post("/leads/{lead_id}/convert", status_code=201)
def convert_lead(
    lead_id: int,
    data: LeadConvert,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    opp = LeadService.convert_lead(
        db=db,
        workspace_id=workspace_id,
        lead_id=lead_id,
        product=data.product,
        estimated_value=data.estimated_value,
        expected_close_date=data.expected_close_date,
        owner_id=member.user_id,
    )
    return {
        "opportunity_id": str(opp.id),
        "account_id": str(opp.account_id),
        "stage": opp.stage,
        "source_lead_id": str(opp.source_lead_id),
    }
