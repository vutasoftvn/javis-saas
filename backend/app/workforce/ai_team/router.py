from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.workforce.ai_team.service import get_function_statuses

router = APIRouter()


@router.get("/status")
def function_status(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return {"functions": get_function_statuses(db, workspace_id)}
