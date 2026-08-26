from __future__ import annotations

from pydantic import BaseModel, Field

from agent_core.evals.promotion import PromotionEvidence
from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = ["PromotionGate", "PromotionGateResult"]


class PromotionGateResult(BaseModel):
    """Kết quả kiểm tra — CHỈ là dữ liệu, không có side effect. Caller
    (services/cosa) tự quyết định làm gì với `approved`/`blocking_issues`."""

    approved: bool
    blocking_issues: list[str] = Field(default_factory=list)
    target_ref: PinnedSpecIdentity
    evidence_id: str


class PromotionGate:
    """Kiểm tra PromotionEvidence có đủ điều kiện promote hay không — CHỈ
    trả kết quả kiểm tra, KHÔNG tự activate/promote gì. Quyền quyết định
    cuối cùng (PromotionDecision) thuộc services/cosa, xem
    docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md."""

    def __init__(self, policy_version: str) -> None:
        self._policy_version = policy_version

    def check(self, evidence: PromotionEvidence, current_fingerprints: dict[str, str]) -> PromotionGateResult:
        issues: list[str] = []

        if evidence.policy_version != self._policy_version:
            issues.append(
                f"Evidence dùng policy_version '{evidence.policy_version}', "
                f"gate hiện yêu cầu '{self._policy_version}'"
            )
        if not evidence.required_eval_run_ids:
            issues.append("Evidence không có eval_run_id nào — chưa từng eval")
        if not evidence.policy_checks_passed:
            issues.append("Eval checks trong evidence chưa pass (policy_checks_passed=False)")
        if evidence.is_stale(current_fingerprints):
            issues.append("Evidence stale — fingerprint (target hoặc dependency) đã đổi kể từ khi tạo evidence")

        return PromotionGateResult(
            approved=len(issues) == 0,
            blocking_issues=issues,
            target_ref=evidence.target_ref,
            evidence_id=evidence.evidence_id,
        )
