"""Wave 9 — A2A authority attenuation (Blueprint V2 §10.2 invariant:
Authority(child) ⊆ Authority(parent)). Test cố ý cho `requested` yêu cầu VƯỢT
quá parent ở từng chiều (capability, risk, expiry, tenant) — verify attenuation
luôn chặn, không bao giờ mở rộng quyền."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent.governance.contracts import CapabilityRisk
from agent_integrations.a2a.authority import A2AAuthorityGrant, attenuate_authority


def test_child_cannot_gain_capability_parent_does_not_have():
    parent = A2AAuthorityGrant(principal_id="parent_agent", tenant_id="t1", capability_refs=["operations.*"])
    requested = A2AAuthorityGrant(
        principal_id="child_agent", capability_refs=["operations.task.list", "finance.payout.execute"]
    )

    child = attenuate_authority(parent, requested)

    assert child.capability_refs == ["operations.task.list"]
    assert "finance.payout.execute" not in child.capability_refs


def test_child_cannot_exceed_parent_max_risk():
    parent = A2AAuthorityGrant(principal_id="parent_agent", capability_refs=["*"], max_risk=CapabilityRisk.MEDIUM)
    requested = A2AAuthorityGrant(principal_id="child_agent", capability_refs=["*"], max_risk=CapabilityRisk.CRITICAL)

    child = attenuate_authority(parent, requested)

    assert child.max_risk == CapabilityRisk.MEDIUM


def test_child_cannot_extend_expiry_beyond_parent():
    now = datetime.now(UTC)
    parent = A2AAuthorityGrant(
        principal_id="parent_agent", capability_refs=["*"], expires_at=now + timedelta(hours=1)
    )
    requested = A2AAuthorityGrant(
        principal_id="child_agent", capability_refs=["*"], expires_at=now + timedelta(days=30)
    )

    child = attenuate_authority(parent, requested)

    assert child.expires_at == parent.expires_at


def test_child_always_inherits_parent_tenant_not_requested_tenant():
    parent = A2AAuthorityGrant(principal_id="parent_agent", tenant_id="tenant_real", capability_refs=["*"])
    requested = A2AAuthorityGrant(principal_id="child_agent", tenant_id="tenant_attacker_supplied", capability_refs=["*"])

    child = attenuate_authority(parent, requested)

    assert child.tenant_id == "tenant_real"


def test_child_with_no_expiry_inherits_parent_expiry():
    now = datetime.now(UTC)
    parent = A2AAuthorityGrant(principal_id="parent_agent", capability_refs=["*"], expires_at=now + timedelta(hours=1))
    requested = A2AAuthorityGrant(principal_id="child_agent", capability_refs=["*"])  # no expiry requested

    child = attenuate_authority(parent, requested)

    assert child.expires_at == parent.expires_at
