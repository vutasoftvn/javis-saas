"""Gộp kết quả từng tiêu chí thành một kết luận."""

from __future__ import annotations

from collections.abc import Sequence

from agent.verification.models import CriterionResult, CriterionVerdict, Verdict

__all__ = ["combine"]


def combine(results: Sequence[CriterionResult]) -> Verdict:
    """FAIL nếu có tiêu chí bắt buộc không đạt; INCONCLUSIVE nếu có tiêu chí bắt buộc chưa rõ
    (hoặc không có kết quả nào); còn lại PASS. Tiêu chí không bắt buộc không bao giờ chặn."""
    if not results:
        return Verdict.INCONCLUSIVE
    required = [r for r in results if r.required]
    if any(r.verdict is CriterionVerdict.FAIL for r in required):
        return Verdict.FAIL
    if any(r.verdict is CriterionVerdict.UNCLEAR for r in required):
        return Verdict.INCONCLUSIVE
    return Verdict.PASS
