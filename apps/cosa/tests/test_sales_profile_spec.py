from __future__ import annotations

from agent.governance.contracts import AutonomyLevel
from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import COSA_SALES_AGENT_SPEC


def test_sales_profile_has_explicit_spec_and_no_external_write_capability():
    spec = AGENT_PROFILE_SPECS["sales"]
    assert spec is COSA_SALES_AGENT_SPEC
    assert spec.id == "cosa.agents.sales"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "engagement.message.send" not in spec.capability_refs
    assert "project.crm.read" in spec.capability_refs
    assert spec.compute_hash() == "089a67c81dc22041835b0ed05df7a441305c6abe416f293f609cc5262d31f332"
