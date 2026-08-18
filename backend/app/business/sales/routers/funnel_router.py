from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_OPPORTUNITY_MANAGEMENT_V13_2, FLAG_SALES_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.business.sales.domain.funnel import FunnelMetricsService

router = APIRouter()


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, FLAG_OPPORTUNITY_MANAGEMENT_V13_2, workspace_id)


@router.get("/funnel")
def get_funnel_metrics(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    metrics = FunnelMetricsService.get_funnel_metrics(db, workspace_id)
    return metrics
