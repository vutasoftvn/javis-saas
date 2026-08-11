from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base

class Brain(Base):
    __tablename__ = "brains"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'slug', name='uix_brain_workspace_slug'),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="brains")

class VaultDocument(Base):
    __tablename__ = "vault_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brains.id"), index=True)
    path: Mapped[str] = mapped_column(String(1024), index=True)
    kind: Mapped[str] = mapped_column(String(50)) # workflow, agent, strategy, etc.
    current_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("vault_revisions.id", use_alter=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VaultRevision(Base):
    __tablename__ = "vault_revisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vault_documents.id"), index=True)
    object_key: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brains.id"), index=True)
    object_key: Mapped[str] = mapped_column(String(1024))
    mime_type: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vault_revisions.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    fts: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)

class ChunkingJob(Base):
    __tablename__ = "chunking_jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vault_documents.id"), index=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vault_revisions.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="queued") # queued, processing, completed, failed
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class KnowledgeObject(Base):
    """Mô hình Knowledge Object - Tri thức có cấu trúc & vòng đời (§65–72)."""
    __tablename__ = "knowledge_objects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brains.id"), index=True)
    vault_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("vault_documents.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    object_type: Mapped[str] = mapped_column(String(50), default="note")  # note, research, fact, concept, decision, adr, requirement, lesson, architecture, skill_spec
    status: Mapped[str] = mapped_column(String(50), default="capture")  # capture, candidate, approved, superseded, archived
    source_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    generated_by: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeRelation(Base):
    """Mô hình Knowledge Relation - Quan hệ liên kết tri thức (wikilinks graph) (§65)."""
    __tablename__ = "knowledge_relations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    from_object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_objects.id"), index=True)
    to_object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_objects.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50), default="RELATED_TO")  # SUPPORTS, IMPLEMENTS, SUPERSEDES, AFFECTS, RELATED_TO
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


