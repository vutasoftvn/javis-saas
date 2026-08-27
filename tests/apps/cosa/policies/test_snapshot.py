from __future__ import annotations

from apps.cosa.policies.snapshot import PolicySnapshot, TenantPolicyRule


def _snapshot(rules: list[TenantPolicyRule]) -> PolicySnapshot:
    return PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=rules,
        snapshot_hash="h1",
    )


def test_exact_match_wins_over_wildcard():
    snap = _snapshot(
        [
            TenantPolicyRule(tool_pattern="*", decision="ALLOW"),
            TenantPolicyRule(tool_pattern="commercial.notification.slack_send", decision="DENY", reason="blocked"),
        ]
    )
    matched = snap.match("commercial.notification.slack_send")
    assert matched is not None
    assert matched.decision == "DENY"
    assert matched.reason == "blocked"


def test_prefix_wildcard_match():
    snap = _snapshot([TenantPolicyRule(tool_pattern="finance.*", decision="REQUIRE_APPROVAL")])
    matched = snap.match("finance.transfer.funds")
    assert matched is not None
    assert matched.decision == "REQUIRE_APPROVAL"


def test_longest_prefix_wins():
    snap = _snapshot(
        [
            TenantPolicyRule(tool_pattern="finance.*", decision="REQUIRE_APPROVAL"),
            TenantPolicyRule(tool_pattern="finance.wire.*", decision="DENY"),
        ]
    )
    matched = snap.match("finance.wire.international")
    assert matched is not None
    assert matched.decision == "DENY"


def test_no_match_returns_none():
    snap = _snapshot([TenantPolicyRule(tool_pattern="finance.*", decision="DENY")])
    assert snap.match("commercial.lead.create") is None


def test_from_context_none_when_missing():
    assert PolicySnapshot.from_context({}) is None


def test_from_context_parses_dict():
    raw = {
        "workspace_id": "c1",
        "workspace_status": "active",
        "principal_status": "active",
        "rules": [{"tool_pattern": "*", "decision": "ALLOW", "reason": None}],
        "snapshot_hash": "h1",
    }
    snap = PolicySnapshot.from_context({"policy_snapshot": raw})
    assert snap is not None
    assert snap.workspace_id == "c1"
    assert snap.rules[0].tool_pattern == "*"
