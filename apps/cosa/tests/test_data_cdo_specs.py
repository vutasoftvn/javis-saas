from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import (
    COSA_DATA_AGENT_SPEC,
    COSA_EXECUTIVE_CDO_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)


def test_data_profile_has_explicit_spec_and_read_only_capability():
    spec = AGENT_PROFILE_SPECS["data"]
    assert spec is COSA_DATA_AGENT_SPEC
    assert spec.id == "cosa.agents.data"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "data.governance.read" in spec.capability_refs
    # Data cannot write ANYTHING — not just a data governance write capability.
    assert not any(
        ref.endswith(".write") or ref.endswith(".create_draft") or ref.endswith(".confirm")
        for ref in spec.capability_refs
    )
    assert spec.compute_hash() == "71535c32bc5d48e79e8b92887e5f9fd549d6142c0a2582690e6a5e6ca65fb21f"


def test_cdo_is_capability_empty_and_carries_advisory_disclaimer():
    assert AGENT_PROFILE_SPECS["cdo"] is COSA_EXECUTIVE_CDO_AGENT_SPEC
    assert COSA_EXECUTIVE_CDO_AGENT_SPEC.id == "cosa.executive.cdo"
    assert COSA_EXECUTIVE_CDO_AGENT_SPEC.version == "1.1.0"  # overlay pin skill (advisor overlay contract)
    assert COSA_EXECUTIVE_CDO_AGENT_SPEC.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cdo"].capability_refs == []
    assert COSA_EXECUTIVE_CDO_AGENT_SPEC.metadata.get("advisory_only") is True


def test_cdo_cannot_read_raw_data_or_change_governance():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cdo"].capability_refs == []
    assert "data.asset.raw.read" not in AGENT_PROFILE_SPECS["data"].capability_refs


def test_data_profile_has_no_write_and_cdo_has_no_capability():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cdo"].capability_refs == []
    assert AGENT_PROFILE_SPECS["data"].capability_refs == [
        "data.governance.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ]
