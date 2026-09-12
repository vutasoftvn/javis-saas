from __future__ import annotations

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import EXECUTIVE_AGENT_SPECS


def test_vpe_is_advisory_only_and_coding_cannot_receive_generic_shell():
    assert AGENT_PROFILE_SPECS["coding"].id == "cosa.agents.coding"
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.vpe"].capability_refs == []
    assert "local.shell.run" not in AGENT_PROFILE_SPECS["coding"].capability_refs
    assert "engineering.evidence.read" in AGENT_PROFILE_SPECS["coding"].capability_refs
