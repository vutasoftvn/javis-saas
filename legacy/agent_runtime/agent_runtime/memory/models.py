from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.snowflake import generate_snowflake_id
from db.base_class import Base

# Integration metadata only (mCOSA V12.3 §183, ADR-MEM-002) - the memory
# engine's own internal schema (whatever TencentDB-Agent-Memory uses for its
# L0-L3 tiers) stays entirely outside this migration set.


class AgentMemoryEngine(Base):
    """A configured memory engine for a workspace (spec §183)."""
    __tablename__ = "agent_memory_engines"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50), default="tencentdb_agent_memory")
    deployment: Mapped[str] = mapped_column(String(50), default="local_sidecar")
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentMemoryScope(Base):
    """ACL scope record (spec §159-160):
    PERSONAL|AGENT_PRIVATE|PROJECT|TEAM|DEPARTMENT|ORGANIZATION|SYSTEM, with
    a classification (spec §161):
    PUBLIC_INTERNAL|INTERNAL|CONFIDENTIAL|RESTRICTED|LOCAL_ONLY."""
    __tablename__ = "agent_memory_scopes"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    scope_type: Mapped[str] = mapped_column(String(50))
    subject_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    classification: Mapped[str] = mapped_column(String(50), default="INTERNAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MemoryCandidate(Base):
    """Exact shape per spec §184."""
    __tablename__ = "memory_candidates"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.projects.id"), nullable=True, index=True)
    source_memory_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    candidate_type: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_refs: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    proposed_target: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PROPOSED")  # PROPOSED|APPROVED|REJECTED|PROMOTED|EXPIRED
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class MemoryPromotion(Base):
    """Record of a MemoryCandidate being promoted (spec §166-167) - never
    automatic, always tied to an authorized `promoted_by` user."""
    __tablename__ = "memory_promotions"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.memory_candidates.id"), index=True)
    promoted_target_type: Mapped[str] = mapped_column(String(50))  # knowledge_object|sop|skill|playbook|founder_profile
    promoted_target_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    promoted_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MemoryEvaluation(Base):
    """Memory usefulness metrics (spec §173) - do not optimize token savings
    if recall accuracy degrades."""
    __tablename__ = "memory_evaluations"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(50))  # resume_time|tokens_saved|recall_precision|...
    value: Mapped[float] = mapped_column(Float)
    context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MemorySyncRecord(Base):
    """Selective local-to-cloud sync tracking (spec §162) - never a full
    memory-database sync."""
    __tablename__ = "memory_sync_records"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    sync_class: Mapped[str] = mapped_column(String(50))  # LOCAL_ONLY|METADATA_ONLY|ENCRYPTED_REPLICA|PROMOTED_KNOWLEDGE
    memory_ref: Mapped[str] = mapped_column(String(255))
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MemoryHealthSnapshot(Base):
    """Periodic health snapshots (spec §180) for observability/history,
    distinct from the live `GET /health` check in `health.py`."""
    __tablename__ = "memory_health_snapshots"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    status: Mapped[str] = mapped_column(String(20))  # HEALTHY|DEGRADED|UNAVAILABLE|REBUILDING
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backend: Mapped[str] = mapped_column(String(50))
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentMemoryEntry(Base):
    """5-Layer Memory Entry (COSA Founder OS §b1, §P0.4).
    Layers: L0_SESSION, L1_WORKING, L2_FOUNDER, L3_KNOWLEDGE, L4_LEARNING.
    """
    __tablename__ = "agent_memory_entries"
    __table_args__ = {"schema": "agent_runtime"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    layer: Mapped[str] = mapped_column(String(20), index=True)  # L0_SESSION, L1_WORKING, L2_FOUNDER, L3_KNOWLEDGE, L4_LEARNING
    key: Mapped[str] = mapped_column(String(100), index=True)
    value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)
    # G3 Phase 1E: absorbed from the retired AgentMemoryItem
    # (control_plane/models.py, agent_business_memories) - zero production
    # readers, one writer (LearningWriter), now redirected here instead of a
    # separate table, per G2 §2.5 "reuse instead of adding a parallel model".
    domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provenance_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
