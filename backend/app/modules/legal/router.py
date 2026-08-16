from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.legal.models import LegalChecklistItem, LegalObligation
from app.modules.legal import legal_review_service

router = APIRouter()


class LegalItemCreate(BaseModel):
    title: str = Field(..., description="Tiêu đề hạng mục pháp lý")
    description: Optional[str] = Field(None, description="Mô tả chi tiết")


class AnalyzeContractRequest(BaseModel):
    contract_text: str = Field(..., description="Toàn văn hợp đồng cần rà soát")
    contract_type: str = Field("COMMERCIAL_SERVICE", description="Loại hợp đồng: COMMERCIAL_SERVICE, EMPLOYMENT, NDA, PARTNERSHIP")


class RecordL4LessonRequest(BaseModel):
    domain: str = Field("LEGAL", description="Lĩnh vực: LEGAL, SALES, MARKETING, FINANCE, TECH")
    lesson_text: str = Field(..., description="Bài học kinh nghiệm cần ghi nhớ")
    tags: Optional[List[str]] = Field(default_factory=list)


def _guard(workspace_id: int, member: WorkspaceMember) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")


@router.get("/status")
def status(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member)
    return {
        "function": "LEGAL",
        "open_checklist_items": db.query(LegalChecklistItem).filter(LegalChecklistItem.workspace_id == workspace_id, LegalChecklistItem.status == "OPEN").count(),
        "open_obligations": db.query(LegalObligation).filter(LegalObligation.workspace_id == workspace_id, LegalObligation.status == "OPEN").count(),
    }


@router.get("/checklist")
def get_checklist(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member)
    items = legal_review_service.list_legal_checklist(db, workspace_id)
    return {"status": "success", "data": items}


@router.post("/checklist", status_code=201)
def create_checklist_item(data: LegalItemCreate, workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member)
    item = LegalChecklistItem(workspace_id=workspace_id, title=data.title)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": str(item.id), "title": item.title, "status": item.status}


@router.get("/obligations")
def get_obligations(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member)
    items = legal_review_service.list_legal_obligations(db, workspace_id)
    return {"status": "success", "data": items}


@router.post("/obligations", status_code=201)
def create_obligation(data: LegalItemCreate, workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    _guard(workspace_id, member)
    item = LegalObligation(workspace_id=workspace_id, title=data.title, description=data.description)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": str(item.id), "title": item.title, "status": item.status}


@router.post("/reviews/analyze")
def analyze_contract(
    workspace_id: int,
    payload: AnalyzeContractRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member)
    analysis = legal_review_service.analyze_contract_risks(
        contract_text=payload.contract_text,
        contract_type=payload.contract_type,
    )
    return {"status": "success", "data": analysis}


@router.post("/memory/l4-lesson")
def record_lesson(
    workspace_id: int,
    payload: RecordL4LessonRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member)
    res = legal_review_service.record_l4_pattern_lesson(
        db=db,
        workspace_id=workspace_id,
        domain=payload.domain,
        lesson_text=payload.lesson_text,
        tags=payload.tags,
    )
    return {"status": "success", "data": res}
