"""Evaluation metrics and scoring functions for COSA AI Programs."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MetricScore(BaseModel):
    """Result of an individual metric evaluation."""

    metric_key: str
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    passed: bool = True
    hard_fail: bool = False
    feedback: Optional[str] = None


class ProgramEvaluationResult(BaseModel):
    """Aggregated evaluation results across all metrics for an eval case or dataset."""

    program_key: str
    program_version: str
    composite_score: float
    hard_failed: bool = False
    scores: List[MetricScore] = []
    case_count: int = 1


class AIProgramMetrics:
    """Standard evaluation metrics for COSA AI Programs."""

    @staticmethod
    def evaluate_schema_validity(output: Dict[str, Any], required_fields: List[str]) -> MetricScore:
        """Deterministic check: all required fields must exist and be non-empty."""
        missing = [f for f in required_fields if f not in output or output[f] is None]
        if missing:
            return MetricScore(
                metric_key="schema_validity",
                score=0.0,
                weight=0.2,
                passed=False,
                hard_fail=True,
                feedback=f"Missing required fields: {', '.join(missing)}",
            )
        return MetricScore(
            metric_key="schema_validity",
            score=1.0,
            weight=0.2,
            passed=True,
            hard_fail=False,
            feedback="All required fields present",
        )

    @staticmethod
    def evaluate_evidence_grounding(evidence: List[str], min_count: int = 1) -> MetricScore:
        """Check if output provides concrete factual citations/evidence."""
        count = len(evidence) if evidence else 0
        if count >= min_count:
            return MetricScore(
                metric_key="evidence_grounding",
                score=1.0,
                weight=0.3,
                passed=True,
                feedback=f"Evidence provided with {count} citations",
            )
        return MetricScore(
            metric_key="evidence_grounding",
            score=0.3,
            weight=0.3,
            passed=False,
            feedback="Insufficient evidence citations",
        )

    @staticmethod
    def evaluate_score_calibration(score_val: float) -> MetricScore:
        """Check if generated score is bounded within [0.0, 1.0]."""
        if 0.0 <= score_val <= 1.0:
            return MetricScore(
                metric_key="score_calibration",
                score=1.0,
                weight=0.1,
                passed=True,
            )
        return MetricScore(
            metric_key="score_calibration",
            score=0.0,
            weight=0.1,
            passed=False,
            hard_fail=True,
            feedback=f"Score value {score_val} is outside [0.0, 1.0]",
        )

    @staticmethod
    def evaluate_brevity_and_focus(items: List[str], max_items: int = 5) -> MetricScore:
        """Check if executive list avoids clutter and stays within cognitive focus limit."""
        if not items:
            return MetricScore(metric_key="brevity_and_focus", score=0.5, weight=0.1, passed=True)
        if len(items) <= max_items:
            return MetricScore(metric_key="brevity_and_focus", score=1.0, weight=0.1, passed=True)
        return MetricScore(
            metric_key="brevity_and_focus",
            score=0.6,
            weight=0.1,
            passed=True,
            feedback=f"Too many items ({len(items)} > {max_items}), reduced focus",
        )
