from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_LEGAL_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.legal.models import LegalChecklistItem, LegalObligation

router = APIRouter()


class LegalItemCreate(BaseModel):
    title: str
    description: str | None = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_LEGAL_FUNCTION_V13, workspace_id)


@router.get("/status")
def status(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member, db)
    return {
        "function": "LEGAL",
        "open_checklist_items": db.query(LegalChecklistItem).filter(LegalChecklistItem.workspace_id == workspace_id, LegalChecklistItem.status == "OPEN").count(),
        "open_obligations": db.query(LegalObligation).filter(LegalObligation.workspace_id == workspace_id, LegalObligation.status == "OPEN").count(),
    }


@router.post("/checklist", status_code=201)
def create_checklist_item(data: LegalItemCreate, workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member, db)
    item = LegalChecklistItem(workspace_id=workspace_id, title=data.title)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": str(item.id), "title": item.title, "status": item.status}


@router.post("/obligations", status_code=201)
def create_obligation(data: LegalItemCreate, workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member, db)
    item = LegalObligation(workspace_id=workspace_id, title=data.title, description=data.description)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": str(item.id), "title": item.title, "status": item.status}
