from __future__ import annotations

from agent.governance.budget_gate import BudgetGate, BudgetQuota


def test_budget_gate_threshold_evaluation():
    """Kiểm thử Ambient Budget Gate (§35 & §43.8)."""
    gate = BudgetGate()

    quota = BudgetQuota(
        tenant_id="tenant_small_biz",
        max_tokens_per_run=10_000,
        max_cost_usd_per_run=0.50,
        hard_limit_action="DENY",
    )
    gate.set_quota("tenant_small_biz", quota)

    # 1. Chi tiêu trong hạn mức -> ALLOWED
    dec1 = gate.evaluate_budget(
        tenant_id="tenant_small_biz",
        run_id="run_b1",
        additional_tokens=2_000,
        additional_cost_usd=0.10,
    )
    assert dec1.is_allowed is True
    assert dec1.status == "ALLOWED"

    gate.record_spend("run_b1", tokens=2_000, cost_usd=0.10)

    # 2. Chi tiêu vượt token limit -> EXCEEDED_DENY
    dec2 = gate.evaluate_budget(
        tenant_id="tenant_small_biz",
        run_id="run_b1",
        additional_tokens=9_000,  # 2000 + 9000 = 11000 > 10000
    )
    assert dec2.is_allowed is False
    assert dec2.status == "EXCEEDED_DENY"
    assert "exceeds maximum allowed per run" in dec2.reason

    # 3. Chi tiêu vượt USD cost limit
    dec3 = gate.evaluate_budget(
        tenant_id="tenant_small_biz",
        run_id="run_b1",
        additional_cost_usd=0.45,  # 0.10 + 0.45 = 0.55 > 0.50
    )
    assert dec3.is_allowed is False
    assert dec3.status == "EXCEEDED_DENY"
