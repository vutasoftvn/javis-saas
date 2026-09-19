#!/usr/bin/env python3
"""Survey Sample Planner - Statistical Sample Size and Margin of Error Calculator.

100% Python Standard Library. Deterministic.
Calculates minimum required sample sizes for market research surveys using Cochran's formula,
with finite population correction and response rate adjustments.

Formulas:
  Infinite Population:
    n0 = (Z^2 * p * (1 - p)) / (e^2)

  Finite Population Correction (when population N is known):
    n = n0 / (1 + (n0 - 1) / N)

  Response Rate Multiplier:
    invites_needed = ceil(n / response_rate)

  Margin of Error given observed sample size n:
    e = Z * sqrt((p * (1 - p)) / n)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

Z_VALUES: Dict[float, float] = {
    0.90: 1.645,
    0.95: 1.960,
    0.99: 2.576,
}


@dataclass
class SurveySamplePlan:
    confidence_level: float
    z_score: float
    margin_of_error: float
    proportion: float
    population_size: Optional[int]
    is_finite: bool
    recommended_sample_size: int
    estimated_response_rate: float
    invites_needed: int
    segments: int
    total_invites_across_segments: int
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SurveySamplePlanner:
    """Calculates statistical sample sizes and margin of error for quantitative surveys."""

    def __init__(self, default_confidence: float = 0.95, default_proportion: float = 0.50):
        if default_confidence not in Z_VALUES:
            raise ValueError(f"Supported confidence levels are: {list(Z_VALUES.keys())}")
        self.default_confidence = default_confidence
        self.default_proportion = default_proportion

    def plan_sample(
        self,
        margin_of_error: float = 0.05,
        confidence_level: Optional[float] = None,
        population_size: Optional[int] = None,
        proportion: Optional[float] = None,
        response_rate: float = 0.15,
        segments: int = 1,
    ) -> SurveySamplePlan:
        conf = confidence_level or self.default_confidence
        if conf not in Z_VALUES:
            raise ValueError(f"Confidence level {conf} not supported. Use {list(Z_VALUES.keys())}")

        p = proportion if proportion is not None else self.default_proportion
        if not (0.0 < p < 1.0):
            raise ValueError("Proportion p must be between 0.0 and 1.0 (exclusive).")

        if not (0.005 <= margin_of_error <= 0.20):
            raise ValueError("Margin of error e must be between 0.5% (0.005) and 20% (0.20).")

        if not (0.01 <= response_rate <= 1.0):
            raise ValueError("Response rate must be between 1% (0.01) and 100% (1.0).")

        if segments < 1:
            raise ValueError("Segments must be at least 1.")

        z = Z_VALUES[conf]
        n0 = (z**2 * p * (1 - p)) / (margin_of_error**2)

        is_finite = False
        if population_size is not None and population_size > 0:
            is_finite = True
            n = n0 / (1.0 + (n0 - 1.0) / population_size)
            final_n = math.ceil(n)
            # Cannot exceed population size
            final_n = min(final_n, population_size)
        else:
            final_n = math.ceil(n0)

        invites_per_segment = math.ceil(final_n / response_rate)
        total_invites = invites_per_segment * segments

        notes: List[str] = [
            f"Based on Cochran's formula at {conf:.0%} confidence interval (Z={z}).",
            f"Maximum variability assumed (p={p:.2f}) giving the most conservative (safe) sample size.",
        ]
        if is_finite:
            notes.append(f"Applied Finite Population Correction for N={population_size:,}.")
        else:
            notes.append("Assumed infinite / large population (N > 50,000).")

        if segments > 1:
            notes.append(f"Plan covers {segments} distinct segments with {final_n} completes each.")

        return SurveySamplePlan(
            confidence_level=conf,
            z_score=z,
            margin_of_error=margin_of_error,
            proportion=p,
            population_size=population_size,
            is_finite=is_finite,
            recommended_sample_size=final_n,
            estimated_response_rate=response_rate,
            invites_needed=invites_per_segment,
            segments=segments,
            total_invites_across_segments=total_invites,
            notes=notes,
        )

    def calculate_margin_of_error(
        self,
        sample_size: int,
        confidence_level: Optional[float] = None,
        population_size: Optional[int] = None,
        proportion: Optional[float] = None,
    ) -> float:
        if sample_size <= 0:
            raise ValueError("Sample size must be positive.")

        conf = confidence_level or self.default_confidence
        if conf not in Z_VALUES:
            raise ValueError(f"Confidence level {conf} not supported. Use {list(Z_VALUES.keys())}")

        z = Z_VALUES[conf]
        p = proportion if proportion is not None else self.default_proportion

        moe = z * math.sqrt((p * (1 - p)) / sample_size)
        if population_size is not None and population_size > sample_size:
            fpc = math.sqrt((population_size - sample_size) / (population_size - 1))
            moe *= fpc

        return round(moe, 4)


def render_human_plan(plan: SurveySamplePlan) -> str:
    lines = [
        "=== Kế Hoạch Cỡ Mẫu Khảo Sát Định Lượng (Cochran Model) ===",
        f"Độ tin cậy: {plan.confidence_level:.0%} (Z = {plan.z_score}) | Sai số cho phép (MOE): +/-{plan.margin_of_error:.1%}",
        f"Cỡ quần thể (Population N): {plan.population_size:, if plan.population_size else 'Không giới hạn (Vô hạn)'}",
        "",
        f"-> CỠ MẪU CẦN ĐẠT (Completes):     {plan.recommended_sample_size:,} phản hồi",
        f"   Tỷ lệ phản hồi dự kiến:         {plan.estimated_response_rate:.1%}",
        f"   Số lượng lời mời cần gửi/nhóm:  {plan.invites_needed:,} invites",
    ]
    if plan.segments > 1:
        lines.append(f"   Số phân khúc khảo sát:          {plan.segments} phân khúc")
        lines.append(f"   TỔNG SỐ LỜI MỜI CẦN GỬI TOÀN BỘ: {plan.total_invites_across_segments:,} invites")

    lines.append("")
    lines.append("Ghi chú phương pháp luận:")
    for note in plan.notes:
        lines.append(f"  - {note}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate statistical survey sample size using Cochran formula.")
    parser.add_argument("--moe", type=float, default=0.05, help="Margin of error (e.g. 0.05 for 5%)")
    parser.add_argument("--conf", type=float, default=0.95, choices=[0.90, 0.95, 0.99], help="Confidence level")
    parser.add_argument("--pop", type=int, default=None, help="Population size (optional)")
    parser.add_argument("--response-rate", type=float, default=0.15, help="Expected response rate (default 15%)")
    parser.add_argument("--segments", type=int, default=1, help="Number of customer segments")
    parser.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args()

    planner = SurveySamplePlanner()
    plan = planner.plan_sample(
        margin_of_error=args.moe,
        confidence_level=args.conf,
        population_size=args.pop,
        response_rate=args.response_rate,
        segments=args.segments,
    )

    if args.output == "json":
        print(json.dumps(plan.to_dict(), indent=2))
    else:
        print(render_human_plan(plan))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
