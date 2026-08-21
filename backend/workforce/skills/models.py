"""Global Skill Registry Models for COSA Operating System (Spec §61, §62, §P5)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin
from core.snowflake import generate_snowflake_id


class SkillRegistryItem(SnowflakeIDMixin, Base):
    """Global Skill Registry Item (Spec §61 / G3 Phase 1C).

    Lifecycle: candidate -> evaluation -> pending_approval -> (active | experimental)
    -> deprecated -> archived. `blocked` is a separate emergency-disable state reachable
    from any status (e.g. a security review fails on an already-active skill).
    - active: normal production use.
    - experimental: promoted but explicitly flagged unstable - visible/usable, not
      the default recommendation.
    - deprecated: discouraged but may still run (soft retirement).
    - archived: retired, excluded from normal listing/use, kept for history.
    - blocked: forcibly disabled regardless of prior status; requires a reason.
    """
    __tablename__ = "global_skill_registry"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.workspaces.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # sales, marketing, finance, legal, tech, general
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")

    # Lifecycle Status
    status: Mapped[str] = mapped_column(String(30), default="candidate", index=True)  # candidate, evaluation, pending_approval, active, experimental, deprecated, archived, blocked

    # G3 Phase 1C: platform-shipped (built-in SKILL.md, seeded automatically, no human
    # clicked approve) vs. workspace-authored (candidate/trajectory/upload flows, always
    # requires SkillLifecycleService.promote_skill's human-approval invariant). Immutable
    # via update_skill() - a founder who wants to customize a system skill registers a new
    # workspace-authored one rather than editing the platform original in place.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Manifest & Capabilities
    description: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[List[str]] = mapped_column(JSONB, default=list)
    tool_permissions: Mapped[List[str]] = mapped_column(JSONB, default=list)
    required_context: Mapped[List[str]] = mapped_column(JSONB, default=list)
    manifest_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Performance Metrics
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_feedback: Mapped[int] = mapped_column(Integer, default=0)
    negative_feedback: Mapped[int] = mapped_column(Integer, default=0)

    # Auditing & Governance
    created_by_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("core.users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SkillTrajectoryCandidate(SnowflakeIDMixin, Base):
    """Learning candidate extracted from completed mission trajectory (Spec §62)."""
    __tablename__ = "skill_trajectory_candidates"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.workspaces.id"), index=True, nullable=False)
    mission_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    
    proposed_name: Mapped[str] = mapped_column(String(100), nullable=False)
    extracted_sop: Mapped[str] = mapped_column(Text, nullable=False)
    tools_used: Mapped[List[str]] = mapped_column(JSONB, default=list)

    # Safety checks
    pii_scan_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    secret_scan_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Evaluation
    eval_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="extracted")  # extracted, scanned, evaluated, converted, rejected

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
