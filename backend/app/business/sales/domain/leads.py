from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.business.sales.models import Account, Contact, SalesLead, SalesOpportunity
from app.business.sales.domain.accounts import AccountService
from app.business.sales.domain.contacts import ContactService
from app.business.sales.domain.qualification import QualificationService
from app.business.sales.domain.activities import ActivityService
from app.platform.license.models import Handoff
from app.platform.license.handoff_service import HandoffService


VALID_LEAD_STAGES = {"NEW", "RESEARCHING", "QUALIFYING", "QUALIFIED", "NURTURING", "DISQUALIFIED", "CONVERTED"}


class LeadService:
    @staticmethod
    def create_lead(
        db: Session,
        workspace_id: int,
        name: str,
        company: Optional[str] = None,
        account_id: Optional[int] = None,
        contact_id: Optional[int] = None,
        key_result_id: Optional[int] = None,
        stage: str = "NEW",
        value: Optional[float] = None,
        source: Optional[str] = None,
        source_campaign_id: Optional[int] = None,
        source_experiment_id: Optional[int] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
        owner_id: Optional[int] = None,
    ) -> SalesLead:
        if stage not in VALID_LEAD_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid lead stage '{stage}'. Must be one of {VALID_LEAD_STAGES}")

        lead = SalesLead(
            workspace_id=workspace_id,
            name=name,
            company=company,
            account_id=account_id,
            contact_id=contact_id,
            key_result_id=key_result_id,
            stage=stage,
            value=value,
            source=source,
            source_campaign_id=source_campaign_id,
            source_experiment_id=source_experiment_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            owner_id=owner_id,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        ActivityService.create_activity(
            db=db,
            workspace_id=workspace_id,
            entity_type="lead",
            entity_id=lead.id,
            activity_type="STATUS_CHANGE",
            summary=f"Lead created with stage {stage}",
            actor_id=owner_id,
        )
        return lead

    @staticmethod
    def qualify_lead(
        db: Session,
        workspace_id: int,
        lead_id: int,
        fit: Optional[str] = None,
        need: Optional[str] = None,
        urgency: Optional[str] = None,
        authority: Optional[str] = None,
        ability_to_pay: Optional[str] = None,
        fit_score: Optional[float] = None,
        intent_score: Optional[float] = None,
        engagement_score: Optional[float] = None,
        actor_id: Optional[int] = None,
    ) -> SalesLead:
        lead = db.query(SalesLead).filter(SalesLead.id == lead_id, SalesLead.workspace_id == workspace_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        status, reason = QualificationService.qualify(
            fit=fit, need=need, urgency=urgency, authority=authority, ability_to_pay=ability_to_pay
        )

        old_status = lead.qualification_status or "UNQUALIFIED"
        lead.qualification_status = status
        lead.disqualification_reason = reason
        if fit_score is not None:
            lead.fit_score = fit_score
        if intent_score is not None:
            lead.intent_score = intent_score
        if engagement_score is not None:
            lead.engagement_score = engagement_score

        if status == "QUALIFIED":
            lead.stage = "QUALIFIED"
        elif status == "DISQUALIFIED":
            lead.stage = "DISQUALIFIED"
        else:
            lead.stage = "QUALIFYING"

        db.add(lead)
        db.commit()
        db.refresh(lead)

        ActivityService.record_status_change(
            db=db,
            workspace_id=workspace_id,
            entity_type="lead",
            entity_id=lead.id,
            old_status=old_status,
            new_status=status,
            reason=reason,
            actor_id=actor_id,
        )
        return lead

    @staticmethod
    def convert_lead(
        db: Session,
        workspace_id: int,
        lead_id: int,
        product: Optional[str] = None,
        estimated_value: Optional[float] = None,
        expected_close_date: Optional[datetime] = None,
        owner_id: Optional[int] = None,
    ) -> SalesOpportunity:
        lead = db.query(SalesLead).filter(SalesLead.id == lead_id, SalesLead.workspace_id == workspace_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        if lead.stage == "CONVERTED":
            raise HTTPException(status_code=400, detail="Lead has already been converted")

        # Ensure account exists or create one
        account_id = lead.account_id
        if not account_id:
            acc_name = lead.company or lead.name
            account = AccountService.create_account(
                db=db, workspace_id=workspace_id, name=acc_name, source=lead.source, owner_id=owner_id or lead.owner_id
            )
            account_id = account.id
            lead.account_id = account_id

        # Create Opportunity
        opp = SalesOpportunity(
            workspace_id=workspace_id,
            account_id=account_id,
            primary_contact_id=lead.contact_id,
            owner_id=owner_id or lead.owner_id,
            source_lead_id=lead.id,
            product=product,
            stage="DISCOVERY",
            estimated_value=estimated_value if estimated_value is not None else lead.value,
            expected_close_date=expected_close_date,
        )
        db.add(opp)

        old_stage = lead.stage
        lead.stage = "CONVERTED"
        db.add(lead)

        db.commit()
        db.refresh(opp)
        db.refresh(lead)

        ActivityService.record_status_change(
            db=db,
            workspace_id=workspace_id,
            entity_type="lead",
            entity_id=lead.id,
            old_status=old_stage,
            new_status="CONVERTED",
            reason=f"Converted to Opportunity {opp.id}",
            actor_id=owner_id,
        )
        ActivityService.create_activity(
            db=db,
            workspace_id=workspace_id,
            entity_type="opportunity",
            entity_id=opp.id,
            activity_type="STATUS_CHANGE",
            summary=f"Opportunity created from converted Lead {lead.id}",
            actor_id=owner_id,
        )
        return opp

    @staticmethod
    def intake_from_handoff(db: Session, workspace_id: int, handoff_id: int) -> Dict[str, Any]:
        handoff = db.query(Handoff).filter(Handoff.id == handoff_id, Handoff.workspace_id == workspace_id).first()
        if not handoff:
            raise HTTPException(status_code=404, detail="Handoff not found")

        refs = handoff.artifact_refs or []
        if isinstance(refs, dict):
            refs = [refs]

        created_leads = []
        deduped_leads = []

        for item in refs:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("contact_name") or "Marketing Lead"
            email = item.get("email")
            company = item.get("company")
            source_campaign_id = item.get("source_campaign_id")

            # 1. Contact
            contact = None
            if email:
                contact = ContactService.create_contact(
                    db=db, workspace_id=workspace_id, name=name, email=email, source="marketing_handoff"
                )

            # 2. Account
            account = None
            if company or (email and "@" in email):
                domain = email.split("@")[1] if (email and "@" in email) else None
                acc_name = company or (domain.capitalize() if domain else "Unknown Account")
                account = AccountService.create_account(
                    db=db, workspace_id=workspace_id, name=acc_name, domain=domain, source="marketing_handoff"
                )

            # Link contact to account if not set
            if contact and account and not contact.account_id:
                contact.account_id = account.id
                db.add(contact)
                db.commit()

            # 3. Check Lead deduplication by contact_id
            existing_lead = None
            if contact:
                existing_lead = (
                    db.query(SalesLead)
                    .filter(
                        SalesLead.workspace_id == workspace_id,
                        SalesLead.contact_id == contact.id,
                        SalesLead.stage.notin_(["DISQUALIFIED", "CONVERTED"]),
                    )
                    .first()
                )

            if existing_lead:
                deduped_leads.append(str(existing_lead.id))
            else:
                lead = LeadService.create_lead(
                    db=db,
                    workspace_id=workspace_id,
                    name=name,
                    company=company or (account.name if account else None),
                    account_id=account.id if account else None,
                    contact_id=contact.id if contact else None,
                    stage="NEW",
                    source="marketing_handoff",
                    source_campaign_id=source_campaign_id,
                )
                created_leads.append(str(lead.id))

        # Accept handoff
        HandoffService.accept_handoff(db=db, workspace_id=workspace_id, handoff_id=handoff_id)
        return {"created_leads": created_leads, "deduped_leads": deduped_leads}
