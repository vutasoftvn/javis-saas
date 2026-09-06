from __future__ import annotations

from agent.governance.contracts import PolicyOutcome

from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.policies.snapshot import (
    BusinessPermissionRule,
    BusinessPolicyRuleSet,
    PolicySnapshot,
    TenantPolicyRule,
)


def _ctx(snapshot: PolicySnapshot) -> dict:
    return {"policy_snapshot": snapshot.model_dump()}


def test_current_gate_denies_suspended_company():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="suspended",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY
    assert "suspended" in decision.reasons[0]


def test_current_gate_denies_revoked_principal():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="revoked",
        rules=[],
        snapshot_hash="h",
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY


def test_emergency_lock_denies_even_with_active_snapshot():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
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
        rules=[
            TenantPolicyRule(
                tool_pattern="finance.payout.*", decision="ALLOW", reason="pre-approved vendor"
            )
        ],
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
        rules=[
            TenantPolicyRule(tool_pattern="operations.task.list", decision="DENY", reason="frozen")
        ],
        snapshot_hash="h",
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY
    assert decision.reasons[0] == "frozen"


def test_no_tenant_rule_falls_back_to_hardcoded_default():
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
    )
    decision = engine.evaluate("finance.payout.execute", {"amount": 20000}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert decision.requirement.role == "founder"


def test_no_snapshot_falls_back_to_legacy_flat_context_keys():
    """Tương thích ngược: context cũ (không qua snapshot) vẫn hoạt động."""
    engine = CosaPolicyEngine()
    decision = engine.evaluate("operations.task.list", {}, {"tenant_status": "suspended"})
    assert decision.outcome == PolicyOutcome.DENY


# IA02 phần 2 — step 2b: business_policy_rules mới (core.role_permissions,
# services/company) chỉ được SIẾT thêm (DENY/REQUIRE_APPROVAL), không tự nới
# lỏng qua rule hardcode/read-only bên dưới.


def test_business_policy_deny_short_circuits_before_hardcoded_rules():
    """finance.payout.execute vốn luôn REQUIRE_APPROVAL theo hardcode — nếu
    business policy rule mới nói DENY, DENY phải thắng (siết thêm, không
    phải nới lỏng xuống REQUIRE_APPROVAL)."""
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
        business_policy_rules=BusinessPolicyRuleSet(
            is_founder=False,
            policy_version=1,
            rule_groups=[
                [BusinessPermissionRule(permission_key="finance.payout.execute", effect="DENY")]
            ],
        ),
    )
    decision = engine.evaluate("finance.payout.execute", {"amount": 500}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.DENY
    assert decision.reasons[0] == "DENY"


def test_business_policy_require_approval_short_circuits_read_only_allow():
    """operations.task.list vốn ALLOW theo hardcode read-only — business
    policy REQUIRE_APPROVAL phải thắng (siết thêm)."""
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
        business_policy_rules=BusinessPolicyRuleSet(
            is_founder=False,
            policy_version=1,
            rule_groups=[
                [
                    BusinessPermissionRule(
                        permission_key="operations.task.list", effect="REQUIRE_APPROVAL"
                    )
                ]
            ],
        ),
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL


def test_business_policy_allow_falls_through_to_hardcoded_require_approval():
    """Business policy ALLOW không được BYPASS safety net cứng — payout vẫn
    phải REQUIRE_APPROVAL từ rule hardcode phía dưới."""
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
        business_policy_rules=BusinessPolicyRuleSet(
            is_founder=False,
            policy_version=1,
            rule_groups=[
                [BusinessPermissionRule(permission_key="finance.payout.execute", effect="ALLOW")]
            ],
        ),
    )
    decision = engine.evaluate("finance.payout.execute", {"amount": 500}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL


def test_tenant_snapshot_override_still_wins_over_business_policy():
    """Step 2 (cosa.company_agent_policy override cũ) vẫn chạy TRƯỚC step 2b
    — nếu step 2 đã match, business_policy_rules không được xét tới."""
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[
            TenantPolicyRule(
                tool_pattern="finance.payout.*", decision="ALLOW", reason="pre-approved vendor"
            )
        ],
        snapshot_hash="h",
        business_policy_rules=BusinessPolicyRuleSet(
            is_founder=False,
            policy_version=1,
            rule_groups=[
                [BusinessPermissionRule(permission_key="finance.payout.execute", effect="DENY")]
            ],
        ),
    )
    decision = engine.evaluate("finance.payout.execute", {"amount": 500}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.ALLOW
    assert decision.reasons[0] == "pre-approved vendor"


def test_no_business_policy_rules_fetched_is_a_pure_no_op():
    """business_policy_rules=None (chưa fetch được / không áp dụng) không
    được tự suy diễn thành DENY — hành vi phải giống hệt trước khi có step 2b."""
    engine = CosaPolicyEngine()
    snapshot = PolicySnapshot(
        workspace_id="c1",
        workspace_status="active",
        principal_status="active",
        rules=[],
        snapshot_hash="h",
    )
    decision = engine.evaluate("operations.task.list", {}, _ctx(snapshot))
    assert decision.outcome == PolicyOutcome.ALLOW
