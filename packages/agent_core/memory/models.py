from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["MemoryKind", "MemoryStatus", "MemoryItem"]


class MemoryKind(str, enum.Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    ORGANIZATIONAL = "ORGANIZATIONAL"


class MemoryStatus(str, enum.Enum):
    """Vòng đời memory theo Blueprint V2 §26 — memory KHÔNG phải business
    truth; nếu mâu thuẫn với Company Service, Company Service thắng."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    RETRACTED = "RETRACTED"
    ARCHIVED = "ARCHIVED"


class MemoryItem(BaseModel):
    """Bản ghi trí nhớ chuẩn hoá theo Master Guide §25, mở rộng generic
    scope/provenance/lifecycle theo Blueprint V2 §26 (migration 009, Wave 8)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    application_id: Optional[str] = None
    tenant_id: Optional[str] = None
    company_id: Optional[str] = None
    workspace_id: str
    scope_type: Optional[str] = None
    scope_id: Optional[str] = None
    agent_key: str
    subject_type: Optional[str] = None
    subject_id: Optional[str] = None
    kind: MemoryKind
    content: str
    content_hash: Optional[str] = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    sensitivity: str = "normal"  # "normal", "confidential", "restricted"
    provenance_run_id: Optional[str] = None
    source_event_id: Optional[str] = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    status: MemoryStatus = MemoryStatus.ACTIVE
    valid_from: Optional[datetime] = None
    supersedes_memory_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
