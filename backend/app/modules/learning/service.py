from typing import Optional

from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.modules.learning.models import Lesson


FUNCTIONS = {"LEGAL", "MARKETING", "SALES", "TECH", "FINANCE"}
TRANSITIONS = {
    "DRAFT": {"CONFIRMED", "REJECTED"},
    "CONFIRMED": {"APPLIED", "SUPERSEDED"},
    "APPLIED": {"SUPERSEDED"},
    "REJECTED": set(),
    "SUPERSEDED": set(),
}


def create_lesson(
    db: Session,
    *,
    workspace_id: int,
    observation: str,
    cycle_id: Optional[int] = None,
    week_no: Optional[int] = None,
    function: Optional[str] = None,
    project_id: Optional[int] = None,
    evidence_refs: Optional[dict] = None,
    interpretation: Optional[str] = None,
    recommendation: Optional[str] = None,
    confidence: Optional[float] = None,
    created_by: Optional[int] = None,
) -> Lesson:
    normalized_function = function.upper() if function else None
    if normalized_function and normalized_function not in FUNCTIONS:
        raise ValueError("Unknown company function")
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError("Confidence must be between 0 and 1")
    lesson = Lesson(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        cycle_id=cycle_id,
        week_no=week_no,
        function=normalized_function,
        project_id=project_id,
        observation=observation,
        evidence_refs=evidence_refs,
        interpretation=interpretation,
        recommendation=recommendation,
        confidence=confidence,
        status="DRAFT",
        created_by=created_by,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def transition_lesson(db: Session, lesson: Lesson, target_status: str) -> Lesson:
    target = target_status.upper()
    if target not in TRANSITIONS.get(lesson.status, set()):
        raise ValueError(f"Invalid lesson status transition: {lesson.status} -> {target}")
    lesson.status = target
    db.commit()
    db.refresh(lesson)
    return lesson


def list_lessons(
    db: Session, *, workspace_id: int, cycle_id: Optional[int] = None, week_no: Optional[int] = None
) -> list[Lesson]:
    query = db.query(Lesson).filter(Lesson.workspace_id == workspace_id)
    if cycle_id is not None:
        query = query.filter(Lesson.cycle_id == cycle_id)
    if week_no is not None:
        query = query.filter(Lesson.week_no == week_no)
    return query.order_by(Lesson.created_at.desc()).all()
