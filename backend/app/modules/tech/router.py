from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_TECH_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.devices.models import DeveloperJob
from app.modules.tasks.models import Task
from app.modules.outcomes.models import Outcome

router = APIRouter()


@router.get("/status")
def get_tech_status(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_TECH_FUNCTION_V13, workspace_id)
    jobs = db.query(DeveloperJob.status, func.count(DeveloperJob.id)).filter(DeveloperJob.workspace_id == workspace_id).group_by(DeveloperJob.status).all()
    return {
        "function": "TECH",
        "jobs": {status: count for status, count in jobs},
        "tasks": db.query(Task).filter(Task.workspace_id == workspace_id, Task.function == "TECH").count(),
        "outcomes": db.query(Outcome).filter(Outcome.workspace_id == workspace_id, Outcome.function == "TECH").count(),
    }
