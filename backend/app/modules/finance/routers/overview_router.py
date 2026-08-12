from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.finance.auth import require_finance_access
from app.modules.finance.models import FinanceManagementSnapshot

router = APIRouter()


@router.get("")
def overview(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    snapshot = db.query(FinanceManagementSnapshot).filter(FinanceManagementSnapshot.workspace_id == workspace_id).order_by(FinanceManagementSnapshot.as_of.desc()).first()
    return {"snapshot": None if snapshot is None else {"id": str(snapshot.id), "as_of": snapshot.as_of.isoformat(), "cash": str(snapshot.cash), "burn": str(snapshot.burn), "runway_months": str(snapshot.runway_months) if snapshot.runway_months is not None else None, "revenue": str(snapshot.revenue), "expenses": str(snapshot.expenses)}}
