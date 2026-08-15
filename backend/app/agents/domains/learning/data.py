from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.modules.learning.models import Lesson


class LearningDataCapability:
    """Capability for querying organizational lessons and improvement records."""

    @classmethod
    def read_lessons(
        cls,
        db: Session,
        workspace_id: int,
        function: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = db.query(Lesson).filter(Lesson.workspace_id == workspace_id)
        if function:
            query = query.filter(Lesson.function == function.upper())
        if status:
            query = query.filter(Lesson.status == status.upper())

        lessons = query.all()
        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "count": len(lessons),
            "lessons": [
                {
                    "id": str(l.id),
                    "function": l.function,
                    "observation": l.observation,
                    "recommendation": l.recommendation,
                    "status": l.status,
                    "confidence": l.confidence,
                }
                for l in lessons
            ],
            "summary": f"Found {len(lessons)} organizational lesson(s).",
        }
