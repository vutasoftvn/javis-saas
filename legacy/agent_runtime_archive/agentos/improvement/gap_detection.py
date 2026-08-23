from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilityOutcome(BaseModel):
    capability: str
    succeeded: bool
    eval_score: float = Field(ge=0.0, le=1.0)


class CapabilityGapEvidence(BaseModel):
    failed_tasks: int
    average_eval: float


class CapabilityGap(BaseModel):
    capability: str
    evidence: CapabilityGapEvidence


class GapDetector:
    """Observe -> detect repeated failure -> identify capability gap
    (blueprint §34/§35). Thresholds are explicit constructor parameters,
    not magic numbers — callers decide how many failures and how low an
    average eval score constitutes a real gap for their context.
    """

    def __init__(self, *, min_failures: int = 3, eval_threshold: float = 0.6) -> None:
        self._min_failures = min_failures
        self._eval_threshold = eval_threshold

    def detect(self, outcomes: list[CapabilityOutcome]) -> list[CapabilityGap]:
        by_capability: dict[str, list[CapabilityOutcome]] = {}
        for outcome in outcomes:
            by_capability.setdefault(outcome.capability, []).append(outcome)

        gaps: list[CapabilityGap] = []
        for capability, records in by_capability.items():
            failed = [r for r in records if not r.succeeded]
            average_eval = sum(r.eval_score for r in records) / len(records)
            if len(failed) >= self._min_failures and average_eval < self._eval_threshold:
                gaps.append(
                    CapabilityGap(
                        capability=capability,
                        evidence=CapabilityGapEvidence(failed_tasks=len(failed), average_eval=average_eval),
                    )
                )
        return gaps
