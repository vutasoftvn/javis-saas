from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["PublishedSpecRecord"]


class PublishedSpecRecord(BaseModel):
    """Bản ghi spec đã publish, bất biến, trong agent_registry.published_specs
    (Blueprint V2 §25). `content` là snapshot đầy đủ của spec tại thời điểm
    publish — cho phép resolve lại đúng nội dung đã dùng cho 1 Run cũ dù code
    hiện tại đã đổi `instructions`/`capability_refs`."""

    spec_kind: str  # "agent" | "workflow" | "skill" | "capability" | "plugin"
    spec_id: str
    version: str
    definition_hash: str
    content: dict[str, Any]
    status: str = "published"  # published | retired
    publisher: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retired_at: datetime | None = None
