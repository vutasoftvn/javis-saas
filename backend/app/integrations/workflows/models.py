from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class TaskWorkflowBinding(Base):
    __tablename__ = "task_workflow_bindings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    workflow_version_id: Mapped[int] = mapped_column(BigInteger, index=True) # References a vault document revision
    input_template_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    version_id: Mapped[int] = mapped_column(BigInteger, index=True) # References vault revision
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    trigger: Mapped[str] = mapped_column(String(50)) # manual, schedule, task
    input_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    scope_snapshot_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# Strategy Operating System (Phase 2B)
# ==========================================

class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    slug: Mapped[str] = mapped_column(String(255))
    current_version_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    scope_binding_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Unique constraint on (brain_id, slug) can be added via __table_args__ if needed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    definition_id: Mapped[int] = mapped_column(ForeignKey("workflow_definitions.id"), index=True)
    revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vault_revisions.id"), nullable=True, index=True)
    graph_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(50), default="draft") # draft, validated, published, archived
    graph_schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    validation_report_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    dependency_snapshot_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    revision_token: Mapped[str] = mapped_column(String(255), default=lambda: generate_snowflake_id()) # For optimistic concurrency
    scope_requirements_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    output_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WorkflowApproval(Base):
    __tablename__ = "workflow_approvals"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    step_id: Mapped[int] = mapped_column(ForeignKey("workflow_steps.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, approved, rejected
    snapshot_payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    scope_snapshot_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ==========================================
# Plugin and Telegram (Phase 5)
# ==========================================
