import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.business.sales.domain.activities import ActivityService
from app.business.sales.models import Contact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/webhooks", tags=["Integration Webhooks"])


@router.post("/resend", status_code=status.HTTP_200_OK)
async def handle_resend_webhook(
    request: Request,
    svix_id: Optional[str] = Header(None, alias="svix-id"),
    svix_timestamp: Optional[str] = Header(None, alias="svix-timestamp"),
    svix_signature: Optional[str] = Header(None, alias="svix-signature"),
    db: Session = Depends(get_db),
):
    """
    Webhook receiver for Resend delivery lifecycle events.
    Events: email.sent, email.delivered, email.opened, email.clicked, email.bounced, email.complained.
    Logs updates into the unified SalesActivity timeline.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = body.get("type", "email.unknown")
    data = body.get("data", {})
    to_emails = data.get("to") or []
    recipient = to_emails[0] if isinstance(to_emails, list) and to_emails else str(to_emails)
    subject = data.get("subject", "No subject")
    email_id = data.get("email_id") or data.get("id")

    # Match contact in CRM to find associated workspace
    contact = db.query(Contact).filter(Contact.email == recipient).first() if recipient else None
    workspace_id = contact.workspace_id if contact else None

    if workspace_id:
        activity_type = "EMAIL"
        summary = f"Email [{event_type}] for {recipient}: {subject}"
        outcome = event_type.replace("email.", "").upper()

        try:
            ActivityService.create_activity(
                db=db,
                workspace_id=workspace_id,
                entity_type="contact" if contact else "outreach",
                entity_id=contact.id if contact else 0,
                activity_type=activity_type,
                summary=summary,
                channel="resend",
                direction="INBOUND" if event_type in ["email.opened", "email.clicked"] else "OUTBOUND",
                outcome=outcome,
                artifact_refs={
                    "resend_email_id": email_id,
                    "event_type": event_type,
                    "svix_id": svix_id,
                    "payload": data,
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to record SalesActivity for Resend webhook: {exc}")

    return {"received": True, "event_type": event_type}
