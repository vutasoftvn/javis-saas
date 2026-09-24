from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import (
    COSA_EXECUTIVE_CISO_AGENT_SPEC,
    COSA_SECURITY_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)


def test_security_profile_has_explicit_spec_and_read_only_capability():
    spec = AGENT_PROFILE_SPECS["security"]
    assert spec is COSA_SECURITY_AGENT_SPEC
    assert spec.id == "cosa.agents.security"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "security.posture.read" in spec.capability_refs
    assert not any(
        ref.endswith(".write") or ref.endswith(".create_draft") for ref in spec.capability_refs
    )
    assert spec.compute_hash() == "54232cdc8454ebda917991b48eb38f639dae3e6d8db3081070b859561670d966"


def test_ciso_is_capability_empty_and_security_cannot_scan_or_access_secret():
    assert AGENT_PROFILE_SPECS["ciso"] is COSA_EXECUTIVE_CISO_AGENT_SPEC
    assert COSA_EXECUTIVE_CISO_AGENT_SPEC.id == "cosa.executive.ciso"
    assert COSA_EXECUTIVE_CISO_AGENT_SPEC.version == "1.1.0"  # overlay pin skill (advisor overlay contract)
    assert COSA_EXECUTIVE_CISO_AGENT_SPEC.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.ciso"].capability_refs == []
    assert COSA_EXECUTIVE_CISO_AGENT_SPEC.metadata.get("advisory_only") is True

    # CISO chỉ được đề xuất risk/control gap — không được scan target, rotate
    # secret, disable user, patch/deploy hay tự tuyên bố compliance/certification.
    assert "security.scan" not in AGENT_PROFILE_SPECS["security"].capability_refs
