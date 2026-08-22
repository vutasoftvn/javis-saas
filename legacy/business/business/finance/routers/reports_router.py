from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.models import WorkspaceMember
from db.session import get_db
from business.finance.auth import require_finance_access
from business.finance.models import FinanceManagementSnapshot

router = APIRouter()


@router.get("")
def list_reports(
    workspace_id: int,
    member: WorkspaceMember = Depends(require_finance_access),
    db: Session = Depends(get_db),
):
    snapshots = (
        db.query(FinanceManagementSnapshot)
        .filter(FinanceManagementSnapshot.workspace_id == workspace_id)
        .order_by(FinanceManagementSnapshot.as_of.desc())
        .limit(24)
        .all()
    )
    return {"reports": [{
        "id": str(snapshot.id),
        "cycle_id": str(snapshot.cycle_id) if snapshot.cycle_id is not None else None,
        "as_of": snapshot.as_of.isoformat(),
        "cash": str(snapshot.cash),
        "burn": str(snapshot.burn),
        "runway_months": str(snapshot.runway_months) if snapshot.runway_months is not None else None,
        "revenue": str(snapshot.revenue),
        "expenses": str(snapshot.expenses),
        "budget_variance": str(snapshot.budget_variance) if snapshot.budget_variance is not None else None,
    } for snapshot in snapshots]}
