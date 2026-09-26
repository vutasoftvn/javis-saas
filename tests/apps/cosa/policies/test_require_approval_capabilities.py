"""WGA G7 — run đánh dấu capability cần founder duyệt: policy chỉ SIẾT."""

from __future__ import annotations

from agent.governance.contracts import PolicyOutcome

from apps.cosa.policies.evaluator import REQUIRE_APPROVAL_CAPABILITIES_KEY, CosaPolicyEngine


def test_marked_capability_allow_becomes_require_approval():
    engine = CosaPolicyEngine()
    ctx = {REQUIRE_APPROVAL_CAPABILITIES_KEY: ["operations.task.list"]}
    # operations.task.list vốn ALLOW (read-only rule).
    assert engine.evaluate("operations.task.list", {}, {}).outcome == PolicyOutcome.ALLOW
    decision = engine.evaluate("operations.task.list", {}, ctx)
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert decision.requirement is not None


def test_unmarked_capability_unchanged():
    engine = CosaPolicyEngine()
    ctx = {REQUIRE_APPROVAL_CAPABILITIES_KEY: ["operations.task.create_draft"]}
    assert engine.evaluate("operations.task.list", {}, ctx).outcome == PolicyOutcome.ALLOW


def test_marking_never_loosens_deny():
    engine = CosaPolicyEngine()
    ctx = {
        REQUIRE_APPROVAL_CAPABILITIES_KEY: ["operations.task.list"],
        "emergency_lock": True,
    }
    assert engine.evaluate("operations.task.list", {}, ctx).outcome == PolicyOutcome.DENY
