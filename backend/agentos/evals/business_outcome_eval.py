# backend/agentos/evals/business_outcome_eval.py
from __future__ import annotations

from pydantic import BaseModel


class BusinessOutcomeEvalResult(BaseModel):
    metric_name: str
    target: float
    actual: float
    achievement_ratio: float
    achieved: bool


def evaluate_business_outcome(metric_name: str, *, target: float, actual: float) -> BusinessOutcomeEvalResult:
    """Business Outcome Eval (blueprint §51/§54): the final layer that
    grounds an eval in a real outcome, not just an LLM judge. Deliberately
    generic — works for the blueprint's Marketing example (CTR, conversion,
    CAC) and OKR example (KR completion) alike, since both reduce to
    "actual vs target" the same way §26's OKR key-result scoring does on
    the Encore side (services/okr/scoring.ts::computeKeyResultScore, added
    in Phase 2).
    """
    ratio = 0.0 if target <= 0 else min(actual / target, 1.0)
    return BusinessOutcomeEvalResult(
        metric_name=metric_name,
        target=target,
        actual=actual,
        achievement_ratio=ratio,
        achieved=ratio >= 1.0,
    )
