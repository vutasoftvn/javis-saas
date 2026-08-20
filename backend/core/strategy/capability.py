from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class CapabilityDefinition(Base):
    """Canonical Capability Registry (G1 §4 / G3 Phase 1B).

    Unifies 3 previously-duplicate `CapabilityDefinition` shapes that turned
    out to serve 3 different concerns rather than being pure duplicates:
    - `workforce/agents/capabilities/registry.py` (deleted) drove REAL
      runtime authorization (CapabilityGateway risk/approval checks) —
      migrated in as rows with `source="runtime_registry"`.
    - `business/packs/schemas.py::CapabilityDefinition` (kept, unchanged,
      as the Pydantic response/DTO shape) is a business-pack content/
      deliverable catalog (artifact type, execution mode, legal context,
      output format) — migrated in as rows with `source="business_pack"`,
      rich pack-specific content kept in `content_jsonb` rather than
      exploded into dedicated columns nothing else queries.
    - This table's own pre-existing rows (seeded by
      `TemplateService._sync_capability_definitions`) keep
      `source="founder_os_seed"`, workspace/brain-scoped as before.

    Platform-global rows (from registry.py / business packs) have
    `workspace_id`/`brain_id` NULL; workspace-specific seeded rows keep
    them set, same as before this migration.
    """
    __tablename__ = "capability_definitions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=True)
    brain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brains.id"), index=True, nullable=True)
    capability_key: Mapped[str] = mapped_column(String(150), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 5 Core Domain Agent ownership (G1 §3.6) — SALES, MARKETING, FINANCE,
    # LEGAL, TECH, or CROSS_DOMAIN when it doesn't map cleanly to one.
    # Reuses the vocabulary already live on FounderDecision.domain rather
    # than inventing a 5th taxonomy.
    domain: Mapped[str] = mapped_column(String(50), default="CROSS_DOMAIN", index=True)
    owner_agent_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, OPTIONAL, EXPERIMENTAL, DEPRECATED, INTERNAL (G1 §4.4)
    # Provenance of the migration, kept for traceability — not itself a
    # runtime decision point (don't branch behavior on `source`).
    source: Mapped[str] = mapped_column(String(30), default="founder_os_seed")
    source_pack_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expected_deliverables_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    evidence_requirements_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Execution modes this capability can be assigned: MANUAL, AI_ASSISTED, AUTONOMOUS.
    supported_execution_modes_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    risk_level: Mapped[str] = mapped_column(String(24), default="LOW")  # LOW, MEDIUM, HIGH, REGULATED
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    professional_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    # Business-pack-origin rich content (execution_mode, artifact_type,
    # required_context, inputs, uses, legal_context, output) — kept as one
    # blob since business/packs/resolver.py reads it as a whole, never
    # queries individual sub-fields.
    content_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Catch-all for source-specific fields not otherwise promoted to a
    # column (e.g. registry.py's permission_level/resource/action).
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkspaceAgent(Base):
    __tablename__ = "workspace_agents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    capability_keys_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
