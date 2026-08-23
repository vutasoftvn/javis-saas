from __future__ import annotations

from pydantic import BaseModel

from agent_core.governance.contracts import AllOf, ApprovalRequirement, PolicyDecision, PolicyOutcome

_OUTCOME_RANK: dict[PolicyOutcome, int] = {
    PolicyOutcome.ALLOW: 0,
    PolicyOutcome.REQUIRE_APPROVAL: 1,
    PolicyOutcome.DENY: 2,
}


def combine_decisions(a: PolicyDecision, b: PolicyDecision) -> PolicyDecision:
    """Temporal conjunction (`G_a ∧ G_b`) của 2 PolicyDecision, tái dùng
    đúng lattice DENY > REQUIRE_APPROVAL > ALLOW đã có trong
    agentos/core/policy.py::evaluate_access() — chỉ mở rộng áp dụng theo
    trục thời gian (request-time ∧ resume-time) thay vì chỉ giữa 6
    dimension trong 1 lần gọi. KHÔNG dùng `stricter(a, b)` kiểu chọn 1
    trong 2, vì requirement có thể không so sánh được (vd FounderApproval
    vs FinanceAdminApproval không có bên nào "chặt hơn" bên nào) — phải
    AND (`AllOf`) cả hai predicate lại, không chọn 1 bên. Xem PHẦN I §2 của
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md."""
    outcome = a.outcome if _OUTCOME_RANK[a.outcome] >= _OUTCOME_RANK[b.outcome] else b.outcome
    requirement = _combine_requirements(a.requirement, b.requirement)
    reasons = tuple(dict.fromkeys((*a.reasons, *b.reasons)))
    return PolicyDecision(outcome=outcome, requirement=requirement, reasons=reasons)


def _combine_requirements(
    a: ApprovalRequirement | None, b: ApprovalRequirement | None
) -> ApprovalRequirement | None:
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    return AllOf(predicates=(a, b))


class InvocationGovernanceState(BaseModel):
    """Accumulator monotonic cho 1 invocation cụ thể, key theo
    (run_id, tool_call_id) — KHÔNG theo toàn Run, để 1 tool-call rủi ro
    không "nhiễm" constraint sang tool-call khác không liên quan trong
    cùng Run. Đối lập với Run-level governance (ambient/current, không
    monotonic) — xem PHẦN I §2.3 của tài liệu governance temporal model."""

    run_id: str
    tool_call_id: str
    accumulated: PolicyDecision

    @classmethod
    def start(cls, *, run_id: str, tool_call_id: str, initial: PolicyDecision) -> "InvocationGovernanceState":
        return cls(run_id=run_id, tool_call_id=tool_call_id, accumulated=initial)

    def accumulate(self, observation: PolicyDecision) -> "InvocationGovernanceState":
        return InvocationGovernanceState(
            run_id=self.run_id,
            tool_call_id=self.tool_call_id,
            accumulated=combine_decisions(self.accumulated, observation),
        )
