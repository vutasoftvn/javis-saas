"""Delegation Envelope & Authority Attenuation Subsystem (Track 9B).

Theo Hermes/LangGraph Integration Plan §3 (Track 9B, HL-06, HL-07, HL-08):
Định nghĩa DelegationEnvelope chuẩn và invariant suy giảm quyền hạn (Authority Attenuation):
    Authority(child) ⊆ Authority(parent) ∩ Delegated Ceiling ∩ Child Spec ∩ Current Grants
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Set
from pydantic import BaseModel, Field

from agent_core.contracts.identity import PinnedSpecIdentity

__all__ = [
    "DelegationStatus",
    "DelegationEnvelope",
    "compute_effective_child_authority",
]


class DelegationStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DelegationEnvelope(BaseModel):
    """Bao bọc uỷ quyền đầy đủ giữa Parent Agent và Child Agent."""

    delegation_id: str
    parent_run_id: str
    child_run_id: str
    parent_spec_identity: PinnedSpecIdentity
    child_spec_identity: PinnedSpecIdentity
    goal: str
    context_snapshot_ref: Optional[str] = None
    delegated_capability_ceiling: list[str] = Field(default_factory=list)
    budget_token_limit: int = 4000
    depth: int = 1
    max_depth: int = 3
    status: DelegationStatus = DelegationStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_effective_child_authority(
    parent_capabilities: list[str] | set[str],
    child_spec_capabilities: list[str] | set[str],
    delegated_ceiling: list[str] | set[str],
    revoked_capabilities: Optional[set[str]] = None,
) -> set[str]:
    """Tính toán quyền hạn hiệu lực của Child Agent tuân thủ nghiêm ngặt Invariant Authority Attenuation.
    
    Quyền của Child là giao (intersection) của:
    1. Quyền thực tế của Parent
    2. Trần quyền hạn được uỷ quyền (Delegated Ceiling)
    3. Khai báo trong AgentSpec của Child
    Trừ đi bất kỳ quyền nào đã bị revoke trong ambient governance.
    """
    parent_set = set(parent_capabilities)
    child_spec_set = set(child_spec_capabilities)
    ceiling_set = set(delegated_ceiling) if delegated_ceiling else child_spec_set
    revoked = revoked_capabilities or set()

    # Authority(child) = (Parent ∩ Ceiling ∩ ChildSpec) - Revoked
    effective = parent_set.intersection(ceiling_set).intersection(child_spec_set)
    return effective - revoked
