from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import (
    COSA_EXECUTIVE_CHRO_AGENT_SPEC,
    COSA_PEOPLE_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)


def test_people_profile_has_explicit_spec_and_read_only_capability():
    spec = AGENT_PROFILE_SPECS["people"]
    assert spec is COSA_PEOPLE_AGENT_SPEC
    assert spec.id == "cosa.agents.people"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "people.risk.read" in spec.capability_refs
    assert not any(
        ref.endswith(".write") or ref.endswith(".create_draft") for ref in spec.capability_refs
    )
    assert spec.compute_hash() == "a03fcb1d3050bf4f364ca7c9e7581b443c08d3dac781199162626a5329dc0b05"


def test_chro_is_advisory_only_with_no_capability_refs():
    assert AGENT_PROFILE_SPECS["chro"] is COSA_EXECUTIVE_CHRO_AGENT_SPEC
    assert COSA_EXECUTIVE_CHRO_AGENT_SPEC.id == "cosa.executive.chro"
    assert (
        COSA_EXECUTIVE_CHRO_AGENT_SPEC.version == "1.1.0"
    )  # overlay pin skill (advisor overlay contract)
    assert COSA_EXECUTIVE_CHRO_AGENT_SPEC.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.chro"].capability_refs == []
    assert COSA_EXECUTIVE_CHRO_AGENT_SPEC.metadata.get("advisory_only") is True
