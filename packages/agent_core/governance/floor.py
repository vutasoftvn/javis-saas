from __future__ import annotations

from typing import Any

from agent_core.governance.contracts import (
    ApprovalPolicy,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)

__all__ = ["capability_floor", "conjoin"]


def capability_floor(
    risk: CapabilityRisk | str,
    approval_policy: ApprovalPolicy | str = ApprovalPolicy.POLICY_DRIVEN,
) -> PolicyOutcome:
    """Xác định sàn quản trị tối thiểu (governance floor) cho capability theo rủi ro và approval policy.

    Quy tắc:
    - approval_policy == ALWAYS: bắt buộc REQUIRE_APPROVAL (không có ngoại lệ ở Batch A).
    - risk in (HIGH, CRITICAL): bắt buộc floor REQUIRE_APPROVAL.
    - Còn lại: ALLOW (cho phép policy engine quyết định tiếp).
    """
    pol = ApprovalPolicy(approval_policy) if isinstance(approval_policy, str) else approval_policy
    r = CapabilityRisk(risk) if isinstance(risk, str) else risk

    if pol == ApprovalPolicy.ALWAYS:
        return PolicyOutcome.REQUIRE_APPROVAL

    if r in (CapabilityRisk.HIGH, CapabilityRisk.CRITICAL):
        return PolicyOutcome.REQUIRE_APPROVAL

    return PolicyOutcome.ALLOW


def conjoin(
    a: PolicyDecision | PolicyOutcome | str,
    b: PolicyDecision | PolicyOutcome | str | None,
) -> PolicyDecision:
    """Kết hợp hai quyết định quản trị theo nguyên tắc nghiêm ngặt nhất (monotonic strictness).

    Độ nghiêm ngặt:
    DENY / NON_APPROVABLE > REQUIRE_APPROVAL > ALLOW.

    ApprovalPolicy.NEVER hoặc tenant ALLOW không bao giờ được phép nới lỏng floor REQUIRE_APPROVAL hoặc DENY.
    """
    dec_a = _normalize_decision(a, source="floor")
    dec_b = _normalize_decision(b, source="tenant")

    # 1. DENY có quyền ưu tiên cao nhất
    if dec_a.outcome in (PolicyOutcome.DENY, PolicyOutcome.NON_APPROVABLE) or dec_b.outcome in (
        PolicyOutcome.DENY,
        PolicyOutcome.NON_APPROVABLE,
    ):
        reasons = (*dec_a.reasons, *dec_b.reasons)
        return PolicyDecision(
            outcome=PolicyOutcome.DENY,
            reasons=reasons or ("Execution denied by conjoined policy",),
        )

    # 2. REQUIRE_APPROVAL có quyền ưu tiên thứ hai
    if (
        dec_a.outcome == PolicyOutcome.REQUIRE_APPROVAL
        or dec_b.outcome == PolicyOutcome.REQUIRE_APPROVAL
    ):
        reasons = (*dec_a.reasons, *dec_b.reasons)
        requirement = (
            dec_b.requirement
            or dec_a.requirement
            or RoleApproval(role="admin")
        )
        return PolicyDecision(
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            requirement=requirement,
            reasons=reasons or ("Action requires human approval",),
        )

    # 3. Cả hai đều ALLOW
    reasons = (*dec_a.reasons, *dec_b.reasons)
    return PolicyDecision(
        outcome=PolicyOutcome.ALLOW,
        reasons=reasons or ("Allowed by conjoined policy",),
    )


def _normalize_decision(
    val: PolicyDecision | PolicyOutcome | str | None,
    source: str = "",
) -> PolicyDecision:
    if val is None:
        return PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=(f"{source}: default allow",))
    if isinstance(val, PolicyDecision):
        return val
    if isinstance(val, PolicyOutcome):
        return PolicyDecision(outcome=val, reasons=(f"{source}: {val.value}",))
    if isinstance(val, str):
        val_str = val.upper().strip()
        if "DENY" in val_str:
            return PolicyDecision(outcome=PolicyOutcome.DENY, reasons=(f"{source}: {val_str}",))
        if "APPROVAL" in val_str:
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL, reasons=(f"{source}: {val_str}",)
            )
        return PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=(f"{source}: {val_str}",))

    return PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=(f"{source}: fallback allow",))
