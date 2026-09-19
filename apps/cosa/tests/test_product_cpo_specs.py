from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import (
    COSA_EXECUTIVE_CPO_AGENT_SPEC,
    COSA_PRODUCT_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)


def test_product_profile_has_explicit_spec_and_read_only_capability():
    spec = AGENT_PROFILE_SPECS["product"]
    assert spec is COSA_PRODUCT_AGENT_SPEC
    assert spec.id == "cosa.agents.product"
    assert spec.version == "1.1.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "product.decision.read" in spec.capability_refs
    assert not any(
        ref.endswith(".write") or ref.endswith(".create_draft") for ref in spec.capability_refs
    )
    assert spec.compute_hash() == "b1dd13108cde94d879b774e1eace24b29660360e68285880c650d24d6532dda7"


def test_cpo_is_advisory_only_with_no_capability_refs():
    assert AGENT_PROFILE_SPECS["cpo"] is COSA_EXECUTIVE_CPO_AGENT_SPEC
    assert COSA_EXECUTIVE_CPO_AGENT_SPEC.id == "cosa.executive.cpo"
    assert COSA_EXECUTIVE_CPO_AGENT_SPEC.version == "1.1.0"
    assert COSA_EXECUTIVE_CPO_AGENT_SPEC.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cpo"].capability_refs == []
    assert COSA_EXECUTIVE_CPO_AGENT_SPEC.metadata.get("advisory_only") is True
