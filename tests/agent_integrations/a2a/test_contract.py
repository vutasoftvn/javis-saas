"""Contract and smoke tests for A2A adapter (A2AAuthorityGrant & attenuate_authority).

Asserts:
- Authority grant initialization and serialization.
- attenuate_authority enforces Authority(child) ⊆ Authority(parent):
  - capability_refs filtered by parent allowlist and wildcard patterns.
  - max_risk is bounded by parent max_risk.
  - expires_at is bounded by earlier timestamp.
  - tenant_id is strictly inherited from parent.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent.governance.contracts import CapabilityRisk
from agent_integrations.a2a.authority import A2AAuthorityGrant, attenuate_authority


def test_a2a_grant_initialization():
    """A2AAuthorityGrant model initialization and default values."""
    grant = A2AAuthorityGrant(
        principal_id="agent_alpha",
        tenant_id="tenant_123",
        capability_refs=["finance.payout.execute", "operations.*"],
        max_risk=CapabilityRisk.HIGH,
    )
    assert grant.principal_id == "agent_alpha"
    assert grant.tenant_id == "tenant_123"
    assert grant.max_risk == CapabilityRisk.HIGH
    assert len(grant.capability_refs) == 2


def test_a2a_attenuate_authority_capability_filtering():
    """Child cannot acquire capabilities not allowed by parent."""
    parent = A2AAuthorityGrant(
        principal_id="parent_agent",
        tenant_id="tenant_x",
        capability_refs=["commercial.*", "operations.task.read"],
        max_risk=CapabilityRisk.MEDIUM,
    )

    requested = A2AAuthorityGrant(
        principal_id="child_agent",
        tenant_id="tenant_y",  # Attempting to override tenant
        capability_refs=[
            "commercial.marketing_context.write",  # matches commercial.* -> ALLOW
            "operations.task.read",  # exact match -> ALLOW
            "finance.payout.execute",  # not in parent -> DENY
        ],
        max_risk=CapabilityRisk.CRITICAL,  # Exceeds parent -> CLAMP
    )

    attenuated = attenuate_authority(parent, requested)

    assert attenuated.principal_id == "child_agent"
    assert attenuated.tenant_id == "tenant_x"  # Strictly parent's tenant
    assert attenuated.max_risk == CapabilityRisk.MEDIUM  # Clamped to parent
    assert set(attenuated.capability_refs) == {
        "commercial.marketing_context.write",
        "operations.task.read",
    }


def test_a2a_attenuate_authority_expiry_intersection():
    """Earlier expiry date always takes precedence."""
    now = datetime.now(UTC)
    t_early = now + timedelta(hours=1)
    t_late = now + timedelta(hours=5)

    # Parent earlier
    p1 = A2AAuthorityGrant(principal_id="p1", expires_at=t_early)
    r1 = A2AAuthorityGrant(principal_id="c1", expires_at=t_late)
    assert attenuate_authority(p1, r1).expires_at == t_early

    # Child earlier
    p2 = A2AAuthorityGrant(principal_id="p2", expires_at=t_late)
    r2 = A2AAuthorityGrant(principal_id="c2", expires_at=t_early)
    assert attenuate_authority(p2, r2).expires_at == t_early

    # One is None
    p3 = A2AAuthorityGrant(principal_id="p3", expires_at=None)
    r3 = A2AAuthorityGrant(principal_id="c3", expires_at=t_early)
    assert attenuate_authority(p3, r3).expires_at == t_early
