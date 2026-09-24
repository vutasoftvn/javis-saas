from __future__ import annotations

from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.specs import (
    COSA_AI_GOVERNANCE_AGENT_SPEC,
    COSA_EXECUTIVE_CAIO_AGENT_SPEC,
    EXECUTIVE_AGENT_SPECS,
)

# Capability id shapes that would let CAIO change policy, publish/pin/retire a
# skill, rotate a provider secret, invoke a model or approve a promotion —
# none of these may ever appear on the capability-empty CAIO spec (global
# constraint, task-3-brief).
_FORBIDDEN_CAPABILITY_SUBSTRINGS = (
    "skill.publish",
    "skill.pin",
    "skill.retire",
    "model.policy.write",
    "model.provider",
    "provider.secret",
    "model.invoke",
    "promotion.approve",
    "approval",
)


def test_ai_governance_profile_has_explicit_spec_and_read_only_capability():
    spec = AGENT_PROFILE_SPECS["ai_governance"]
    assert spec is COSA_AI_GOVERNANCE_AGENT_SPEC
    assert spec.id == "cosa.agents.ai_governance"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "ai.governance.read" in spec.capability_refs
    # AI Governance cannot write ANYTHING — not just an ai governance write capability.
    assert not any(
        ref.endswith(".write") or ref.endswith(".create_draft") or ref.endswith(".confirm")
        for ref in spec.capability_refs
    )
    assert spec.compute_hash() == "5cea97aae46c8c872708356cd7b52195760b9dfc62969b40b96bd2ba77f15f99"


def test_ai_governance_profile_capability_refs_never_touch_governance_write_surface():
    spec = AGENT_PROFILE_SPECS["ai_governance"]
    for ref in spec.capability_refs:
        for forbidden in _FORBIDDEN_CAPABILITY_SUBSTRINGS:
            assert forbidden not in ref, (
                f"forbidden capability surface {ref!r} found on ai_governance spec"
            )


def test_caio_is_capability_empty_and_carries_advisory_disclaimer():
    assert AGENT_PROFILE_SPECS["caio"] is COSA_EXECUTIVE_CAIO_AGENT_SPEC
    assert COSA_EXECUTIVE_CAIO_AGENT_SPEC.id == "cosa.executive.caio"
    assert COSA_EXECUTIVE_CAIO_AGENT_SPEC.version == "1.1.0"  # overlay pin skill (advisor overlay contract)
    assert COSA_EXECUTIVE_CAIO_AGENT_SPEC.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.caio"].capability_refs == []
    assert COSA_EXECUTIVE_CAIO_AGENT_SPEC.metadata.get("advisory_only") is True


def test_caio_cannot_change_policy_or_read_foreign_snapshot():
    # Mirror plan brief's Step 1 red test intent: CAIO is capability-empty, so
    # it structurally cannot invoke ANY capability (policy write, skill
    # publish, or even the read capability itself) — there is nothing in its
    # capability_refs for a gateway to resolve and execute.
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.caio"].capability_refs == []


def test_ai_governance_profile_has_no_write_and_caio_has_no_capability():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.caio"].capability_refs == []
    assert AGENT_PROFILE_SPECS["ai_governance"].capability_refs == [
        "ai.governance.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ]
