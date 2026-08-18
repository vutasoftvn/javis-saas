from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.business.finance.auth import require_finance_access
from app.business.finance.models import AccountingPeriod, FinancialTransaction, FinanceException
from app.business.finance.domain.exception_engine import detect_exceptions

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
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit_log(db, "user", member.user_id, "finance.transaction.created", "financial_transaction", row.id, {"workspace_id": str(workspace_id)})

    # Detect exceptions and create blockers
    exceptions = detect_exceptions(data.model_dump(), today=date.today())
    for exc in exceptions:
        fe = FinanceException(
            workspace_id=workspace_id,
            transaction_id=row.id,
            exception_type=exc["type"],
            severity=exc["severity"],
            details={"description": data.description, "amount": str(data.amount)},
            status="OPEN",
        )
        db.add(fe)
        db.commit()
        if exc.get("severity") == "ERROR" or exc.get("type") == "MISSING_DOCUMENT":
            try:
                from app.platform.license.blocker_router import BlockerRouter
                BlockerRouter.create_blocker(
                    db=db,
                    workspace_id=workspace_id,
                    blocker_type="FINANCE_EXCEPTION" if exc.get("severity") == "ERROR" else "MISSING_DOCUMENT",
                    description=f"Finance exception {exc['type']} on transaction '{data.description}': amount {data.amount}",
                    cycle_id=data.cycle_id,
                    assigned_function="FINANCE",
                )
            except Exception:
                pass

    return {"id": str(row.id), "amount": str(row.amount), "direction": row.direction}
