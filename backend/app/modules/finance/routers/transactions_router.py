from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.finance.auth import require_finance_access
from app.modules.finance.models import AccountingPeriod, FinancialTransaction

router = APIRouter()


class TransactionCreate(BaseModel):
    transaction_date: date
    description: str
    amount: Decimal = Field(gt=0)
    direction: str
    category: str | None = None
    document_id: int | None = None
    project_id: int | None = None
    cycle_id: int | None = None
    work_item_id: int | None = None


@router.get("")
def list_transactions(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    rows = db.query(FinancialTransaction).filter(FinancialTransaction.workspace_id == workspace_id).order_by(FinancialTransaction.transaction_date.desc()).all()
    return {"transactions": [{"id": str(row.id), "date": row.transaction_date.isoformat(), "description": row.description, "amount": str(row.amount), "direction": row.direction, "category": row.category} for row in rows]}


@router.post("", status_code=201)
def create_transaction(data: TransactionCreate, workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    if data.direction not in {"IN", "OUT"}:
        raise HTTPException(status_code=422, detail="direction must be IN or OUT")
    locked = db.query(AccountingPeriod).filter(AccountingPeriod.workspace_id == workspace_id, AccountingPeriod.start_date <= data.transaction_date, AccountingPeriod.end_date >= data.transaction_date, AccountingPeriod.status == "LOCKED").first()
    if locked:
        raise HTTPException(status_code=409, detail="Accounting period is LOCKED")
    row = FinancialTransaction(workspace_id=workspace_id, **data.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    write_audit_log(db, "user", member.user_id, "finance.transaction.created", "financial_transaction", row.id, {"workspace_id": str(workspace_id)})
    return {"id": str(row.id), "amount": str(row.amount), "direction": row.direction}
