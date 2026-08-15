from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class FormDefinition(Base):
    """Schema-driven form configuration associated with landing pages and campaigns."""
    __tablename__ = "form_definitions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    form_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True, index=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_experiments.id"), nullable=True, index=True)

    # Schema definition: fields list, validation rules, required fields
    schema_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Submit actions: e.g. send_confirmation_email, webhook_url, redirect_url, lead_stage
    submit_action: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class FormSubmission(Base):
    """Submissions received from public landing pages / forms."""
    __tablename__ = "form_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    form_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_definitions.id"), nullable=True, index=True)
    form_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    payload_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales_leads.id"), nullable=True, index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="received", nullable=False)  # received, processed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WebEvent(Base):
    """Web event ingestion for landing pages, experiments, and conversion tracking."""
    __tablename__ = "web_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    experiment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_experiments.id"), nullable=True, index=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspace_domains.id"), nullable=True, index=True)

    variant: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "variant_a", "variant_b", "control"
    visitor_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # page_view, cta_clicked, form_submitted, scroll_depth

    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # mobile, desktop, tablet
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    __table_args__ = (
        Index("ix_web_events_ws_exp_type", "workspace_id", "experiment_id", "event_type"),
    )
