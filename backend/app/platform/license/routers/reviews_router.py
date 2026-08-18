from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.platform.license.review_service import ReviewService

router = APIRouter()


class ReviewCreateRequest(BaseModel):
    reviewer_type: str
    result: str  # ACCEPTED, REWORK_REQUIRED, ESCALATED
    reviewer_id: Optional[int] = None
    feedback: Optional[str] = None
    evidence_refs: Optional[Any] = None
    max_rework_count: Optional[int] = 3


@router.post("/outcomes/{outcome_id}/review", status_code=status.HTTP_201_CREATED)
def submit_review(
    outcome_id: int,
    data: ReviewCreateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    reviewer_id = data.reviewer_id or member.user_id

    try:
        review = ReviewService.create_review(
            db=db,
            workspace_id=workspace_id,
            outcome_id=outcome_id,
            reviewer_type=data.reviewer_type,
            result=data.result,
            reviewer_id=reviewer_id,
            feedback=data.feedback,
            evidence_refs=data.evidence_refs,
            max_rework_count=data.max_rework_count or 3,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": str(review.id),
        "outcome_id": str(review.outcome_id),
        "reviewer_type": review.reviewer_type,
        "result": review.result,
        "feedback": review.feedback,
        "created_at": review.created_at.isoformat(),
    }
