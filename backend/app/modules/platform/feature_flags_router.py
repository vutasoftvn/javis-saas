from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import effective_feature_flags, list_feature_flags
from app.db.models import WorkspaceMember
from app.db.session import get_db


router = APIRouter()


@router.get("/feature-flags")
def get_feature_flags(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Return the resolved feature policy for the authenticated workspace."""
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
    return {"flags": effective_feature_flags(list_feature_flags(db, workspace_id), workspace_id)}
