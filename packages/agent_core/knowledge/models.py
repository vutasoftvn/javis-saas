from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["KnowledgeDocument", "KnowledgeChunk", "CitationProvenance"]


class KnowledgeChunk(BaseModel):
    """Một đoạn tri thức đã được băm nhỏ và nhúng vector theo Master Guide §26."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    workspace_id: str
    chunk_index: int
    content: str
    page_or_section: Optional[str] = None
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeDocument(BaseModel):
    """Tài liệu tri thức chuẩn hoá của doanh nghiệp."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    title: str
    source_uri: Optional[str] = None
    media_type: str = "text/plain"
    checksum: Optional[str] = None
    ingest_status: str = "completed"  # "pending", "processing", "completed", "failed"
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationProvenance(BaseModel):
    """Bằng chứng trích dẫn tri thức cung cấp cho LLM Context."""

    chunk_id: str
    document_id: str
    document_title: str
    source_uri: Optional[str] = None
    page_or_section: Optional[str] = None
    snippet: str
    similarity_score: float = 1.0
