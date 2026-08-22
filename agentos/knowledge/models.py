from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeSourceType(str, enum.Enum):
    """Loại nguồn tài liệu (blueprint §66: docs/wiki/policies/manuals/specs/web pages/files)."""

    DOC = "DOC"
    WIKI = "WIKI"
    POLICY = "POLICY"
    MANUAL = "MANUAL"
    SPEC = "SPEC"
    WEB_PAGE = "WEB_PAGE"
    FILE = "FILE"


class KnowledgeSource(BaseModel):
    """1 tài liệu nguồn (trước khi chunk) — Knowledge khác Memory (blueprint
    §67): đây là tài liệu/fact ingest từ nguồn ngoài, không phải trải
    nghiệm runtime của agent.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    title: str
    source_type: KnowledgeSourceType
    uri: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeChunk(BaseModel):
    """1 đoạn văn bản đã chunk từ 1 KnowledgeSource, kèm embedding vector
    (nếu đã embed). `chunk_index` giữ thứ tự gốc trong tài liệu — cần khi
    ghép lại ngữ cảnh xung quanh 1 kết quả tìm kiếm.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    workspace_id: str
    chunk_index: int
    content: str
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchResult(BaseModel):
    chunk: KnowledgeChunk
    score: float
