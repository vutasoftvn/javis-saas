"""Chính sách lifecycle cho MemoryService (P1 Task 6).

Production service khai báo tường minh — không để mặc định ngầm quyết định
memory sống bao lâu / tối đa bao nhiêu item / scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from agent.memory.models import MemoryKind

__all__ = ["RetentionPolicy"]


@dataclass(frozen=True)
class RetentionPolicy:
    ttl_by_kind: dict[MemoryKind, timedelta] = field(default_factory=dict)
    max_items_per_scope: int = 10_000

    @classmethod
    def permissive(cls) -> RetentionPolicy:
        """Không TTL, hạn mức rất cao — dùng cho test/dev."""
        return cls(ttl_by_kind={}, max_items_per_scope=1_000_000)
