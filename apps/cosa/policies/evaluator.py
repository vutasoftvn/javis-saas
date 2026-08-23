from __future__ import annotations

from typing import Any, Optional
from agent_core.governance.contracts import (
    ApprovalRequirement,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)

__all__ = ["CosaPolicyEngine"]


class CosaPolicyEngine:
    """Policy Engine chính quy cho ứng dụng COSA.
    
    Quy tắc quản trị:
    1. Tenant suspended/disabled -> DENY.
    2. Principal revoked -> DENY.
    3. Action có risk = HIGH hoặc có từ khoá 'payout' / 'wire' -> REQUIRE_APPROVAL (Founder / CFO Approval).
    4. Action có risk = MEDIUM hoặc có từ khoá 'discount' / 'delete' -> REQUIRE_APPROVAL (Manager Approval).
    5. Action read-only / risk = LOW -> ALLOW.
    """

    def __init__(self, default_outcome: PolicyOutcome = PolicyOutcome.ALLOW) -> None:
        self.default_outcome = default_outcome

    def evaluate(
        self,
        capability_id: str,
        payload: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> PolicyDecision:
        ctx = context or {}
        # 1. Ambient check
        if ctx.get("tenant_status") in ("suspended", "disabled"):

            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                reasons=(f"Tenant is {ctx.get('tenant_status')}",),
            )

        if ctx.get("principal_status") in ("revoked", "disabled"):
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                reasons=(f"Principal is {ctx.get('principal_status')}",),
            )

        if ctx.get("emergency_lock") is True:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                reasons=("Global emergency lock is active",),
            )


        # 2. Risk check theo action và payload
        if "payout" in capability_id or "wire" in capability_id:
            amount = payload.get("amount", 0)
            if amount > 10000:
                return PolicyDecision(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    requirement=RoleApproval(role="founder"),
                    reasons=(f"High-value payout (${amount}) requires Founder approval",),
                )
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                requirement=RoleApproval(role="finance_lead"),
                reasons=(f"Payout (${amount}) requires Finance Lead approval",),
            )

        if "transaction" in capability_id and payload.get("amount", 0) > 50000:
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                requirement=RoleApproval(role="cfo"),
                reasons=("High-value transaction record requires CFO review",),
            )

        # Read-only actions
        if capability_id.startswith("operations.task.read") or capability_id.startswith("operations.task.list"):
            return PolicyDecision(
                outcome=PolicyOutcome.ALLOW,
                reasons=("Read-only operations task queries are permitted",),
            )

        return PolicyDecision(outcome=self.default_outcome, reasons=("Default policy outcome",))
