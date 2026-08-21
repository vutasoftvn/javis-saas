from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.audit import write_audit_log
from db.models import WorkspaceMember
from db.session import get_db
from business.finance.auth import require_finance_access
from business.finance.domain.period_service import transition_period
from business.finance.models import AccountingPeriod

router = APIRouter()


class PeriodCreate(BaseModel):
    start_date: date
    end_date: date


class PeriodTransition(BaseModel):
    status: str
    authorize_locked_reopen: bool = False


@router.get("")
def list_periods(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    periods = db.query(AccountingPeriod).filter(AccountingPeriod.workspace_id == workspace_id).order_by(AccountingPeriod.start_date.desc()).all()
    return {"periods": [{"id": str(p.id), "start_date": p.start_date.isoformat(), "end_date": p.end_date.isoformat(), "status": p.status} for p in periods]}


@router.post("", status_code=201)
def create_period(data: PeriodCreate, workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    if data.end_date < data.start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    period = AccountingPeriod(workspace_id=workspace_id, **data.model_dump())
    db.add(period); db.commit(); db.refresh(period)
    return {"id": str(period.id), "status": period.status}


@router.post("/{period_id}/status")
def change_period(period_id: int, data: PeriodTransition, workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    period = db.query(AccountingPeriod).filter(AccountingPeriod.id == period_id, AccountingPeriod.workspace_id == workspace_id).first()
    if period is None:
        raise HTTPException(status_code=404, detail="Accounting period not found")
    try:
        transition_period(period, data.status, can_reopen_locked=data.authorize_locked_reopen and member.role == "admin")
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if period.status in {"CLOSED", "LOCKED"}:
        period.closed_by = member.user_id; period.closed_at = datetime.utcnow()
    db.commit(); db.refresh(period)
    write_audit_log(db, "user", member.user_id, "finance.period.status_changed", "accounting_period", period.id, {"workspace_id": str(workspace_id), "status": period.status})
    return {"id": str(period.id), "status": period.status}
