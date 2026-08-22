from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_ACCOUNT_CONTACT_V13_2, FLAG_SALES_FUNCTION_V13, require_flag
from db.models import WorkspaceMember
from db.session import get_db
from business.sales.domain.contacts import ContactService

router = APIRouter()


class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    account_id: Optional[int] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    consent_status: Optional[str] = None
    do_not_contact: bool = False


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, FLAG_ACCOUNT_CONTACT_V13_2, workspace_id)


def _serialize_contact(c):
    return {
        "id": str(c.id),
        "workspace_id": str(c.workspace_id),
        "account_id": str(c.account_id) if c.account_id else None,
        "name": c.name,
        "title": c.title,
        "phone": c.phone,
        "email": c.email,
        "source": c.source,
        "consent_status": c.consent_status,
        "do_not_contact": c.do_not_contact,
        "owner_id": str(c.owner_id) if c.owner_id else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.post("/contacts", status_code=201)
def create_contact(
    data: ContactCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    contact = ContactService.create_contact(
        db=db,
        workspace_id=workspace_id,
        name=data.name,
        email=data.email,
        account_id=data.account_id,
        title=data.title,
        phone=data.phone,
        source=data.source,
        consent_status=data.consent_status,
        do_not_contact=data.do_not_contact,
        owner_id=member.user_id,
    )
    return _serialize_contact(contact)


@router.get("/contacts")
def list_contacts(
    workspace_id: int,
    account_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    contacts = ContactService.list_contacts(db, workspace_id, account_id=account_id, limit=limit, offset=offset)
    return {"contacts": [_serialize_contact(c) for c in contacts]}


@router.get("/contacts/{contact_id}")
def get_contact(
    contact_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    contact = ContactService.get_contact(db, workspace_id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _serialize_contact(contact)
