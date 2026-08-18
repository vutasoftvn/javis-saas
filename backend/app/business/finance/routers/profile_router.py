from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.business.finance.auth import require_finance_access
from app.business.finance.domain.accounting_profile_service import activate_profile
from app.business.finance.models import AccountingProfile

router = APIRouter()


class ProfileCreate(BaseModel):
    mode: str = "TT58_MODE_1"


@router.get("")
def get_profile(workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    profile = db.query(AccountingProfile).filter(AccountingProfile.workspace_id == workspace_id).first()
    return {"profile": None if profile is None else {"id": str(profile.id), "mode": profile.mode, "status": profile.status, "confirmed_by": str(profile.confirmed_by) if profile.confirmed_by else None}}


@router.post("", status_code=201)
def create_profile(data: ProfileCreate, workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    existing = db.query(AccountingProfile).filter(AccountingProfile.workspace_id == workspace_id).first()
    if existing:
        existing.mode = data.mode
        existing.status = "ACTIVE"
        db.commit()
        db.refresh(existing)
        return {"id": str(existing.id), "mode": existing.mode, "status": existing.status}
    profile = AccountingProfile(workspace_id=workspace_id, mode=data.mode, status="ACTIVE")
    db.add(profile); db.commit(); db.refresh(profile)
    return {"id": str(profile.id), "mode": profile.mode, "status": profile.status}


@router.put("")
def update_profile(data: ProfileCreate, workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    profile = db.query(AccountingProfile).filter(AccountingProfile.workspace_id == workspace_id).first()
    if profile is None:
        profile = AccountingProfile(workspace_id=workspace_id, mode=data.mode, status="ACTIVE")
        db.add(profile)
    else:
        profile.mode = data.mode
        profile.status = "ACTIVE"
    db.commit()
    db.refresh(profile)
    return {"id": str(profile.id), "mode": profile.mode, "status": profile.status}


@router.post("/{profile_id}/activate")
def confirm_profile(profile_id: int, workspace_id: int, member: WorkspaceMember = Depends(require_finance_access), db: Session = Depends(get_db)):
    profile = db.query(AccountingProfile).filter(AccountingProfile.id == profile_id, AccountingProfile.workspace_id == workspace_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Accounting profile not found")
    try:
        activate_profile(profile, member.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    profile.confirmed_at = datetime.utcnow(); db.commit(); db.refresh(profile)
    write_audit_log(db, "user", member.user_id, "finance.profile.activated", "accounting_profile", profile.id, {"workspace_id": str(workspace_id), "mode": profile.mode})
    return {"id": str(profile.id), "status": profile.status}

