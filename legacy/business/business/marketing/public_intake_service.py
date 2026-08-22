"""Public Intake Gateway Service for COSA Hybrid Architecture (Phase 4).

Ingests public leads, forms, and surveys from company-owned landing pages (Level 1, Level 2, or Level 3)
and routes them into Local CRM and Platform Inbox.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 23, 51, 52)
"""
from datetime import datetime
import hashlib
import logging
from typing import Any, Dict, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from business.marketing.form_models import FormDefinition, FormSubmission
from business.sales.models import SalesLead, Contact
from platform_core.sync.models import PlatformInbox

logger = logging.getLogger(__name__)


class PublicIntakeService:
    """Gateway service for privacy-preserving lead and survey intake."""

    @staticmethod
    def hash_ip(client_ip: Optional[str]) -> Optional[str]:
        """Generates privacy-preserving salted SHA-256 hash of the client IP."""
        if not client_ip:
            return None
        salt = "cosa_intake_salt_2026"
        return hashlib.sha256(f"{client_ip}:{salt}".encode("utf-8")).hexdigest()[:32]

    @classmethod
    def ingest_submission(
        cls,
        db: Session,
        company_id: str,
        form_slug: str,
        payload: Dict[str, Any],
        client_ip: Optional[str] = None,
        source_domain: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Tuple[FormSubmission, PlatformInbox]:
        """Ingests form/survey submission, creates FormSubmission, local SalesLead, and PlatformInbox entry."""
        submission_id = str(uuid.uuid4())
        ip_hash = cls.hash_ip(client_ip)
        now = datetime.utcnow()

        # 1. Look up form definition if exists
        stmt = select(FormDefinition).where(FormDefinition.form_key == form_slug)
        form_def = db.scalars(stmt).first()
        workspace_id = form_def.workspace_id if form_def else 1

        # 2. Extract standard lead fields from payload
        name = payload.get("name") or payload.get("full_name") or payload.get("contact_name")
        email = payload.get("email")
        phone = payload.get("phone") or payload.get("phone_number")
        company = payload.get("company") or payload.get("company_name")

        utm_params = {
            "utm_source": payload.get("utm_source"),
            "utm_medium": payload.get("utm_medium"),
            "utm_campaign": payload.get("utm_campaign"),
            "utm_term": payload.get("utm_term"),
            "utm_content": payload.get("utm_content"),
        }

        # 3. Create Contact and SalesLead in local CRM if contact info is present
        contact = None
        lead = None
        if email or phone or name:
            contact = Contact(
                workspace_id=workspace_id,
                name=name or "Web Visitor",
                email=email,
                phone=phone,
                source=utm_params["utm_source"] or "landing_page",
                created_at=now,
            )
            db.add(contact)
            db.flush()

            lead = SalesLead(
                workspace_id=workspace_id,
                contact_id=contact.id,
                name=name or "Web Lead",
                company=company,
                source=utm_params["utm_source"] or "landing_page",
                utm_source=utm_params["utm_source"],
                utm_medium=utm_params["utm_medium"],
                utm_campaign=utm_params["utm_campaign"],
                utm_term=utm_params["utm_term"],
                utm_content=utm_params["utm_content"],
                stage="NEW",
                created_at=now,
            )
            db.add(lead)
            db.flush()

        # 4. Create FormSubmission
        submission = FormSubmission(
            workspace_id=workspace_id,
            form_definition_id=form_def.id if form_def else None,
            form_key=form_slug,
            payload_jsonb=payload,
            client_ip=ip_hash,
            utm_source=utm_params["utm_source"],
            utm_medium=utm_params["utm_medium"],
            utm_campaign=utm_params["utm_campaign"],
            utm_term=utm_params["utm_term"],
            utm_content=utm_params["utm_content"],
            contact_id=contact.id if contact else None,
            lead_id=lead.id if lead else None,
            status="received",
            created_at=now,
        )
        db.add(submission)
        db.flush()

        # 5. Queue into PlatformInbox for local event processing and attribution
        inbox_entry = PlatformInbox(
            event_id=submission_id,
            event_type="form.submission_received",
            company_id=company_id,
            payload={
                "submission_id": submission_id,
                "form_slug": form_slug,
                "source_domain": source_domain,
                "ip_hash": ip_hash,
                "project_id": project_id,
                "name": name,
                "email": email,
                "phone": phone,
                "company": company,
                "utm": utm_params,
                "submitted_at": now.isoformat(),
            },
            status="pending",
            received_at=now,
        )
        db.add(inbox_entry)
        db.commit()

        logger.info(f"Ingested submission {submission_id} for form '{form_slug}' (Company: {company_id})")
        return submission, inbox_entry
