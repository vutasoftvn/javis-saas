from __future__ import annotations

from agent_core.governance.accumulator import combine_decisions
from agent_core.governance.contracts import AllOf, PolicyDecision, PolicyOutcome, RoleApproval


def test_allow_and_allow_is_allow():
    a = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    b = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    result = combine_decisions(a, b)

    assert result.outcome == PolicyOutcome.ALLOW
    assert result.requirement is None


def test_deny_dominates_allow():
    a = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("tenant_suspended",))
    b = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    result = combine_decisions(a, b)

    assert result.outcome == PolicyOutcome.DENY


def test_deny_dominates_require_approval():
    a = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    b = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("connector_revoked",))

    result = combine_decisions(a, b)

    assert result.outcome == PolicyOutcome.DENY


def test_risk_increase_after_approval_still_requires_the_new_stricter_approval():
    # Case A của tài liệu: risk MEDIUM -> CRITICAL. Approval cũ (dưới
    # MEDIUM) không được tự động đủ cho CRITICAL.
    request_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="finance_admin"),
        reasons=("risk=MEDIUM",),
    )
    resume_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="security_officer"),
        reasons=("risk=CRITICAL",),
    )

    effective = combine_decisions(request_time, resume_time)

    assert effective.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert effective.requirement == AllOf(
        predicates=(RoleApproval(role="finance_admin"), RoleApproval(role="security_officer"))
    )


def test_risk_decrease_does_not_erase_the_original_constraint():
    # Case B của tài liệu: risk CRITICAL -> LOW. Relaxation sau đó KHÔNG
    # được xoá constraint CRITICAL đã tích luỹ từ request-time.
    request_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="founder"),
        reasons=("risk=CRITICAL",),
    )
    resume_time = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("risk=LOW",))

    effective = combine_decisions(request_time, resume_time)

    assert effective.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert effective.requirement == RoleApproval(role="founder")


def test_orthogonal_requirement_change_requires_both_not_the_longer_list():
    # Case C của tài liệu: requirement đổi trực giao (không so sánh được
    # theo severity) -> phải AND cả hai, không phải "list dài hơn thắng".
    request_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="founder"),
    )
    resume_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="finance_admin"),
    )

    effective = combine_decisions(request_time, resume_time)

    assert effective.requirement == AllOf(
        predicates=(RoleApproval(role="founder"), RoleApproval(role="finance_admin"))
    )


def test_combining_identical_requirements_does_not_double_wrap():
    a = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    b = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))

    result = combine_decisions(a, b)

    assert result.requirement == RoleApproval(role="founder")


def test_reasons_are_merged_without_duplicates_preserving_order():
    a = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("r1", "r2"))
    b = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("r2", "r3"))

    result = combine_decisions(a, b)

    assert result.reasons == ("r1", "r2", "r3")


def test_combine_is_commutative_for_outcome_and_requirement():
    a = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    b = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("connector_revoked",))

    forward = combine_decisions(a, b)
    backward = combine_decisions(b, a)

    assert forward.outcome == backward.outcome == PolicyOutcome.DENY
