"""Context Contracts for COSA Agent Platform.

Theo Hermes/LangGraph Integration Plan §3, Phase 1 và CONTEXT_ASSEMBLER_AUDIT.md:
Định nghĩa các hợp đồng tối thiểu về Context (ContextFragment, ContextSnapshot, ContextLifetime, ContextIntent).
Không import bất kỳ business domain models nào để bảo đảm tính framework-neutral.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = [
    "ContextLifetime",
    "ContextIntent",
    "ContextFragment",
    "ContextSnapshot",
]


class ContextLifetime(str, Enum):
    """Vòng đời của từng đoạn ngữ cảnh (Context Lifetime) theo Hermes Specification."""

    STABLE = "STABLE"        # Dữ liệu tĩnh/ổn định lâu dài (workspace profile, tenant policy, founder preferences)
    RUN = "RUN"              # Dữ liệu có hiệu lực trong phạm vi 1 Run cụ thể (project metadata, active plan)
    CURRENT = "CURRENT"      # Dữ liệu động tại thời điểm hiện tại (KPI snapshot, real-time balance)
    EPHEMERAL = "EPHEMERAL"  # Dữ liệu tạm thời chỉ dùng cho 1 turn/action (approval response, one-off signal)


class ContextIntent(BaseModel):
    """Định danh ý định ngữ cảnh framework-neutral, thay thế enum hardcoded của domain cũ."""

    kind: str = "general_chat"  # general_chat, strategic_review, project_task, domain_query, etc.
    domain: Optional[str] = None  # finance, operations, sales, marketing, legal, etc.
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextFragment(BaseModel):
    """Một phân mảnh ngữ cảnh có xuất xứ (provenance) và vòng đời rõ ràng."""

    source_kind: str  # rpc, memory, knowledge, system, static
    source_ref: str   # identifier của source (e.g. services.company.operations.task)
    lifetime: ContextLifetime = ContextLifetime.RUN
    content: str = ""
    token_estimate: int = 0
    sensitivity: str = "internal"  # public, internal, confidential, restricted
    provenance: dict[str, Any] = Field(default_factory=dict)
    freshness: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cache_key: Optional[str] = None


class ContextSnapshot(BaseModel):
    """Ảnh chụp toàn bộ ngữ cảnh được lắp ráp cho một Run cụ thể."""

    run_id: str
    principal_id: str
    tenant_id: str
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fragments: list[ContextFragment] = Field(default_factory=list)
    budget_tokens_remaining: int = 16000
    memory_access_enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def total_estimated_tokens(self) -> int:
        return sum(f.token_estimate for f in self.fragments)
