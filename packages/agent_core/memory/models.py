from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["MemoryKind", "MemoryItem"]


class MemoryKind(str, enum.Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    ORGANIZATIONAL = "ORGANIZATIONAL"


class MemoryItem(BaseModel):
    """Bản ghi trí nhớ chuẩn hoá theo Master Guide §25."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    company_id: Optional[str] = None
    workspace_id: str
    agent_key: str
    kind: MemoryKind
    content: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    sensitivity: str = "normal"  # "normal", "confidential", "restricted"
    provenance_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
