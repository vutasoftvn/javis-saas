from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent.ids import uuid7_str  # LeafId UUIDv7 (M2 §3)

__all__ = ["MemoryItem", "MemoryKind", "MemoryStatus"]


class MemoryKind(enum.StrEnum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    ORGANIZATIONAL = "ORGANIZATIONAL"


class MemoryStatus(enum.StrEnum):
    """Vòng đời memory theo Blueprint V2 §26 — memory KHÔNG phải business
    truth; nếu mâu thuẫn với Company Service, Company Service thắng."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    RETRACTED = "RETRACTED"
    ARCHIVED = "ARCHIVED"


class MemoryItem(BaseModel):
    """Bản ghi trí nhớ chuẩn hoá theo Master Guide §25, mở rộng generic
    scope/provenance/lifecycle theo Blueprint V2 §26 (migration 009, Wave 8).

    workspace_id là khóa tenant duy nhất sau Task 7 (2026-08-27).
    """

    id: str = Field(default_factory=uuid7_str)
    application_id: str | None = None
    workspace_id: str
    scope_type: str | None = None
    scope_id: str | None = None
    agent_key: str
    subject_type: str | None = None
    subject_id: str | None = None
    kind: MemoryKind
    content: str
    content_hash: str | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    sensitivity: str = "normal"  # "normal", "confidential", "restricted"
    provenance_run_id: str | None = None
    source_event_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    status: MemoryStatus = MemoryStatus.ACTIVE
    valid_from: datetime | None = None
    supersedes_memory_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
