from __future__ import annotations

import re
from agent.governance.contracts import AutonomyLevel
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC as S

FORBIDDEN = re.compile(
    r"(\.write$|\.send$|\.execute$|message\.send|assignment\.write|lead\.write|opportunity\.write)"
)


def test_copilot_spec_is_artifact_only():
    assert S.autonomy_level in (AutonomyLevel.L0_OBSERVE, AutonomyLevel.L0)
    assert S.autonomy_level.value == "L0"
    for cap in S.capability_refs:
        assert not FORBIDDEN.search(cap), f"copilot must not hold write/send capability: {cap}"


def test_copilot_spec_prompt_and_model_pinned():
    assert S.prompt_ref.definition_hash
    assert S.model_policy_ref is not None


def test_copilot_spec_capabilities():
    expected_caps = {
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
    }
    assert set(S.capability_refs) == expected_caps
