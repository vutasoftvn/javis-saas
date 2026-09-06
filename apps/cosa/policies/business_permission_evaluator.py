"""IA02 phần 2 — port 1:1 của
services/company/identity/services/permission-evaluator.ts sang Python, để
CosaPolicyEngine.evaluate() (đồng bộ) có thể tự áp dụng business-policy rules
đã fetch sẵn (BusinessPolicyRuleSet, xem snapshot.py) mà không cần gọi HTTP
tại thời điểm thực thi từng capability.

QUAN TRỌNG: đây là bản PORT, không phải nguồn sự thật — nguồn sự thật thật
sự vẫn là permission-evaluator.ts (CLAUDE.md quy tắc 1: "Business truth
thuộc services/*"). Nếu logic 2 bên trôi nhau (drift), services/* luôn là
đúng; port này cần được cập nhật theo, không phải ngược lại. Giữ 2 file
song song có rủi ro drift theo thời gian — đây là đánh đổi đã được chấp
nhận rõ ràng khi chọn wiring gateway-level thay vì chỉ enforce ở tầng
service TS (xem ghi chú IA02 tại apps/cosa/policies/evaluator.py).
"""

from __future__ import annotations

from apps.cosa.policies.snapshot import BusinessPermissionRule, BusinessPolicyRuleSet

__all__ = [
    "combine_permission_rules",
    "evaluate_business_policy_ruleset",
    "match_best_rule_in_role",
]


def combine_permission_rules(rules: list[BusinessPermissionRule]) -> str:
    """Port của combinePermissionRules — DENY thắng tất cả, rồi tới
    REQUIRE_APPROVAL, mặc định ALLOW. Danh sách rỗng -> DENY (fail-closed,
    khớp `!rules.length` phía TS)."""
    if not rules or any(r.effect == "DENY" for r in rules):
        return "DENY"
    if any(r.effect == "REQUIRE_APPROVAL" for r in rules):
        return "REQUIRE_APPROVAL"
    return "ALLOW"


def match_best_rule_in_role(
    rules: list[BusinessPermissionRule],
    action: str,
    facts: dict | None = None,
) -> BusinessPermissionRule | None:
    """Port của matchBestRuleInRole — quy tắc cụ thể hơn (exact match) thắng
    quy tắc wildcard (domain.* hoặc *). IA16: rule có điều kiện hạn mức/
    currency nhưng thiếu facts.amount -> fail-closed DENY (không âm thầm bỏ
    qua điều kiện như bug IA16 gốc)."""
    best_rule: BusinessPermissionRule | None = None
    best_specificity = -1  # -1: none, 0: *, 1: domain.*, 2: exact

    for rule in rules:
        key = rule.permission_key
        if not key:
            continue

        specificity = -1
        if key == action:
            specificity = 2
        elif key.endswith(".*") and action.startswith(key[:-1]):
            specificity = 1
        elif key == "*":
            specificity = 0

        if specificity > best_specificity:
            best_specificity = specificity
            best_rule = rule

    if best_rule is None:
        return None

    conditions = best_rule.conditions or {}
    requires_amount_facts = "maxAmountMinor" in conditions or "currency" in conditions
    fact_amount = (facts or {}).get("amount")

    if requires_amount_facts and not fact_amount:
        return best_rule.model_copy(update={"effect": "DENY"})

    if conditions and fact_amount:
        fact_currency = fact_amount.get("currency")
        fact_minor = int(fact_amount.get("minor") or "0")

        if conditions.get("currency") and conditions["currency"] != fact_currency:
            return best_rule.model_copy(update={"effect": "DENY"})

        max_amount_minor = conditions.get("maxAmountMinor")
        if max_amount_minor is not None and fact_minor > int(max_amount_minor):
            return best_rule.model_copy(update={"effect": "DENY"})

    return best_rule


def evaluate_business_policy_ruleset(
    rule_set: BusinessPolicyRuleSet,
    action: str,
    facts: dict | None = None,
) -> tuple[str, list[str]]:
    """Port của phần thân authorizeBusinessAction SAU bước catalog/scope
    check (2 bước đó đã xảy ra ở services/company khi rule_set được fetch —
    isKnownPermission/CROSS_WORKSPACE_ACCESS_DENIED không áp dụng ở đây vì
    action truyền vào là capability_id phía Python, không phải permission
    catalog key — xem ghi chú vocabulary mismatch tại
    business-authorization.service.ts::getBusinessPolicyRulesForMemberService).

    Trả (effect, reason_codes). Nếu KHÔNG có rule nào trong bất kỳ group nào
    khớp action, trả ("ALLOW", ["FOUNDER_DEFAULT_ALLOW"]) khi is_founder,
    else ("DENY", ["NO_MATCHING_RULE"]) — khớp đúng hành vi authorizeBusinessAction
    khi applicableRules rỗng.
    """
    applicable: list[BusinessPermissionRule] = []
    for group in rule_set.rule_groups:
        best_in_group = match_best_rule_in_role(group, action, facts)
        if best_in_group is not None:
            applicable.append(best_in_group)

    if applicable:
        combined = combine_permission_rules(applicable)
        return combined, [combined]

    if rule_set.is_founder:
        return "ALLOW", ["FOUNDER_DEFAULT_ALLOW"]

    return "DENY", ["NO_MATCHING_RULE"]
