from __future__ import annotations

import re
import pytest

from agent_core.governance.contracts import AutonomyLevel
from apps.cosa.agents.specs import (
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
)


def test_customer_support_autopilot_spec_structure_and_hashes():
    # Prompt is hash pinned
    assert COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.id == "cosa.agents.customer_support_autopilot.prompt"
    assert COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.version == "1.0.0"
    assert bool(COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.definition_hash)

    # Spec is pinned and write mode (L2_EXECUTE / L2_ACT)
    spec = COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC
    assert spec.id == "cosa.agents.customer_support_autopilot"
    assert spec.version == "1.0.0"
    assert spec.autonomy_level in (AutonomyLevel.L2, AutonomyLevel.L2_EXECUTE, AutonomyLevel.L2_EXECUTE_WITH_APPROVAL)

    # Required narrow capabilities for FAQ autopilot
    expected_caps = {
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
        "engagement.message.send",
        "engagement.assignment.write",
    }
    assert set(spec.capability_refs) == expected_caps


def test_customer_support_autopilot_spec_forbidden_capabilities_static_guard():
    spec = COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC

    # Static guard: NO billing, finance, CRM opportunity, or CRM lead write capabilities
    forbidden_pattern = re.compile(r"(billing\.|finance\.|\.opportunity\.|\.lead\.write)")
    for cap in spec.capability_refs:
        assert not forbidden_pattern.search(cap), f"Capability '{cap}' is forbidden in narrow support autopilot"
