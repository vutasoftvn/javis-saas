from __future__ import annotations

from apps.cosa.policies.business_permission_evaluator import (
    combine_permission_rules,
    evaluate_business_policy_ruleset,
    match_best_rule_in_role,
)
from apps.cosa.policies.snapshot import BusinessPermissionRule, BusinessPolicyRuleSet


def _rule(permission_key: str, effect: str, **conditions) -> BusinessPermissionRule:
    return BusinessPermissionRule(
        permission_key=permission_key, effect=effect, conditions=conditions
    )


class TestCombinePermissionRules:
    def test_empty_list_is_deny(self):
        assert combine_permission_rules([]) == "DENY"

    def test_any_deny_wins(self):
        rules = [_rule("a", "ALLOW"), _rule("b", "DENY"), _rule("c", "REQUIRE_APPROVAL")]
        assert combine_permission_rules(rules) == "DENY"

    def test_require_approval_beats_allow(self):
        rules = [_rule("a", "ALLOW"), _rule("b", "REQUIRE_APPROVAL")]
        assert combine_permission_rules(rules) == "REQUIRE_APPROVAL"

    def test_all_allow(self):
        assert combine_permission_rules([_rule("a", "ALLOW")]) == "ALLOW"


class TestMatchBestRuleInRole:
    def test_exact_match_beats_wildcard(self):
        rules = [_rule("finance.*", "DENY"), _rule("finance.request.approve", "ALLOW")]
        best = match_best_rule_in_role(rules, "finance.request.approve")
        assert best is not None
        assert best.permission_key == "finance.request.approve"
        assert best.effect == "ALLOW"

    def test_domain_wildcard_matches_prefix(self):
        rules = [_rule("finance.*", "ALLOW")]
        best = match_best_rule_in_role(rules, "finance.request.approve")
        assert best is not None
        assert best.effect == "ALLOW"

    def test_global_wildcard_is_lowest_priority(self):
        rules = [_rule("*", "DENY"), _rule("finance.*", "ALLOW")]
        best = match_best_rule_in_role(rules, "finance.request.approve")
        assert best is not None
        assert best.effect == "ALLOW"

    def test_no_match_returns_none(self):
        rules = [_rule("legal.obligation.manage", "ALLOW")]
        assert match_best_rule_in_role(rules, "finance.request.approve") is None

    def test_ia16_fail_closed_when_amount_limited_rule_missing_facts(self):
        """IA16 (port từ TS) — rule có maxAmountMinor/currency nhưng
        facts.amount không truyền -> DENY, không âm thầm bỏ qua điều kiện."""
        rules = [
            _rule("finance.request.approve", "ALLOW", maxAmountMinor="5000000", currency="VND")
        ]
        best = match_best_rule_in_role(rules, "finance.request.approve", facts=None)
        assert best is not None
        assert best.effect == "DENY"

    def test_amount_within_limit_allows(self):
        rules = [
            _rule("finance.request.approve", "ALLOW", maxAmountMinor="5000000", currency="VND")
        ]
        best = match_best_rule_in_role(
            rules,
            "finance.request.approve",
            facts={"amount": {"minor": "1000000", "currency": "VND"}},
        )
        assert best is not None
        assert best.effect == "ALLOW"

    def test_amount_exceeding_limit_denies(self):
        rules = [
            _rule("finance.request.approve", "ALLOW", maxAmountMinor="5000000", currency="VND")
        ]
        best = match_best_rule_in_role(
            rules,
            "finance.request.approve",
            facts={"amount": {"minor": "9000000", "currency": "VND"}},
        )
        assert best is not None
        assert best.effect == "DENY"

    def test_currency_mismatch_denies(self):
        rules = [
            _rule("finance.request.approve", "ALLOW", maxAmountMinor="5000000", currency="VND")
        ]
        best = match_best_rule_in_role(
            rules,
            "finance.request.approve",
            facts={"amount": {"minor": "100", "currency": "USD"}},
        )
        assert best is not None
        assert best.effect == "DENY"


class TestEvaluateBusinessPolicyRuleset:
    def test_no_rule_groups_founder_default_allow(self):
        rule_set = BusinessPolicyRuleSet(is_founder=True, policy_version=1, rule_groups=[])
        effect, reasons = evaluate_business_policy_ruleset(rule_set, "finance.request.approve")
        assert effect == "ALLOW"
        assert reasons == ["FOUNDER_DEFAULT_ALLOW"]

    def test_no_rule_groups_non_founder_denies(self):
        rule_set = BusinessPolicyRuleSet(is_founder=False, policy_version=1, rule_groups=[])
        effect, reasons = evaluate_business_policy_ruleset(rule_set, "finance.request.approve")
        assert effect == "DENY"
        assert reasons == ["NO_MATCHING_RULE"]

    def test_matching_rule_across_multiple_role_groups_combines_deny(self):
        """1 group ALLOW, group khác DENY cho cùng action -> DENY thắng
        (combine_permission_rules), không phải flatten rồi chọn 1 rule tuỳ ý."""
        rule_set = BusinessPolicyRuleSet(
            is_founder=False,
            policy_version=1,
            rule_groups=[
                [_rule("finance.request.approve", "ALLOW")],
                [_rule("finance.request.approve", "DENY")],
            ],
        )
        effect, reasons = evaluate_business_policy_ruleset(rule_set, "finance.request.approve")
        assert effect == "DENY"
        assert reasons == ["DENY"]

    def test_founder_default_ignored_when_explicit_rule_matches(self):
        rule_set = BusinessPolicyRuleSet(
            is_founder=True,
            policy_version=1,
            rule_groups=[[_rule("finance.request.approve", "DENY")]],
        )
        effect, _ = evaluate_business_policy_ruleset(rule_set, "finance.request.approve")
        assert effect == "DENY"
