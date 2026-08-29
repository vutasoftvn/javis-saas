from __future__ import annotations

import pytest

from agent_core.governance.contracts import (
    ApprovalPolicy,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)
from agent_core.governance.floor import capability_floor, conjoin


def test_capability_floor_always_requires_approval():
    # ApprovalPolicy.ALWAYS always requires approval, regardless of risk
    assert capability_floor(CapabilityRisk.LOW, ApprovalPolicy.ALWAYS) == PolicyOutcome.REQUIRE_APPROVAL
    assert capability_floor(CapabilityRisk.MEDIUM, ApprovalPolicy.ALWAYS) == PolicyOutcome.REQUIRE_APPROVAL
    assert capability_floor(CapabilityRisk.HIGH, ApprovalPolicy.ALWAYS) == PolicyOutcome.REQUIRE_APPROVAL


def test_capability_floor_high_risk_requires_approval():
    assert capability_floor(CapabilityRisk.HIGH, ApprovalPolicy.POLICY_DRIVEN) == PolicyOutcome.REQUIRE_APPROVAL
    assert capability_floor(CapabilityRisk.CRITICAL, ApprovalPolicy.POLICY_DRIVEN) == PolicyOutcome.REQUIRE_APPROVAL


def test_capability_floor_low_risk_allows():
    assert capability_floor(CapabilityRisk.LOW, ApprovalPolicy.POLICY_DRIVEN) == PolicyOutcome.ALLOW
    assert capability_floor(CapabilityRisk.LOW, ApprovalPolicy.NEVER) == PolicyOutcome.ALLOW


def test_conjoin_strictness_order():
    # ALLOW + ALLOW -> ALLOW
    d = conjoin(PolicyOutcome.ALLOW, PolicyOutcome.ALLOW)
    assert d.outcome == PolicyOutcome.ALLOW

    # REQUIRE_APPROVAL + ALLOW -> REQUIRE_APPROVAL (floor cannot be relaxed by tenant ALLOW)
    d = conjoin(PolicyOutcome.REQUIRE_APPROVAL, PolicyOutcome.ALLOW)
    assert d.outcome == PolicyOutcome.REQUIRE_APPROVAL

    # ALLOW + REQUIRE_APPROVAL -> REQUIRE_APPROVAL (tenant policy can tighten)
    d = conjoin(PolicyOutcome.ALLOW, PolicyOutcome.REQUIRE_APPROVAL)
    assert d.outcome == PolicyOutcome.REQUIRE_APPROVAL

    # REQUIRE_APPROVAL + DENY -> DENY (DENY wins)
    d = conjoin(PolicyOutcome.REQUIRE_APPROVAL, PolicyOutcome.DENY)
    assert d.outcome == PolicyOutcome.DENY

    # DENY + ALLOW -> DENY
    d = conjoin(PolicyOutcome.DENY, PolicyOutcome.ALLOW)
    assert d.outcome == PolicyOutcome.DENY


def test_conjoin_preserves_requirement():
    req = RoleApproval(role="cfo")
    tenant_dec = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=req)
    d = conjoin(PolicyOutcome.ALLOW, tenant_dec)
    assert d.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert d.requirement == req
