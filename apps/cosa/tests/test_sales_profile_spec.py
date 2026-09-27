from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import COSA_EXECUTIVE_CRO_AGENT_SPEC, COSA_SALES_AGENT_SPEC


def test_sales_profile_has_explicit_spec_and_no_external_write_capability():
    spec = AGENT_PROFILE_SPECS["sales"]
    assert spec is COSA_SALES_AGENT_SPEC
    assert spec.id == "cosa.agents.sales"
    assert spec.version == "1.1.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "engagement.message.send" not in spec.capability_refs
    assert "project.crm.read" in spec.capability_refs
    assert spec.compute_hash() == "3604eb24d4ddd9f45c55253c4a72e37ca271e4128833ac9be1d23abba11633d2"


def test_cro_executive_profile_has_explicit_capability_empty_spec():
    """CRO là role duy nhất trong 8 executive role thiếu hẳn AgentSpec (final
    whole-branch review) — test này khoá lại shape sau khi bổ sung để không
    tái diễn: capability-empty, L1_PROPOSE, advisory-only, ánh xạ đúng qua
    AGENT_PROFILE_SPECS["cro"]."""
    spec = AGENT_PROFILE_SPECS["cro"]
    assert spec is COSA_EXECUTIVE_CRO_AGENT_SPEC
    assert spec.id == "cosa.executive.cro"
    assert spec.version == "1.1.0"  # overlay pin skill (advisor overlay contract)
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert spec.capability_refs == []
    # Overlay advisory pin đúng 1 skill cro-advisor (contract executive-advisor-overlays).
    assert [pin.skill_id for pin in spec.pinned_skills] == ["executive.cro-advisor"]
    assert spec.metadata.get("advisory_only") is True
    assert spec.compute_hash() == "55b0df2e6bdde7cbb3ad4a86122639514adfb262d06eff4eba9dc7598cbd1f75"
