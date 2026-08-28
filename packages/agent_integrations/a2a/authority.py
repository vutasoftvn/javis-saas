from __future__ import annotations

from datetime import datetime

from agent_core.governance.contracts import CapabilityRisk
from pydantic import BaseModel, Field

__all__ = ["A2AAuthorityGrant", "attenuate_authority"]

_RISK_ORDER = {
    CapabilityRisk.LOW: 0,
    CapabilityRisk.MEDIUM: 1,
    CapabilityRisk.HIGH: 2,
    CapabilityRisk.CRITICAL: 3,
}


class A2AAuthorityGrant(BaseModel):
    """Phạm vi quyền hạn cho 1 remote agent (A2A) — Blueprint V2 §10.2.
    `capability_refs` hỗ trợ wildcard prefix kiểu `"finance.*"` (khớp
    `capability_refs` của `AgentSpec`, cùng convention với policy tool_pattern
    ở `services/cosa/services/agent-policy.service.ts`)."""

    principal_id: str
    tenant_id: str | None = None
    capability_refs: list[str] = Field(default_factory=list)
    max_risk: CapabilityRisk = CapabilityRisk.LOW
    expires_at: datetime | None = None


def _capability_allowed(capability_id: str, allowed_refs: list[str]) -> bool:
    for ref in allowed_refs:
        if ref == capability_id:
            return True
        if ref.endswith(".*") and capability_id.startswith(ref[:-1]):
            return True
        if ref == "*":
            return True
    return False


def attenuate_authority(
    parent: A2AAuthorityGrant, requested: A2AAuthorityGrant
) -> A2AAuthorityGrant:
    """Tính authority thực tế cho remote child agent = giao (intersection) của
    parent grant và requested grant. Bất biến bắt buộc (Blueprint V2 §10.2):
    `Authority(child) ⊆ Authority(parent)` — child KHÔNG BAO GIỜ có quyền vượt
    quá parent dù `requested` yêu cầu rộng hơn.

    - `capability_refs`: chỉ giữ lại capability nào requested VÀ được parent
      cho phép (theo wildcard prefix của parent).
    - `max_risk`: min(parent, requested) theo thứ tự LOW < MEDIUM < HIGH < CRITICAL.
    - `expires_at`: sớm hơn giữa 2 bên (None nghĩa là không giới hạn — nếu 1
      bên có hạn, hạn đó áp dụng; nếu cả 2 có hạn, lấy hạn sớm hơn).
    - `tenant_id`: LUÔN lấy theo parent — child không được tự chọn tenant khác
      tenant của parent.
    """
    attenuated_caps = [
        c for c in requested.capability_refs if _capability_allowed(c, parent.capability_refs)
    ]

    max_risk = (
        requested.max_risk
        if _RISK_ORDER[requested.max_risk] < _RISK_ORDER[parent.max_risk]
        else parent.max_risk
    )

    if parent.expires_at is None:
        expires_at = requested.expires_at
    elif requested.expires_at is None:
        expires_at = parent.expires_at
    else:
        expires_at = min(parent.expires_at, requested.expires_at)

    return A2AAuthorityGrant(
        principal_id=requested.principal_id,
        tenant_id=parent.tenant_id,
        capability_refs=attenuated_caps,
        max_risk=max_risk,
        expires_at=expires_at,
    )
