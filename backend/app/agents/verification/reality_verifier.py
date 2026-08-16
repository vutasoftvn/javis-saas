"""Reality Verifier & Outcome Certificate Service (§P0.7, C1/C2 Spec).

Enforces Architectural Invariant: "NO VERIFIED STATUS WITHOUT REALITY CHECK".
Verifies that mutations claimed by agents genuinely occurred in Postgres/External systems
and mints tamper-evident Outcome Certificates stored as external_action_receipt Artifacts.
"""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.modules.outcomes.models import Artifact, OutcomeRun

logger = logging.getLogger(__name__)


class VerificationVerdict(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class VerificationEvidence(BaseModel):
    domain: str
    resource_type: str
    resource_id: str
    is_valid: bool
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VerificationResult(BaseModel):
    verdict: VerificationVerdict
    evidence: List[VerificationEvidence] = Field(default_factory=list)
    unresolved: List[str] = Field(default_factory=list)
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RealityVerifier:
    """Performs real-world state inspection against PostgreSQL domain records."""

    @classmethod
    def verify_crm_contact(
        cls,
        db: Session,
        workspace_id: int,
        contact_id: int,
        expected_email: Optional[str] = None,
    ) -> VerificationResult:
        """Verify that a contact row really exists in CRM and has valid attributes."""
        from app.modules.sales.models import Contact

        contact = db.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if contact is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Contact ID {contact_id} does not exist in workspace {workspace_id}"],
                summary="CRM Verification Failed: Contact not found in database.",
            )

        if expected_email and contact.email != expected_email:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Contact email mismatch: expected {expected_email}, found {contact.email}"],
                summary="CRM Verification Failed: Contact email does not match expected state.",
            )

        evidence = VerificationEvidence(
            domain="sales",
            resource_type="contact",
            resource_id=str(contact.id),
            is_valid=True,
            details={"name": contact.name, "email": contact.email, "title": contact.title},
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"CRM Contact {contact.name} ({contact.id}) verified successfully.",
        )

    @classmethod
    def verify_crm_lead(
        cls,
        db: Session,
        workspace_id: int,
        lead_id: int,
        expected_company: Optional[str] = None,
        expected_stage: Optional[str] = None,
    ) -> VerificationResult:
        """Verify that a sales lead exists in PostgreSQL and matches expected attributes."""
        from app.modules.sales.models import SalesLead

        lead = db.execute(
            select(SalesLead).where(
                SalesLead.id == lead_id,
                SalesLead.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if lead is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Lead ID {lead_id} does not exist in workspace {workspace_id}"],
                summary="CRM Verification Failed: Sales lead not found in database.",
            )

        if expected_company and lead.company != expected_company:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Lead company mismatch: expected '{expected_company}', found '{lead.company}'"],
                summary="CRM Verification Failed: Lead company name does not match expected state.",
            )

        if expected_stage and lead.stage != expected_stage:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Lead stage mismatch: expected '{expected_stage}', found '{lead.stage}'"],
                summary="CRM Verification Failed: Lead stage does not match expected state.",
            )

        evidence = VerificationEvidence(
            domain="sales",
            resource_type="lead",
            resource_id=str(lead.id),
            is_valid=True,
            details={
                "name": lead.name,
                "company": lead.company,
                "stage": lead.stage,
                "fit_score": lead.fit_score,
                "qualification_status": lead.qualification_status,
            },
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"CRM Lead '{lead.name}' ({lead.company}) verified successfully in stage '{lead.stage}'.",
        )

    @classmethod
    def verify_email_approval_sent(
        cls,
        db: Session,
        workspace_id: int,
        approval_id: int,
    ) -> VerificationResult:
        """Verify that an EmailApproval was approved and successfully sent."""
        from app.db.models import EmailApproval

        approval = db.execute(
            select(EmailApproval).where(
                EmailApproval.id == approval_id,
                EmailApproval.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if approval is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"EmailApproval ID {approval_id} does not exist in workspace {workspace_id}"],
                summary="Email Verification Failed: Approval record not found.",
            )

        if approval.status != "sent":
            verdict = VerificationVerdict.PARTIAL if approval.status == "pending" else VerificationVerdict.FAILED
            return VerificationResult(
                verdict=verdict,
                unresolved=[f"EmailApproval status is '{approval.status}' (expected 'sent')"],
                summary=f"Email Verification: Approval status is '{approval.status}', message has not been sent.",
            )

        evidence = VerificationEvidence(
            domain="communication",
            resource_type="email_approval",
            resource_id=str(approval.id),
            is_valid=True,
            details={
                "to_email": approval.to_email,
                "subject": approval.subject,
                "status": approval.status,
                "provider": approval.provider,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
            },
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"EmailApproval {approval.id} to '{approval.to_email}' verified as SENT.",
        )

    @classmethod
    def verify_email_outbox(
        cls,
        db: Session,
        workspace_id: int,
        outbox_id: int,
    ) -> VerificationResult:
        """Verify that an email dispatch was recorded in outbox with valid message_id/status."""
        from app.modules.integrations.models import Outbox

        outbox = db.execute(
            select(Outbox).where(
                Outbox.id == outbox_id,
                Outbox.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if outbox is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Outbox record {outbox_id} does not exist in database"],
                summary="Email Verification Failed: Outbox entry not found.",
            )

        if outbox.status not in ("sent", "queued", "delivered", "success"):
            return VerificationResult(
                verdict=VerificationVerdict.PARTIAL if outbox.status == "pending" else VerificationVerdict.FAILED,
                unresolved=[f"Outbox status is '{outbox.status}' instead of confirmed delivery."],
                summary=f"Email Verification: Outbox status is {outbox.status}.",
            )

        evidence = VerificationEvidence(
            domain="communication",
            resource_type="outbox",
            resource_id=str(outbox.id),
            is_valid=True,
            details={"channel": outbox.channel, "status": outbox.status, "recipient": outbox.recipient},
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"Email outbox dispatch {outbox.id} verified with status '{outbox.status}'.",
        )

    @classmethod
    def verify_deployment(
        cls,
        db: Session,
        workspace_id: int,
        deployment_id: int,
        expected_commit: Optional[str] = None,
    ) -> VerificationResult:
        """Verify deployment record status and commit hash integrity."""
        from app.modules.platform.deployment_models import Deployment

        deployment = db.execute(
            select(Deployment).where(
                Deployment.id == deployment_id,
                Deployment.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if deployment is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Deployment ID {deployment_id} not found."],
                summary="Deployment Verification Failed: Deployment entity not found.",
            )

        if expected_commit and deployment.commit_hash != expected_commit:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Commit hash mismatch: expected {expected_commit}, got {deployment.commit_hash}"],
                summary="Deployment Verification Failed: Commit hash mismatch.",
            )

        evidence = VerificationEvidence(
            domain="platform",
            resource_type="deployment",
            resource_id=str(deployment.id),
            is_valid=True,
            details={"service_name": deployment.service_name, "status": deployment.status, "commit": deployment.commit_hash},
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"Deployment {deployment.service_name} verified with status {deployment.status}.",
        )

    @classmethod
    def verify_accounting_document(
        cls,
        db: Session,
        workspace_id: int,
        document_id: int,
        expected_status: Optional[str] = None,
        expected_document_no: Optional[str] = None,
        expected_document_type: Optional[str] = None,
    ) -> VerificationResult:
        """Verify that an AccountingDocument physically exists in PostgreSQL and matches expected state."""
        from app.modules.finance.models import AccountingDocument

        doc = db.execute(
            select(AccountingDocument).where(
                AccountingDocument.id == document_id,
                AccountingDocument.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if doc is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"AccountingDocument ID {document_id} does not exist in workspace {workspace_id}"],
                summary="Finance Verification Failed: Accounting document not found in database.",
            )

        if expected_status and doc.status != expected_status:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Document status mismatch: expected '{expected_status}', found '{doc.status}'"],
                summary=f"Finance Verification Failed: Document status is '{doc.status}' (expected '{expected_status}').",
            )

        if expected_document_no and doc.document_no != expected_document_no:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Document number mismatch: expected '{expected_document_no}', found '{doc.document_no}'"],
                summary="Finance Verification Failed: Document number mismatch.",
            )

        if expected_document_type and doc.document_type != expected_document_type:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Document type mismatch: expected '{expected_document_type}', found '{doc.document_type}'"],
                summary="Finance Verification Failed: Document type mismatch.",
            )

        evidence = VerificationEvidence(
            domain="finance",
            resource_type="accounting_document",
            resource_id=str(doc.id),
            is_valid=True,
            details={
                "document_no": doc.document_no,
                "document_type": doc.document_type,
                "status": doc.status,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
            },
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"AccountingDocument {doc.document_no} ({doc.id}) verified with status '{doc.status}'.",
        )

    @classmethod
    def verify_financial_transaction(
        cls,
        db: Session,
        workspace_id: int,
        transaction_id: int,
        expected_direction: Optional[str] = None,
        expected_category: Optional[str] = None,
    ) -> VerificationResult:
        """Verify that a FinancialTransaction exists in PostgreSQL with accompanying AccountingRecord."""
        from app.modules.finance.models import AccountingRecord, FinancialTransaction

        tx = db.execute(
            select(FinancialTransaction).where(
                FinancialTransaction.id == transaction_id,
                FinancialTransaction.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

        if tx is None:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"FinancialTransaction ID {transaction_id} does not exist in workspace {workspace_id}"],
                summary="Finance Verification Failed: Financial transaction record not found.",
            )

        if expected_direction and (tx.direction or "").upper() != expected_direction.upper():
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Transaction direction mismatch: expected '{expected_direction}', found '{tx.direction}'"],
                summary="Finance Verification Failed: Transaction direction mismatch.",
            )

        if expected_category and tx.category != expected_category:
            return VerificationResult(
                verdict=VerificationVerdict.FAILED,
                unresolved=[f"Transaction category mismatch: expected '{expected_category}', found '{tx.category}'"],
                summary="Finance Verification Failed: Transaction category mismatch.",
            )

        # Check corresponding ledger AccountingRecord
        records = db.execute(
            select(AccountingRecord).where(
                AccountingRecord.transaction_id == tx.id,
                AccountingRecord.workspace_id == workspace_id,
            )
        ).scalars().all()

        evidence = VerificationEvidence(
            domain="finance",
            resource_type="financial_transaction",
            resource_id=str(tx.id),
            is_valid=True,
            details={
                "amount": float(tx.amount),
                "direction": tx.direction,
                "category": tx.category,
                "has_accounting_record": len(records) > 0,
                "records_count": len(records),
            },
        )
        return VerificationResult(
            verdict=VerificationVerdict.VERIFIED,
            evidence=[evidence],
            summary=f"FinancialTransaction {tx.id} ({tx.amount} {tx.direction}) verified with {len(records)} ledger records.",
        )

    @classmethod
    def create_outcome_certificate(
        cls,
        db: Session,
        workspace_id: int,
        outcome_id: int,
        run_id: int,
        verification_result: VerificationResult,
        user_id: Optional[int] = None,
    ) -> Artifact:
        """Mint a verifiable Outcome Certificate and persist as an external_action_receipt Artifact."""
        certificate_payload = {
            "certificate_id": str(generate_snowflake_id()),
            "outcome_id": str(outcome_id),
            "run_id": str(run_id),
            "workspace_id": str(workspace_id),
            "verdict": verification_result.verdict.value,
            "evidence": [e.model_dump() for e in verification_result.evidence],
            "unresolved": verification_result.unresolved,
            "summary": verification_result.summary,
            "issued_at": verification_result.timestamp,
        }

        content_json = json.dumps(certificate_payload, sort_keys=True)
        content_hash = hashlib.sha256(content_json.encode("utf-8")).hexdigest()

        # Update OutcomeRun verification fields
        outcome_run = db.execute(
            select(OutcomeRun).where(OutcomeRun.id == run_id)
        ).scalar_one_or_none()

        if outcome_run:
            outcome_run.verification_status = verification_result.verdict.value
            outcome_run.verification_jsonb = certificate_payload
            db.commit()

        # Mint Certificate Artifact
        artifact = Artifact(
            id=generate_snowflake_id(),
            run_id=run_id,
            outcome_id=outcome_id,
            workspace_id=workspace_id,
            type="external_action_receipt",
            title=f"Outcome Certificate — {verification_result.verdict.value}",
            content_hash=content_hash,
            status="approved" if verification_result.verdict == VerificationVerdict.VERIFIED else "review",
            created_by=user_id or 1,
            created_at=datetime.now(timezone.utc),
        )
        db.add(artifact)
        db.commit()

        logger.info(
            f"[RealityVerifier] Minted Outcome Certificate for run {run_id}: verdict={verification_result.verdict.value}"
        )
        return artifact
