from typing import List, Optional
from sqlalchemy.orm import Session
from app.business.sales.models import Account


class AccountService:
    @staticmethod
    def create_account(
        db: Session,
        workspace_id: int,
        name: str,
        domain: Optional[str] = None,
        industry: Optional[str] = None,
        size_segment: Optional[str] = None,
        country: Optional[str] = None,
        source: Optional[str] = None,
        lifecycle_status: str = "TARGET",
        owner_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Account:
        if domain:
            domain = domain.strip().lower()
            existing = (
                db.query(Account)
                .filter(Account.workspace_id == workspace_id, Account.domain == domain)
                .first()
            )
            if existing:
                return existing

        account = Account(
            workspace_id=workspace_id,
            name=name,
            domain=domain,
            industry=industry,
            size_segment=size_segment,
            country=country,
            source=source,
            lifecycle_status=lifecycle_status,
            owner_id=owner_id,
            tags=tags,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def get_account(db: Session, workspace_id: int, account_id: int) -> Optional[Account]:
        return (
            db.query(Account)
            .filter(Account.id == account_id, Account.workspace_id == workspace_id)
            .first()
        )

    @staticmethod
    def list_accounts(db: Session, workspace_id: int, limit: int = 100, offset: int = 0) -> List[Account]:
        return (
            db.query(Account)
            .filter(Account.workspace_id == workspace_id)
            .order_by(Account.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
