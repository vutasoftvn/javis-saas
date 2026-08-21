"""SQLAlchemy models for COSA Hybrid Platform Sync Outbox & Inbox (Phase 2).

Specification:
- COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 16, 17, 31)
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, BigInteger, Boolean, Integer, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class PlatformOutbox(SnowflakeIDMixin, Base):
    """Local transactional outbox for reliable sync from Local to Supabase Central."""
    __tablename__ = "platform_outbox"
    __table_args__ = (
        Index("ix_platform_outbox_status_next_retry", "status", "next_retry_at"),
        Index("ix_platform_outbox_company_status", "company_id", "status"),
        Index("ix_platform_outbox_event_id", "event_id", unique=True),
    )

    event_id: Mapped[str] = mapped_column(String(36), nullable=False) # UUID string
    event_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. project.stage_changed
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False) # project, company, form
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False) # platform UUID
    company_id: Mapped[str] = mapped_column(String(36), nullable=False) # platform UUID
    classification: Mapped[str] = mapped_column(String(50), default="PLATFORM_REQUIRED")
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Delivery tracking
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, processing, sent, acknowledged, failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=10)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PlatformInbox(SnowflakeIDMixin, Base):
    """Local inbox for receiving and processing events from Supabase Central."""
    __tablename__ = "platform_inbox"
    __table_args__ = (
        Index("ix_platform_inbox_status", "status"),
        Index("ix_platform_inbox_event_id", "event_id", unique=True),
    )

    event_id: Mapped[str] = mapped_column(String(36), nullable=False) # UUID string
    event_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. form.submission_received, entitlement.updated
    company_id: Mapped[str] = mapped_column(String(36), nullable=False) # platform UUID
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, processed, failed, ignored
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class LocalEntitlementSnapshot(SnowflakeIDMixin, Base):
    """Local, DB-persisted cache of the current signed entitlement snapshot
    (G2 P0.3 / G3 §9.3). Before this model existed, `EntitlementManager` only
    cached snapshots in a process-memory dict — every restart lost any Pro
    entitlement and silently fell back to Free, even with a still-valid
    license. `is_current` marks the one row in effect per company; refreshing
    must flip the old row's `is_current` to false and insert a new one in the
    same transaction, never update-in-place, so verification history stays
    auditable.
    """
    __tablename__ = "local_entitlement_snapshots"
    __table_args__ = (
        # "Only one is_current=true row per company" is enforced at the
        # application level (EntitlementManager flips the old row to false
        # and inserts the new one in the same transaction) rather than a
        # partial unique DB constraint, to keep this migration simple.
        Index("ix_local_entitlement_snapshots_company_current", "company_id", "is_current"),
    )

    company_id: Mapped[str] = mapped_column(String(36), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)  # full SignedEntitlementSnapshot.model_dump()
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signature_alg: Mapped[str] = mapped_column(String(30), default="HMAC_SHA256")
    key_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="UNVERIFIED")  # UNVERIFIED|VALID|INVALID
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
