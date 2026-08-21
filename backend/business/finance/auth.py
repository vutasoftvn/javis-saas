from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_FINANCE_FUNCTION_V13, require_flag
from db.models import WorkspaceMember
from db.session import get_db


def require_finance_access(workspace_id: int, member: WorkspaceMember = Depends(get_current_workspace_member), db: Session = Depends(get_db)) -> WorkspaceMember:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_FINANCE_FUNCTION_V13, workspace_id)
    return member
