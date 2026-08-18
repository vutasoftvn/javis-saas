from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import (
    WorkspaceMember,
    StrategicDecision,
    PromptTemplate,
)
from app.founder_os.strategy.schemas.analysis_schemas import (
    PromptTemplateUpdate,
)

router = APIRouter()


def _serialize_decision(item: StrategicDecision) -> dict:
    return {
        "id": str(item.id),
        "decision": item.decision,
        "status": item.status,
        "tows_option_id": str(item.tows_option_id) if item.tows_option_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.post("/decisions")
def create_decision(
    workspace_id: int,
    data: dict,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    decision_text = data.get("decision")
    tows_option_id = data.get("tows_option_id")
    if not decision_text:
        raise HTTPException(status_code=400, detail="decision text is required")
    item = StrategicDecision(
        workspace_id=workspace_id,
        decision=decision_text,
        tows_option_id=int(tows_option_id) if tows_option_id else None,
        status="active"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_decision(item)


@router.get("/decisions")
def list_decisions(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    items = db.query(StrategicDecision).filter(StrategicDecision.workspace_id == workspace_id).all()
    return {"decisions": [_serialize_decision(i) for i in items]}
