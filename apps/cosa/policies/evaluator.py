from __future__ import annotations

from typing import Any

from agent.governance.contracts import (
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)

from apps.cosa.policies.snapshot import PolicySnapshot

__all__ = ["CosaPolicyEngine"]


class CosaPolicyEngine:
    """Policy Engine chính quy cho ứng dụng COSA.

    Kiến trúc theo COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md
    §29.3 mục 1: `services/cosa` (`cosa.company_agent_policy`) giữ
    configuration/source of truth, class này giữ runtime evaluation
    semantics — không phải "hai policy engine cạnh tranh". `context`
    (populated bởi `apps/cosa/api/routes.py` trước khi gọi kernel, resolve
    qua `CosaTenantPolicyClient`) mang `PolicySnapshot` đã resolve tại
    boundary phù hợp (run-start/trước resume) — snapshot KHÔNG bị đóng băng
    cho current gate (company/principal status re-observe từ snapshot mới
    nhất mỗi lần evaluate được gọi với context mới).

    Quy tắc quản trị (evaluate order):
    0. PolicySnapshot.workspace_status/principal_status (current gate, từ
       services/cosa thật) -> DENY nếu không "active".
    1. `emergency_lock` trong context -> DENY.
    1b. Ambient key cũ (`tenant_status`/`principal_status` trần trong
        context, không qua snapshot) — giữ làm fallback tương thích ngược,
        không phải đường chính.
    2. Tenant-configured override (`PolicySnapshot.match()`) — ưu tiên TRƯỚC
       rule hardcode bên dưới nếu company đã tự cấu hình qua
       cosa.company_agent_policy (hệ thống rule tool-pattern cũ, coarse).
    2b. IA02 phần 2 — business-policy rules mới (core.role_permissions,
        services/company/identity, fine-grained theo role/member, xem
        BusinessPolicyRuleSet ở snapshot.py) — resolve sẵn tại boundary
        run-start (KHÔNG gọi HTTP đồng bộ ở đây). CHỈ short-circuit khi kết
        quả là DENY/REQUIRE_APPROVAL (governance chỉ được SIẾT thêm, không
        tự nới lỏng — CLAUDE.md quy tắc 5: "Constraint lịch sử không tự mất
        khi policy sau nới lỏng"); nếu ALLOW hoặc chưa fetch được rule set,
        rơi xuống rule hardcode bên dưới như cũ — hệ thống mới không tự ý
        bỏ qua safety net cứng đã có.
    3. Rule hardcode (fallback explicitly versioned khi tenant chưa cấu hình
       hoặc không có snapshot):
       - Action có risk = HIGH hoặc có từ khoá 'payout' / 'wire' -> REQUIRE_APPROVAL.
       - Action có từ khoá 'transaction' + amount lớn -> REQUIRE_APPROVAL.
       - Action read-only -> ALLOW.
    """

    def __init__(self, default_outcome: PolicyOutcome = PolicyOutcome.ALLOW) -> None:
        self.default_outcome = default_outcome

    def evaluate(
        self,
        capability_id: str,
        payload: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        ctx = context or {}
        snapshot = PolicySnapshot.from_context(ctx)

        # 0. Current gate từ PolicySnapshot thật (services/cosa) — re-observe
        # mỗi lần evaluate() được gọi với context mới, không đóng băng theo run.
        if snapshot is not None:
            if snapshot.workspace_status != "active":
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    reasons=(f"Tenant is {snapshot.workspace_status}",),
                )
            if snapshot.principal_status != "active":
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    reasons=(f"Principal is {snapshot.principal_status}",),
                )

        if ctx.get("emergency_lock") is True:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                reasons=("Global emergency lock is active",),
            )

        # 1b. Fallback tương thích ngược nếu chưa có snapshot thật (vd. test
        # cũ truyền thẳng tenant_status/principal_status vào context).
        if snapshot is None:
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

        # 1c. Statutory floor check (current law overrides tenant policy)
        compliance_snap = ctx.get("compliance_snapshot")
        if (
            compliance_snap is not None
            or capability_id.startswith("hr.")
            or "candidate.rank" in capability_id
            or "credit.score" in capability_id
        ):
            from apps.cosa.compliance.statutory_floor import StatutoryFloor

            floor_decision = StatutoryFloor().evaluate(capability_id, payload, compliance_snap)
            if floor_decision.is_deny:
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    reasons=floor_decision.reasons,
                )

        # 2. Tenant-configured override — trước rule hardcode.
        if snapshot is not None:
            matched = snapshot.match(capability_id)
            if matched is not None:
                if matched.decision == "ALLOW":
                    return PolicyDecision(
                        outcome=PolicyOutcome.ALLOW,
                        reasons=(
                            matched.reason or f"Tenant policy ALLOW for {matched.tool_pattern}",
                        ),
                    )
                if matched.decision == "DENY":
                    return PolicyDecision(
                        outcome=PolicyOutcome.DENY,
                        reasons=(
                            matched.reason or f"Tenant policy DENY for {matched.tool_pattern}",
                        ),
                    )
                if matched.decision == "REQUIRE_APPROVAL":
                    return PolicyDecision(
                        outcome=PolicyOutcome.REQUIRE_APPROVAL,
                        requirement=RoleApproval(role="admin"),
                        reasons=(
                            matched.reason
                            or f"Tenant policy REQUIRE_APPROVAL for {matched.tool_pattern}",
                        ),
                    )

        # 2b. IA02 phần 2 — business-policy rules mới (xem docstring class).
        if snapshot is not None and snapshot.business_policy_rules is not None:
            from apps.cosa.policies.business_permission_evaluator import (
                evaluate_business_policy_ruleset,
            )

            # KHÔNG tự dựng facts["amount"] từ payload["amount"] — capability
            # payload (vd. finance.transaction.record) chỉ có "amount" dạng
            # number THUẦN, không kèm currency, trong khi maxAmountMinor
            # condition cần Money {minor, currency} chuẩn (đơn vị minor, có
            # currency — xem parseDecimalToMoney/IA13). Đoán currency mặc
            # định (vd. VND) có thể sai lệch đơn vị 100x với ý định workspace
            # cấu hình — nguy hiểm hơn là không check. Rule có điều kiện hạn
            # mức vẫn tự fail-closed DENY khi facts=None (match_best_rule_in_role,
            # cùng hành vi IA16) — chỉ rule KHÔNG điều kiện hạn mức mới evaluate
            # được chính xác qua đường này hiện tại.
            bp_effect, bp_reasons = evaluate_business_policy_ruleset(
                snapshot.business_policy_rules, capability_id, facts=None
            )
            if bp_effect == "DENY":
                return PolicyDecision(outcome=PolicyOutcome.DENY, reasons=tuple(bp_reasons))
            if bp_effect == "REQUIRE_APPROVAL":
                return PolicyDecision(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    requirement=RoleApproval(role="admin"),
                    reasons=tuple(bp_reasons),
                )
            # ALLOW (kể cả FOUNDER_DEFAULT_ALLOW) -> rơi xuống rule hardcode
            # bên dưới, không short-circuit ALLOW ở đây.

        # 3. Rule hardcode — fallback explicitly versioned.
        # 3a. Risk check theo action và payload
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

        if capability_id == "engagement.message.send":
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                requirement=RoleApproval(role="admin"),
                reasons=("Public customer message send requires approval",),
            )

        if "transaction" in capability_id and payload.get("amount", 0) > 50000:
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                requirement=RoleApproval(role="cfo"),
                reasons=("High-value transaction record requires CFO review",),
            )

        # Read-only actions
        if capability_id.startswith("operations.task.read") or capability_id.startswith(
            "operations.task.list"
        ):
            return PolicyDecision(
                outcome=PolicyOutcome.ALLOW,
                reasons=("Read-only operations task queries are permitted",),
            )

        return PolicyDecision(outcome=self.default_outcome, reasons=("Default policy outcome",))
