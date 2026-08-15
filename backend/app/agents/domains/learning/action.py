from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.modules.learning.service import create_lesson, transition_lesson


class LearningActionCapability:
    """Action capability for recording and promoting organizational lessons."""

    @classmethod
    def record_new_lesson(
        cls,
        db: Session,
        workspace_id: int,
        observation: str,
        function: str = "SALES",
        recommendation: Optional[str] = None,
        confidence: float = 0.85,
    ) -> Dict[str, Any]:
        lesson = create_lesson(
            db=db,
            workspace_id=workspace_id,
            observation=observation,
            function=function,
            recommendation=recommendation or "Review process and update playbook.",
            confidence=confidence,
        )
        return {
            "status": "success",
            "lesson_id": str(lesson.id),
            "function": lesson.function,
            "lesson_status": lesson.status,
            "summary": f"Recorded new organizational lesson (ID: {lesson.id}).",
        }

    @classmethod
    def confirm_lesson(
        cls,
        db: Session,
        lesson_id: int,
    ) -> Dict[str, Any]:
        lesson = transition_lesson(
            db=db,
            lesson_id=lesson_id,
            target_status="CONFIRMED",
        )
        return {
            "status": "success",
            "lesson_id": str(lesson.id),
            "lesson_status": lesson.status,
            "summary": f"Confirmed lesson {lesson.id} as approved company knowledge.",
        }
