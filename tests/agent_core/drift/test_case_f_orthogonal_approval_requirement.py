from __future__ import annotations

from agent_core.governance.accumulator import combine_decisions
from agent_core.governance.contracts import AllOf, PolicyDecision, PolicyOutcome, RoleApproval


def test_case_f_orthogonal_approval_requirement_conjunction():
    """Case F: Orthogonal approval requirement (Master Guide §41.1 Case F).
    
    Kịch bản:
    1. Request-time quan sát requirement: FounderApproval.
    2. Resume-time quan sát requirement: FinanceAdminApproval.
    3. Invariant: Hệ thống KHÔNG ĐƯỢC chọn 1 trong 2 theo kiểu stricter(a, b)
       (vì 2 role trực giao không có role nào "chặt hơn" role nào).
       Đại số kết hợp BẮT BUỘC dùng `AllOf` (AND cả hai predicates lại),
       yêu cầu thoả mãn CẢ HAI trừ khi có bằng chứng chứng minh khác.
    """
    req_founder = RoleApproval(role="founder")
    req_finance = RoleApproval(role="finance_admin")

    decision_req = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=req_founder,
        reasons=("Initial request requires Founder sign-off",),
    )

    decision_resume = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=req_finance,
        reasons=("Current compliance requires Finance Admin sign-off",),
    )

    combined = combine_decisions(decision_req, decision_resume)

    assert combined.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert isinstance(combined.requirement, AllOf)
    assert len(combined.requirement.predicates) == 2
    assert req_founder in combined.requirement.predicates
    assert req_finance in combined.requirement.predicates
    assert len(combined.reasons) == 2
