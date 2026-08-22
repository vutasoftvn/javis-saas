from sqlalchemy.orm import Session

from business.learning.models import Lesson
from founder_os.outcomes.models import Artifact, Outcome
from founder_os.tasks.models import Task


FUNCTIONS = ("LEGAL", "MARKETING", "SALES", "TECH", "FINANCE")


def get_function_statuses(db: Session, workspace_id: int) -> list[dict]:
    statuses = []
    for function in FUNCTIONS:
        task_count = db.query(Task).filter(Task.workspace_id == workspace_id, Task.function == function).count()
        outcome_count = db.query(Outcome).filter(Outcome.workspace_id == workspace_id, Outcome.function == function).count()
        current = db.query(Task).filter(Task.workspace_id == workspace_id, Task.function == function, Task.status.in_(("todo", "in_progress", "waiting_approval", "blocked"))).order_by(Task.updated_at.desc()).first()
        latest_outcome = db.query(Outcome).filter(Outcome.workspace_id == workspace_id, Outcome.function == function).order_by(Outcome.updated_at.desc()).first()
        latest_artifact = None
        if latest_outcome is not None:
            latest_artifact = db.query(Artifact).filter(Artifact.workspace_id == workspace_id, Artifact.outcome_id == latest_outcome.id).order_by(Artifact.created_at.desc()).first()
        latest_lesson = db.query(Lesson).filter(Lesson.workspace_id == workspace_id, Lesson.function == function).order_by(Lesson.created_at.desc()).first()
        statuses.append({
            "function": function,
            "status": "NEEDS_FOUNDER" if current is not None and current.status in {"waiting_approval", "blocked"} else ("WORKING" if current is not None else "IDLE"),
            "current_work": current.title if current is not None else None,
            "latest_result": latest_artifact.title if latest_artifact is not None else (latest_outcome.title if latest_outcome is not None else None),
            "needs_founder": current is not None and current.status in {"waiting_approval", "blocked"},
            "key_metric": {"tasks": task_count, "outcomes": outcome_count},
            "task_count": task_count,
            "outcome_count": outcome_count,
            "latest_lesson": latest_lesson.observation if latest_lesson is not None else None,
        })
    return statuses
