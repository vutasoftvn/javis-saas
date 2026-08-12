from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_SALES_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.sales.models import SalesLead

router = APIRouter()


class LeadCreate(BaseModel):
    name: str
    company: str | None = None
    key_result_id: int | None = None
    value: float | None = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)


@router.get("/leads")
def list_leads(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member, db)
    leads = db.query(SalesLead).filter(SalesLead.workspace_id == workspace_id).order_by(SalesLead.created_at.desc()).all()
    return {"leads": [{"id": str(lead.id), "name": lead.name, "company": lead.company, "stage": lead.stage, "value": lead.value} for lead in leads]}


@router.post("/leads", status_code=201)
def create_lead(data: LeadCreate, workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member, db)
    lead = SalesLead(workspace_id=workspace_id, owner_id=member.user_id, **data.model_dump())
    db.add(lead); db.commit(); db.refresh(lead)
    return {"id": str(lead.id), "name": lead.name, "stage": lead.stage}
