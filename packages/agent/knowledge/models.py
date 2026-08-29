from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent.ids import uuid7_str  # LeafId UUIDv7 (M2 §3)

__all__ = ["CitationProvenance", "KnowledgeChunk", "KnowledgeDocument"]


class KnowledgeChunk(BaseModel):
    """Một đoạn tri thức đã được băm nhỏ và nhúng vector theo Master Guide §26."""

    id: str = Field(default_factory=uuid7_str)
    document_id: str
    workspace_id: str
    chunk_index: int
    content: str
    content_hash: str | None = None
    page_or_section: str | None = None
    chunker_name: str | None = None
    chunker_version: str | None = None
    embedding: list[float] | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeDocument(BaseModel):
    """Tài liệu tri thức chuẩn hoá của doanh nghiệp.

    `authority_class` theo Blueprint V2 §27 (Wave 8, migration 010):
    REFERENCE | POLICY | BUSINESS_SNAPSHOT | USER_CONTENT | EXTERNAL.
    BUSINESS_SNAPSHOT không thay thế live business query — Company Service
    vẫn là nguồn sự thật cho state hiện tại.

    `ingest_status` cho phép:
    - Raw ingestion pipeline: "pending", "processing", "completed", "failed"
    - Review pipeline (Phase A): "review_pending", "published", "rejected"
    """

    id: str = Field(default_factory=uuid7_str)
    workspace_id: str
    title: str
    source_uri: str | None = None
    media_type: str = "text/plain"
    checksum: str | None = None
    authority_class: str = "REFERENCE"
    ingest_status: str = "completed"  # Expanded to include: "pending", "processing", "completed", "failed", "review_pending", "published", "rejected"
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationProvenance(BaseModel):
    """Bằng chứng trích dẫn tri thức cung cấp cho LLM Context."""

    chunk_id: str
    document_id: str
    document_title: str
    source_uri: str | None = None
    page_or_section: str | None = None
    snippet: str
    similarity_score: float = 1.0
