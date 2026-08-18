from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limiter import public_rate_limiter
from app.business.marketing.form_models import FormDefinition, FormSubmission, WebEvent
from app.platform.core.models import WorkspaceDomain
from app.business.sales.domain.contacts import ContactService
from app.business.sales.domain.leads import LeadService
from app.business.sales.domain.accounts import AccountService
from app.business.sales.models import SalesLead

router = APIRouter(prefix="/public", tags=["Public APIs"])


class FormSubmissionRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # UTM parameters
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None

    # Context
    visitor_id: Optional[str] = None
    session_id: Optional[str] = None
    variant: Optional[str] = None


class WebEventItem(BaseModel):
    workspace_id: Optional[int] = None
    site_key: Optional[str] = None
    experiment_id: Optional[int] = None
    variant: Optional[str] = None
    visitor_id: str
    session_id: Optional[str] = None
    event_type: str = "page_view"
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    referrer: Optional[str] = None
    device: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WebEventsBatchRequest(BaseModel):
    events: List[WebEventItem]


@router.post("/forms/{form_key}/submissions", status_code=status.HTTP_201_CREATED)
async def submit_public_form(
    form_key: str,
    body: FormSubmissionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public endpoint for landing page and embedded form submissions.
    Rate-limited, validates form definition, upserts Contact & Lead into CRM with UTM attribution.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    referrer = request.headers.get("referer", "")

    # 1. Rate limiting check (e.g. max 30 submissions per minute per IP + form_key)
    rate_key = f"form:{client_ip}:{form_key}"
    allowed, _ = public_rate_limiter.is_allowed(rate_key, max_requests=30, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again in a moment.",
        )

    # 2. Resolve FormDefinition
    form_def = (
        db.query(FormDefinition)
        .filter(FormDefinition.form_key == form_key, FormDefinition.is_active == True)
        .first()
    )
    if not form_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found or inactive")

    workspace_id = form_def.workspace_id
    payload = {
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "company": body.company,
        "message": body.message,
        **(body.data or {}),
    }

    # 3. Create initial FormSubmission record
    submission = FormSubmission(
        workspace_id=workspace_id,
        form_definition_id=form_def.id,
        form_key=form_key,
        payload_jsonb=payload,
        client_ip=client_ip,
        user_agent=user_agent,
        referrer=referrer,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
        utm_term=body.utm_term,
        status="received",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    contact_id = None
    lead_id = None

    try:
        contact_name = body.name or (body.email.split("@")[0] if body.email and "@" in body.email else "Web Lead")
        
        # 4. Upsert Contact if email provided
        if body.email:
            contact = ContactService.create_contact(
                db=db,
                workspace_id=workspace_id,
                name=contact_name,
                email=body.email,
                phone=body.phone,
                source="landing_form",
            )
            contact_id = contact.id

        # 5. Handle Account if company provided
        account_id = None
        if body.company or (body.email and "@" in body.email):
            domain = body.email.split("@")[1] if (body.email and "@" in body.email) else None
            acc_name = body.company or (domain.capitalize() if domain else "Web Account")
            account = AccountService.create_account(
                db=db,
                workspace_id=workspace_id,
                name=acc_name,
                domain=domain,
                source="landing_form",
            )
            account_id = account.id

        # 6. Check existing active lead or create new Lead with full UTM attribution
        existing_lead = None
        if contact_id:
            existing_lead = (
                db.query(SalesLead)
                .filter(
                    SalesLead.workspace_id == workspace_id,
                    SalesLead.contact_id == contact_id,
                    SalesLead.stage.notin_(["DISQUALIFIED", "CONVERTED"]),
                )
                .first()
            )

        if existing_lead:
            lead_id = existing_lead.id
        else:
            lead = LeadService.create_lead(
                db=db,
                workspace_id=workspace_id,
                name=contact_name,
                company=body.company,
                account_id=account_id,
                contact_id=contact_id,
                stage="NEW",
                source="landing_form",
                source_campaign_id=form_def.campaign_id,
                source_experiment_id=form_def.experiment_id,
                utm_source=body.utm_source,
                utm_medium=body.utm_medium,
                utm_campaign=body.utm_campaign,
                utm_content=body.utm_content,
                utm_term=body.utm_term,
            )
            lead_id = lead.id

        # 7. Ingest conversion WebEvent if visitor_id is provided
        if body.visitor_id:
            event = WebEvent(
                workspace_id=workspace_id,
                experiment_id=form_def.experiment_id,
                variant=body.variant,
                visitor_id=body.visitor_id,
                session_id=body.session_id,
                event_type="form_submitted",
                utm_source=body.utm_source,
                utm_medium=body.utm_medium,
                utm_campaign=body.utm_campaign,
                utm_content=body.utm_content,
                utm_term=body.utm_term,
                referrer=referrer,
                metadata_jsonb={"form_key": form_key, "lead_id": str(lead_id) if lead_id else None},
            )
            db.add(event)

        # 8. Update submission record
        submission.contact_id = contact_id
        submission.lead_id = lead_id
        submission.status = "processed"
        submission.processed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        submission.status = "failed"
        submission.error_message = str(e)
        db.commit()

    return {
        "success": True,
        "message": "Submission received successfully",
        "submission_id": str(submission.id),
    }


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_public_events(
    body: WebEventsBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public ingestion endpoint for web analytics and experiment conversion events.
    Supports single or batch event payloads.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"events:{client_ip}"
    allowed, _ = public_rate_limiter.is_allowed(rate_key, max_requests=120, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Event rate limit exceeded",
        )

    ingested_count = 0

    for item in body.events:
        workspace_id = item.workspace_id

        # Resolve workspace_id from site_key if not directly passed
        site_id = None
        if not workspace_id and item.site_key:
            domain_rec = (
                db.query(WorkspaceDomain)
                .filter(
                    (WorkspaceDomain.domain == item.site_key) | (WorkspaceDomain.subdomain == item.site_key)
                )
                .first()
            )
            if domain_rec:
                workspace_id = domain_rec.workspace_id
                site_id = domain_rec.id

        if not workspace_id:
            continue

        web_event = WebEvent(
            workspace_id=workspace_id,
            experiment_id=item.experiment_id,
            site_id=site_id,
            variant=item.variant,
            visitor_id=item.visitor_id,
            session_id=item.session_id,
            event_type=item.event_type,
            utm_source=item.utm_source,
            utm_medium=item.utm_medium,
            utm_campaign=item.utm_campaign,
            utm_content=item.utm_content,
            utm_term=item.utm_term,
            referrer=item.referrer,
            device=item.device,
            metadata_jsonb=item.metadata or {},
        )
        db.add(web_event)
        ingested_count += 1

    db.commit()

    return {
        "success": True,
        "ingested_count": ingested_count,
    }


@router.get("/sites/{site_key}/navigation")
async def get_site_navigation(
    site_key: str,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Public navigation manifest endpoint.
    Returns structured navigation tree with cache headers for client-side caching.
    """
    from app.platform.core.models import NavigationGroup, NavigationItem

    # Find NavigationGroup by site_key or domain match
    group = (
        db.query(NavigationGroup)
        .filter(NavigationGroup.site_key == site_key, NavigationGroup.is_active == True)
        .first()
    )

    if not group:
        # Fallback: check if site_key matches a WorkspaceDomain
        domain_rec = (
            db.query(WorkspaceDomain)
            .filter((WorkspaceDomain.domain == site_key) | (WorkspaceDomain.subdomain == site_key))
            .first()
        )
        if domain_rec and domain_rec.navigation_group_id:
            group = db.query(NavigationGroup).filter(NavigationGroup.id == domain_rec.navigation_group_id).first()

    if not group:
        # Return empty default manifest with caching
        response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300"
        return {
            "site_key": site_key,
            "group_name": "Default Navigation",
            "items": [],
        }

    items = (
        db.query(NavigationItem)
        .filter(NavigationItem.group_id == group.id, NavigationItem.is_visible == True)
        .order_by(NavigationItem.sort_order.asc())
        .all()
    )

    nav_tree = [
        {
            "id": str(item.id),
            "title": item.title,
            "path": item.path,
            "icon": item.icon,
            "target": item.target,
            "sort_order": item.sort_order,
            "children": item.children_jsonb or [],
        }
        for item in items
    ]

    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300"
    return {
        "site_key": site_key,
        "group_name": group.name,
        "items": nav_tree,
    }
