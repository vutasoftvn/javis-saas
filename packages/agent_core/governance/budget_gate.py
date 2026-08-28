from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["BudgetDecision", "BudgetGate", "BudgetQuota"]


class BudgetQuota(BaseModel):
    """Ngưỡng ngân sách chi tiêu token và chi phí USD theo Master Guide §35."""

    tenant_id: str
    max_tokens_per_run: int = 100_000
    max_cost_usd_per_run: float = 5.0
    max_daily_cost_usd: float = 50.0
    hard_limit_action: str = "DENY"  # "DENY" or "PAUSE_REQUIRE_APPROVAL"


class BudgetDecision(BaseModel):
    is_allowed: bool
    status: str  # "ALLOWED", "EXCEEDED_DENY", "EXCEEDED_APPROVAL_REQUIRED"
    reason: str
    current_tokens: int = 0
    current_cost_usd: float = 0.0
    quota: BudgetQuota | None = None


class BudgetGate:
    """Ambient Budget & Run-level Gate theo Master Guide §35 & §43.8.

    Quy tắc:
    - Budget là một ambient/current check, không tích luỹ vĩnh viễn vào invocation history.
    - Khi vượt ngưỡng, hệ thống từ chối hoặc tạm dừng các protected executions mới.
    """

    def __init__(self, default_quota: BudgetQuota | None = None) -> None:
        self._default_quota = default_quota or BudgetQuota(tenant_id="*")
        self._quotas: dict[str, BudgetQuota] = {}
        self._spend_records: dict[
            str, dict[str, Any]
        ] = {}  # run_id -> {"tokens": int, "cost_usd": float}

    def set_quota(self, tenant_id: str, quota: BudgetQuota) -> None:
        self._quotas[tenant_id] = quota

    def record_spend(self, run_id: str, *, tokens: int, cost_usd: float = 0.0) -> None:
        rec = self._spend_records.setdefault(run_id, {"tokens": 0, "cost_usd": 0.0})
        rec["tokens"] += tokens
        rec["cost_usd"] += cost_usd

    def evaluate_budget(
        self,
        *,
        tenant_id: str,
        run_id: str,
        additional_tokens: int = 0,
        additional_cost_usd: float = 0.0,
    ) -> BudgetDecision:
        quota = self._quotas.get(tenant_id, self._default_quota)
        current = self._spend_records.get(run_id, {"tokens": 0, "cost_usd": 0.0})

        projected_tokens = current["tokens"] + additional_tokens
        projected_cost = current["cost_usd"] + additional_cost_usd

        # 1. Check tokens hard limit
        if projected_tokens > quota.max_tokens_per_run:
            status = (
                "EXCEEDED_DENY"
                if quota.hard_limit_action == "DENY"
                else "EXCEEDED_APPROVAL_REQUIRED"
            )
            return BudgetDecision(
                is_allowed=False,
                status=status,
                reason=f"Projected tokens ({projected_tokens}) exceeds maximum allowed per run ({quota.max_tokens_per_run})",
                current_tokens=projected_tokens,
                current_cost_usd=projected_cost,
                quota=quota,
            )

        # 2. Check USD cost limit
        if projected_cost > quota.max_cost_usd_per_run:
            status = (
                "EXCEEDED_DENY"
                if quota.hard_limit_action == "DENY"
                else "EXCEEDED_APPROVAL_REQUIRED"
            )
            return BudgetDecision(
                is_allowed=False,
                status=status,
                reason=f"Projected cost (${projected_cost:.2f}) exceeds maximum allowed per run (${quota.max_cost_usd_per_run:.2f})",
                current_tokens=projected_tokens,
                current_cost_usd=projected_cost,
                quota=quota,
            )

        return BudgetDecision(
            is_allowed=True,
            status="ALLOWED",
            reason="Within budget quotas",
            current_tokens=projected_tokens,
            current_cost_usd=projected_cost,
            quota=quota,
        )
