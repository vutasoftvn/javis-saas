from __future__ import annotations

from agent.contracts.identity import PinnedSkillRef
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.advisor_overlay_validation import validate_advisor_overlay
from apps.cosa.agents.capability_readiness import check_agent_spec_readiness

PROFILE = AgentSpec(
    id="profile",
    autonomy_level=AutonomyLevel.L1,
    capability_refs=["cap.read"],
    model_input_capability_ref="model.input.direct-user-message",
)
SKILL = PinnedSkillRef(skill_id="s.one", version="1.0.0", definition_hash="h" * 64)


def _overlay(**kw) -> AgentSpec:
    base = {
        "id": "overlay",
        "autonomy_level": AutonomyLevel.L1_PROPOSE,
        "capability_refs": [],
        "model_input_capability_ref": "model.input.direct-user-message",
        "pinned_skills": [SKILL],
    }
    return AgentSpec(**{**base, **kw})


def test_valid_contained_overlay():
    assert (
        validate_advisor_overlay(_overlay(), PROFILE, {"s.one": {"runtime": {"tools": []}}}) == []
    )


def test_extra_capability_rejected():
    out = validate_advisor_overlay(_overlay(capability_refs=["cap.write"]), PROFILE)
    assert out == ["capabilities_outside_profile:cap.write"]


def test_higher_autonomy_rejected():
    out = validate_advisor_overlay(_overlay(autonomy_level=AutonomyLevel.L2), PROFILE)
    assert any(v.startswith("autonomy_exceeds_advisory") for v in out)


def test_missing_skill_manifest_rejected():
    assert validate_advisor_overlay(_overlay(), PROFILE, {}) == ["skill_manifest_missing:s.one"]


def test_skill_tool_outside_overlay_rejected_and_readiness_reports_it():
    manifests = {"s.one": {"runtime": {"tools": ["cap.read"]}}}
    out = validate_advisor_overlay(_overlay(), PROFILE, manifests)
    assert out == ["skill_tools_outside_overlay:s.one:cap.read"]
    # Readiness phải báo tool skill thiếu trong capability_refs dù registry có sẵn.
    assert check_agent_spec_readiness(_overlay(), {"cap.read"}, manifests) == ["cap.read"]
