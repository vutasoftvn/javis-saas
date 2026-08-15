from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="TARGET", nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("uq_accounts_workspace_domain", "workspace_id", "domain", unique=True, postgresql_where=domain.isnot(None)),
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    consent_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("uq_contacts_workspace_email", "workspace_id", "email", unique=True, postgresql_where=email.isnot(None)),
    )


class SalesLead(Base):
    __tablename__ = "sales_leads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    key_result_id: Mapped[Optional[int]] = mapped_column(ForeignKey("key_results.id"), nullable=True, index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stage: Mapped[str] = mapped_column(String(30), default="NEW", nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True)
    source_experiment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_experiments.id"), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fit_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intent_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qualification_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    disqualification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_action_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SalesOpportunity(Base):
    __tablename__ = "sales_opportunities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True, nullable=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    primary_contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    source_lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales_leads.id"), nullable=True)
    product: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stage: Mapped[str] = mapped_column(String(30), default="DISCOVERY", nullable=False)
    estimated_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="VND", nullable=False)
    probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_close_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    pain_points: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    needs: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    objections: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    competitors: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    next_action_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    won_reason: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    lost_reason: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    lost_reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SalesActivity(Base):
    __tablename__ = "sales_activities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # account, contact, lead, opportunity, customer
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)  # RESEARCH, EMAIL, MESSAGE, CALL, MEETING, DEMO, PROPOSAL, FOLLOW_UP, NOTE, STATUS_CHANGE
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    artifact_refs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    acquired_from_opportunity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales_opportunities.id"), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="ONBOARDING", nullable=False)
    activation_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    first_purchase_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    renewal_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    health_status: Mapped[str] = mapped_column(String(20), default="HEALTHY", nullable=False)
    last_success_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_success_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("uq_customers_workspace_account", "workspace_id", "account_id", unique=True),
    )
