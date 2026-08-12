from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_LEARNING_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.learning.models import Lesson
from app.modules.learning.service import create_lesson, list_lessons, transition_lesson


router = APIRouter()


class LessonCreate(BaseModel):
    observation: str = Field(min_length=1)
    cycle_id: Optional[int] = None
    week_no: Optional[int] = Field(default=None, ge=1, le=13)
    function: Optional[str] = None
    project_id: Optional[int] = None
    evidence_refs: Optional[dict] = None
    interpretation: Optional[str] = None
    recommendation: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


class LessonTransition(BaseModel):
    status: str


def _authorize(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_LEARNING_V13, workspace_id)


def _serialize(lesson: Lesson) -> dict:
    return {
        "id": str(lesson.id),
        "workspace_id": str(lesson.workspace_id),
        "cycle_id": str(lesson.cycle_id) if lesson.cycle_id else None,
        "week_no": lesson.week_no,
        "function": lesson.function,
        "project_id": str(lesson.project_id) if lesson.project_id else None,
        "observation": lesson.observation,
        "evidence_refs": lesson.evidence_refs,
        "interpretation": lesson.interpretation,
        "recommendation": lesson.recommendation,
        "confidence": lesson.confidence,
        "status": lesson.status,
        "created_by": str(lesson.created_by) if lesson.created_by else None,
        "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
    }


@router.get("")
def get_lessons(
    workspace_id: int,
    cycle_id: Optional[int] = None,
    week_no: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _authorize(workspace_id, member, db)
    return {"lessons": [_serialize(item) for item in list_lessons(db, workspace_id=workspace_id, cycle_id=cycle_id, week_no=week_no)]}


@router.post("", status_code=201)
def post_lesson(
    data: LessonCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _authorize(workspace_id, member, db)
    return _serialize(create_lesson(db, workspace_id=workspace_id, created_by=member.user_id, **data.model_dump()))


@router.post("/{lesson_id}/status")
def change_lesson_status(
    lesson_id: int,
    data: LessonTransition,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _authorize(workspace_id, member, db)
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.workspace_id == workspace_id).first()
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    try:
        return _serialize(transition_lesson(db, lesson, data.status))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
