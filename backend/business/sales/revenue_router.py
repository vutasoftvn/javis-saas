from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from db.session import get_db
from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from business.sales import revenue_engine_service as service

router = APIRouter()


# ── Pydantic Request Models ───────────────────────────────────────────────────

class UpdateICPRequest(BaseModel):
    icp: Optional[Dict[str, Any]] = None
    brand_voice: Optional[Dict[str, Any]] = None
    positioning: Optional[Dict[str, Any]] = None
    personas: Optional[List[Dict[str, Any]]] = None
    value_proposition: Optional[Dict[str, Any]] = None


class CreateCampaignRequest(BaseModel):
    name: str = Field(..., description="Tên chiến dịch")
    funnel_stage: str = Field("discover", description="Giai đoạn phễu")
    channels: Optional[List[str]] = Field(default_factory=lambda: ["email", "landing_page"])
    budget: float = Field(0.0, description="Ngân sách chiến dịch")
    owner: Optional[str] = Field("Growth Agent")


class ConvertLeadRequest(BaseModel):
    title: Optional[str] = None
    estimated_value: float = Field(50000000.0, description="Giá trị ước tính của cơ hội")


class UpdateStageRequest(BaseModel):
    stage: str = Field(..., description="DISCOVERY | PROPOSAL | NEGOTIATION | WON | LOST")
    lost_reason: Optional[str] = None


class GenerateOutreachRequest(BaseModel):
    lead_id: str = Field(..., description="Snowflake string ID của Lead")
    channel: str = Field("email", description="email | zalo | telegram")
    tone: str = Field("professional", description="professional | friendly | urgent")
    focus_pain_point: Optional[str] = None


class CreateAccountRequest(BaseModel):
    name: str = Field(..., description="Tên công ty / Tên đối tác / Tên khách hàng")
    category: str = Field("CUSTOMER", description="CUSTOMER | PARTNER | VENDOR")
    domain: Optional[str] = None
    industry: Optional[str] = None
    size_segment: Optional[str] = None
    source: Optional[str] = None
    lifecycle_status: Optional[str] = None
    tags: Optional[List[str]] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/revenue/icp")
def get_icp(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return {"status": "success", "data": service.get_icp_context(db, workspace_id)}


@router.post("/workspaces/{workspace_id}/revenue/icp")
def update_icp(
    workspace_id: int,
    payload: UpdateICPRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    data = service.update_icp_context(db, workspace_id, payload.dict(exclude_unset=True))
    return {"status": "success", "data": data}


@router.get("/workspaces/{workspace_id}/revenue/campaigns")
def list_campaigns(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return {"status": "success", "data": service.list_campaigns(db, workspace_id)}


@router.post("/workspaces/{workspace_id}/revenue/campaigns")
def create_campaign(
    workspace_id: int,
    payload: CreateCampaignRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    res = service.create_campaign(
        db=db,
        workspace_id=workspace_id,
        name=payload.name,
        funnel_stage=payload.funnel_stage,
        channels=payload.channels,
        budget=payload.budget,
        owner=payload.owner,
    )
    return {"status": "success", "data": res}


@router.get("/workspaces/{workspace_id}/revenue/crm/leads")
def get_crm_leads(
    workspace_id: int,
    stage: Optional[str] = None,
    limit: int = 50,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return {"status": "success", "data": service.list_crm_leads(db, workspace_id, stage, limit)}


@router.post("/workspaces/{workspace_id}/revenue/crm/leads/{lead_id}/score")
def score_lead(
    workspace_id: int,
    lead_id: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        lid = int(lead_id)
        res = service.score_lead_with_ai(db, workspace_id, lid)
        return {"status": "success", "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/revenue/crm/leads/{lead_id}/convert-to-opportunity")
def convert_to_opportunity(
    workspace_id: int,
    lead_id: str,
    payload: ConvertLeadRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        lid = int(lead_id)
        res = service.convert_lead_to_opportunity(
            db=db,
            workspace_id=workspace_id,
            user_id=member.user_id,
            lead_id=lid,
            title=payload.title,
            estimated_value=payload.estimated_value,
        )
        return {"status": "success", "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workspaces/{workspace_id}/revenue/crm/pipeline")
def get_pipeline(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return {"status": "success", "data": service.get_pipeline_kanban(db, workspace_id)}


@router.patch("/workspaces/{workspace_id}/revenue/crm/opportunities/{opportunity_id}/stage")
def update_opportunity_stage(
    workspace_id: int,
    opportunity_id: str,
    payload: UpdateStageRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        oid = int(opportunity_id)
        res = service.update_opportunity_stage(
            db=db,
            workspace_id=workspace_id,
            user_id=member.user_id,
            opportunity_id=oid,
            stage=payload.stage,
            lost_reason=payload.lost_reason,
        )
        return {"status": "success", "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/revenue/outreach/generate")
def generate_outreach(
    workspace_id: int,
    payload: GenerateOutreachRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        lid = int(payload.lead_id)
        res = service.generate_outreach_draft(
            db=db,
            workspace_id=workspace_id,
            user_id=member.user_id,
            lead_id=lid,
            channel=payload.channel,
            tone=payload.tone,
            focus_pain_point=payload.focus_pain_point,
        )
        return {"status": "success", "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workspaces/{workspace_id}/revenue/crm/accounts")
def get_crm_accounts(
    workspace_id: int,
    account_type: Optional[str] = Query(None, description="CUSTOMER | PARTNER | VENDOR | ALL"),
    lifecycle_status: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    data = service.list_crm_accounts(
        db=db,
        workspace_id=workspace_id,
        account_type=account_type,
        lifecycle_status=lifecycle_status,
        search=search,
        tag=tag,
        limit=limit,
    )
    return {"status": "success", "data": data}


@router.post("/workspaces/{workspace_id}/revenue/crm/accounts")
def create_crm_account(
    workspace_id: int,
    payload: CreateAccountRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    try:
        data = service.create_crm_account(
            db=db,
            workspace_id=workspace_id,
            name=payload.name,
            category=payload.category,
            domain=payload.domain,
            industry=payload.industry,
            size_segment=payload.size_segment,
            source=payload.source,
            lifecycle_status=payload.lifecycle_status,
            tags=payload.tags,
            contact_name=payload.contact_name,
            contact_phone=payload.contact_phone,
            contact_email=payload.contact_email,
        )
        return {"status": "success", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
