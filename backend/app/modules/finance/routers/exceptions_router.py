from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.finance.auth import require_finance_access
from app.modules.finance.models import FinanceException

router = APIRouter()


@router.get("")
def list_exceptions(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    rows = db.query(FinanceException).filter(FinanceException.workspace_id == workspace_id).order_by(FinanceException.created_at.desc()).all()
    return {"exceptions": [{"id": str(row.id), "type": row.exception_type, "severity": row.severity, "status": row.status, "details": row.details} for row in rows]}
