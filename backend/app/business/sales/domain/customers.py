from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.business.sales.models import Customer


VALID_HEALTH_STATUSES = {"HEALTHY", "WATCH", "AT_RISK"}
VALID_LIFECYCLE_STATUSES = {"ONBOARDING", "ACTIVE", "WATCH", "AT_RISK", "CHURNED", "EXPANSION"}


class CustomerService:
    @staticmethod
    def get_customer(db: Session, workspace_id: int, customer_id: int) -> Optional[Customer]:
        return (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.workspace_id == workspace_id)
            .first()
        )

    @staticmethod
    def list_customers(db: Session, workspace_id: int, limit: int = 100, offset: int = 0) -> List[Customer]:
        return (
            db.query(Customer)
            .filter(Customer.workspace_id == workspace_id)
            .order_by(Customer.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_customer_health(
        db: Session,
        workspace_id: int,
        customer_id: int,
        health_status: str,
        lifecycle_status: Optional[str] = None,
        last_success_interaction_at: Optional[datetime] = None,
        next_success_action_at: Optional[datetime] = None,
    ) -> Customer:
        customer = CustomerService.get_customer(db, workspace_id, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        status_code = health_status.strip().upper()
        if status_code not in VALID_HEALTH_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid health_status '{health_status}'. Must be one of {VALID_HEALTH_STATUSES}",
            )

        customer.health_status = status_code
        if lifecycle_status:
            life_code = lifecycle_status.strip().upper()
            if life_code not in VALID_LIFECYCLE_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid lifecycle_status '{lifecycle_status}'. Must be one of {VALID_LIFECYCLE_STATUSES}",
                )
            customer.lifecycle_status = life_code

        if last_success_interaction_at:
            customer.last_success_interaction_at = last_success_interaction_at
        if next_success_action_at:
            customer.next_success_action_at = next_success_action_at

        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer
