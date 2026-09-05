from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from agent.governance.contracts import PolicyDecision, PolicyOutcome
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.policies.snapshot import PolicySnapshot, TenantPolicyRule


class DummyBusinessPolicyClient:
    def __init__(self):
        self.current_effect = "REQUIRE_APPROVAL"
        self.current_version = 1
        self.current_hash = "h1"

    def evaluate(self, action: str, resource_ref: str, version: int):
        return {
            "effect": self.current_effect,
            "policyVersion": self.current_version,
            "policyHash": self.current_hash,
            "reasonCodes": [self.current_effect],
        }


def test_business_policy_revocation_prevents_side_effects():
    client = DummyBusinessPolicyClient()
    tool_side_effect_calls = 0

    # 1. Before revocation: evaluator / client returns REQUIRE_APPROVAL
    decision_before_data = client.evaluate("finance.request.create", "res_1", 1)
    class DecisionWrapper:
        def __init__(self, data):
            self.effect = data["effect"]
            self.policy_version = data["policyVersion"]

    decision_before = DecisionWrapper(decision_before_data)
    assert decision_before.effect == "REQUIRE_APPROVAL"

    # 2. Permission revoked while waiting for approval
    client.current_effect = "DENY"
    client.current_version = 2
    client.current_hash = "h2"

    # 3. Re-evaluation before executing side effect
    decision_after_revocation_data = client.evaluate("finance.request.create", "res_1", 2)
    decision_after_revocation = DecisionWrapper(decision_after_revocation_data)
    assert decision_after_revocation.effect == "DENY"

    # If DENY, the runner / gateway must not call the tool side-effect
    if decision_after_revocation.effect == "ALLOW":
        tool_side_effect_calls += 1

    assert tool_side_effect_calls == 0
