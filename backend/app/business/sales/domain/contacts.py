from typing import List, Optional
from sqlalchemy.orm import Session
from app.business.sales.models import Contact


class ContactService:
    @staticmethod
    def create_contact(
        db: Session,
        workspace_id: int,
        name: str,
        email: Optional[str] = None,
        account_id: Optional[int] = None,
        title: Optional[str] = None,
        phone: Optional[str] = None,
        source: Optional[str] = None,
        consent_status: Optional[str] = None,
        do_not_contact: bool = False,
        owner_id: Optional[int] = None,
    ) -> Contact:
        if email:
            email = email.strip().lower()
            existing = (
                db.query(Contact)
                .filter(Contact.workspace_id == workspace_id, Contact.email == email)
                .first()
            )
            if existing:
                return existing

        contact = Contact(
            workspace_id=workspace_id,
            account_id=account_id,
            name=name,
            title=title,
            phone=phone,
            email=email,
            source=source,
            consent_status=consent_status,
            do_not_contact=do_not_contact,
            owner_id=owner_id,
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def get_contact(db: Session, workspace_id: int, contact_id: int) -> Optional[Contact]:
        return (
            db.query(Contact)
            .filter(Contact.id == contact_id, Contact.workspace_id == workspace_id)
            .first()
        )

    @staticmethod
    def list_contacts(db: Session, workspace_id: int, account_id: Optional[int] = None, limit: int = 100, offset: int = 0) -> List[Contact]:
        query = db.query(Contact).filter(Contact.workspace_id == workspace_id)
        if account_id:
            query = query.filter(Contact.account_id == account_id)
        return query.order_by(Contact.created_at.desc()).offset(offset).limit(limit).all()
