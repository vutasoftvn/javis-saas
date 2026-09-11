from __future__ import annotations

from agent.governance.contracts import PolicyOutcome

from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.policies.snapshot import (
    AgentCapabilityAuthority,
)
from tests.apps.cosa.policy_test_helpers import (
    agent_authority_snapshot,
    policy_snapshot_with,
)


def test_platform_allow_cannot_bypass_missing_company_agent_grant() -> None:
    snapshot = policy_snapshot_with(
        control_rule=("operations.task.*", "ALLOW"),
        agent_authority=agent_authority_snapshot(grants=[]),
    )
    decision = CosaPolicyEngine().evaluate(
        "operations.task.list", {}, {"policy_snapshot": snapshot}
    )
    assert decision.outcome is PolicyOutcome.DENY
    assert "MISSING_AGENT_CAPABILITY_GRANT" in decision.reasons


def test_platform_deny_overrides_agent_grant() -> None:
    grant = AgentCapabilityAuthority(
        capability_id="operations.task.list",
        permission_key="operations.task.read",
        risk_class="READ",
        grant_id="grant-1",
        constraints={},
    )
    snapshot = policy_snapshot_with(
        control_rule=("operations.task.*", "DENY"),
        agent_authority=agent_authority_snapshot(grants=[grant]),
    )
    decision = CosaPolicyEngine().evaluate(
        "operations.task.list", {}, {"policy_snapshot": snapshot}
    )
    assert decision.outcome is PolicyOutcome.DENY
    assert any("DENY" in r for r in decision.reasons)


def test_agent_grant_allows_when_control_plane_has_no_deny() -> None:
    grant = AgentCapabilityAuthority(
        capability_id="operations.task.list",
        permission_key="operations.task.read",
        risk_class="READ",
        grant_id="grant-1",
        constraints={},
    )
    snapshot = policy_snapshot_with(
        control_rule=None,
        agent_authority=agent_authority_snapshot(grants=[grant]),
    )
    decision = CosaPolicyEngine().evaluate(
        "operations.task.list", {}, {"policy_snapshot": snapshot}
    )
    assert decision.outcome is PolicyOutcome.ALLOW
