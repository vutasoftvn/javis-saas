from __future__ import annotations

from agent.governance.contracts import PolicyOutcome
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.policies.snapshot import PolicySnapshot, TenantPolicyRule


def _ctx(snapshot: PolicySnapshot) -> dict:
    return {"policy_snapshot": snapshot.model_dump()}


def test_current_gate_denies_suspended_company():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1", workspace_status="suspended", principal_status="active", rules=[], snapshot_hash="h"
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY
    assert "suspended" in decision.reasons[0]


def test_current_gate_denies_revoked_principal():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1", workspace_status="active", principal_status="revoked", rules=[], snapshot_hash="h"
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY


def test_emergency_lock_denies_even_with_active_snapshot():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1", workspace_status="active", principal_status="active", rules=[], snapshot_hash="h"
    )
    ctx = _ctx(snapshot)
    ctx["emergency_lock"] = True
    decision = engine.evaluate("operations.task.list", {}, ctx)
    assert decision.outcome == PolicyOutcome.DENY
    assert "emergency" in decision.reasons[0].lower()


def test_tenant_override_allow_beats_hardcoded_require_approval():
    """Mặc định hardcode: capability chứa 'payout' -> REQUIRE_APPROVAL. Tenant
    tự cấu hình ALLOW cho đúng pattern này phải thắng — theo §29.3 mục 1."""
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[TenantPolicyRule(tool_pattern="finance.payout.*", decision="ALLOW", reason="pre-approved vendor")],
        snapshot_hash="h",
    )
    decision = engine.evaluate("finance.payout.execute", {"amount": 500}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.ALLOW
    assert decision.reasons[0] == "pre-approved vendor"


def test_tenant_override_deny_beats_hardcoded_allow():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[TenantPolicyRule(tool_pattern="operations.task.list", decision="DENY", reason="frozen")],
        snapshot_hash="h",
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY
    assert decision.reasons[0] == "frozen"


def test_no_tenant_rule_falls_back_to_hardcoded_default():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1", workspace_status="active", principal_status="active", rules=[], snapshot_hash="h"
    )
    decision = engine.evaluate("finance.payout.execute", {"amount": 20000}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert decision.requirement.role == "founder"


def test_no_snapshot_falls_back_to_legacy_flat_context_keys():
    """Tương thích ngược: context cũ (không qua snapshot) vẫn hoạt động."""
    engine = CosaPolicyEngine()
    decision = engine.evaluate("operations.task.list", {}, {"tenant_status": "suspended"})
    assert decision.outcome == PolicyOutcome.DENY
