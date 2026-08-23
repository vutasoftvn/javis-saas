from __future__ import annotations

from typing import Any, Callable, Optional

__all__ = ["QualityGateDecision", "QualityGate"]


class QualityGateDecision:
    def __init__(self, passed: bool, score: float, feedback: str = "") -> None:
        self.passed = passed
        self.score = score
        self.feedback = feedback


class QualityGate:
    """Primitive đánh giá chất lượng đầu ra của specialist trước khi chuyển giao."""

    def __init__(
        self,
        evaluator_fn: Optional[Callable[[dict[str, Any]], QualityGateDecision]] = None,
        min_threshold: float = 0.7,
    ) -> None:
        self._evaluator = evaluator_fn
        self._min_threshold = min_threshold

    def evaluate(self, artifact: dict[str, Any], criteria: list[str] | None = None) -> QualityGateDecision:
        if self._evaluator:
            return self._evaluator(artifact)

        # Baseline heuristic validator
        if not artifact:
            return QualityGateDecision(passed=False, score=0.0, feedback="Output artifact is empty")

        # Kiểm tra nếu artifact chứa kết quả hợp lệ
        has_content = bool(artifact.get("output") or artifact.get("content") or artifact.get("summary"))
        score = 1.0 if has_content else 0.5
        passed = score >= self._min_threshold
        feedback = "Validation passed" if passed else "Validation failed: missing required content"
        return QualityGateDecision(passed=passed, score=score, feedback=feedback)
