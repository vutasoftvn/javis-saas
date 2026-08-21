from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_CUSTOMER_CORE_V13_2, FLAG_SALES_FUNCTION_V13, require_flag
from db.models import WorkspaceMember
from db.session import get_db
from business.sales.models import Customer
from business.sales.domain.customers import CustomerService

router = APIRouter()


class CustomerHealthUpdate(BaseModel):
    health_status: str
    lifecycle_status: Optional[str] = None
    last_success_interaction_at: Optional[datetime] = None
    next_success_action_at: Optional[datetime] = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, FLAG_CUSTOMER_CORE_V13_2, workspace_id)


def _serialize_customer(c: Customer):
    return {
        "id": str(c.id),
        "workspace_id": str(c.workspace_id),
        "account_id": str(c.account_id),
        "acquired_from_opportunity_id": str(c.acquired_from_opportunity_id) if c.acquired_from_opportunity_id else None,
        "lifecycle_status": c.lifecycle_status,
        "activation_status": c.activation_status,
        "owner_id": str(c.owner_id) if c.owner_id else None,
        "first_purchase_at": c.first_purchase_at.isoformat() if c.first_purchase_at else None,
        "renewal_date": c.renewal_date.isoformat() if c.renewal_date else None,
        "health_status": c.health_status,
        "last_success_interaction_at": c.last_success_interaction_at.isoformat() if c.last_success_interaction_at else None,
        "next_success_action_at": c.next_success_action_at.isoformat() if c.next_success_action_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/customers")
def list_customers(
    workspace_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    customers = CustomerService.list_customers(db, workspace_id, limit=limit, offset=offset)
    return {"customers": [_serialize_customer(c) for c in customers]}


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    c = CustomerService.get_customer(db, workspace_id, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _serialize_customer(c)


@router.post("/customers/{customer_id}/health")
def update_customer_health(
    customer_id: int,
    data: CustomerHealthUpdate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    c = CustomerService.update_customer_health(
        db=db,
        workspace_id=workspace_id,
        customer_id=customer_id,
        health_status=data.health_status,
        lifecycle_status=data.lifecycle_status,
        last_success_interaction_at=data.last_success_interaction_at,
        next_success_action_at=data.next_success_action_at,
    )
    return _serialize_customer(c)
