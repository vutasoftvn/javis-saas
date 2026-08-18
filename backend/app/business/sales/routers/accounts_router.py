from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_ACCOUNT_CONTACT_V13_2, FLAG_SALES_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.business.sales.domain.accounts import AccountService

router = APIRouter()


class AccountCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    size_segment: Optional[str] = None
    country: Optional[str] = None
    source: Optional[str] = None
    lifecycle_status: str = "TARGET"
    tags: Optional[List[str]] = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, FLAG_ACCOUNT_CONTACT_V13_2, workspace_id)


def _serialize_account(acc):
    return {
        "id": str(acc.id),
        "workspace_id": str(acc.workspace_id),
        "name": acc.name,
        "domain": acc.domain,
        "industry": acc.industry,
        "size_segment": acc.size_segment,
        "country": acc.country,
        "source": acc.source,
        "lifecycle_status": acc.lifecycle_status,
        "owner_id": str(acc.owner_id) if acc.owner_id else None,
        "tags": acc.tags,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
        "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
    }


@router.post("/accounts", status_code=201)
def create_account(
    data: AccountCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    acc = AccountService.create_account(
        db=db,
        workspace_id=workspace_id,
        name=data.name,
        domain=data.domain,
        industry=data.industry,
        size_segment=data.size_segment,
        country=data.country,
        source=data.source,
        lifecycle_status=data.lifecycle_status,
        owner_id=member.user_id,
        tags=data.tags,
    )
    return _serialize_account(acc)


@router.get("/accounts")
def list_accounts(
    workspace_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    accounts = AccountService.list_accounts(db, workspace_id, limit=limit, offset=offset)
    return {"accounts": [_serialize_account(a) for a in accounts]}


@router.get("/accounts/{account_id}")
def get_account(
    account_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    acc = AccountService.get_account(db, workspace_id, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return _serialize_account(acc)
