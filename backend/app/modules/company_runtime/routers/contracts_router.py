from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.outcomes.models import Outcome
from app.modules.company_runtime.contract_service import WorkContractService

router = APIRouter()


class ContractSetRequest(BaseModel):
    task_id: Optional[int] = None
    required_artifacts: Optional[Any] = None
    reviewer_id: Optional[int] = None
    review_type: Optional[str] = None
    validation_rules: Optional[Any] = None
    linked_kr_ids: Optional[List[int]] = None


@router.post("/outcomes/{outcome_id}/contract", status_code=status.HTTP_200_OK)
def set_contract(
    outcome_id: int,
    data: ContractSetRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    outcome = (
        db.query(Outcome)
        .filter(Outcome.id == outcome_id, Outcome.workspace_id == workspace_id)
        .first()
    )
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    updated = WorkContractService.set_work_contract(
        db=db,
        outcome=outcome,
        task_id=data.task_id,
        required_artifacts=data.required_artifacts,
        reviewer_id=data.reviewer_id,
        review_type=data.review_type,
        validation_rules=data.validation_rules,
        linked_kr_ids=data.linked_kr_ids,
    )

    return {
        "id": str(updated.id),
        "task_id": str(updated.task_id) if updated.task_id else None,
        "title": updated.title,
        "review_type": updated.review_type,
        "rework_count": updated.rework_count,
        "required_artifacts": updated.required_artifacts,
        "validation_rules": updated.validation_rules,
    }
