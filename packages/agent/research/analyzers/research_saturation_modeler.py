#!/usr/bin/env python3
"""Research Saturation Modeler & Insight Linter.

100% Python Standard Library. Deterministic. No LLM dependencies.
Models user research sample sizes and saturation thresholds across two core methodologies:

  1. Usability Testing (Nielsen Model):
     - Formula: n = ceil(ln(1 - Target Coverage) / ln(1 - p))
     - Default detection rate p = 0.31 (Nielsen & Landauer 1993)
     - 5 users uncovers ~85% of usability issues in a homogeneous segment.

  2. Thematic Saturation in User Interviews (Guest et al. Model):
     - Minimum 12 in-depth interviews for homogeneous participant pools to reach thematic saturation.
     - 15+ interviews when heterogeneity or business stakes are high (Faulkner 2003).

  3. Insight Integrity Linter:
     - Enforces the hard rule: A finding derived from 1 participant is an ANECDOTE,
       never an INSIGHT. Flags generalizations made from single-participant assertions.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SaturationPlanResult:
    method: str  # usability, thematic, evaluative-coverage
    segments: int
    n_per_segment: int
    total_participants: int
    expected_coverage: float
    confidence: str  # HIGH, MODERATE, LOW
    limits_and_rationale: str
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InsightLintViolation:
    line_number: int | None
    statement: str
    participant_count: int
    classification: str  # ANECDOTE vs INSIGHT
    violation_rule: str
    suggested_correction: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InsightLintReport:
    total_claims_checked: int
    anecdote_count: int
    insight_count: int
    is_compliant: bool
    violations: list[InsightLintViolation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResearchSaturationModeler:
    """Calculates study saturation requirements and lints insight claims."""

    def plan_usability_study(
        self,
        segments: int = 1,
        detection_rate: float = 0.31,
        target_coverage: float = 0.85,
    ) -> SaturationPlanResult:
        if not (0.05 <= detection_rate < 1.0):
            raise ValueError("Per-problem detection rate must be between 0.05 and 1.0.")
        if not (0.50 <= target_coverage < 1.0):
            raise ValueError("Target coverage must be between 50% (0.50) and 99.9% (0.999).")
        if segments < 1:
            raise ValueError("Segments must be at least 1.")

        n_per_seg = math.ceil(math.log(1.0 - target_coverage) / math.log(1.0 - detection_rate))
        actual_coverage = round(1.0 - (1.0 - detection_rate) ** n_per_seg, 3)

        confidence = "HIGH" if n_per_seg >= 5 else "MODERATE"

        limits = (
            f"Theo định luật Nielsen (p={detection_rate:.2f}): {n_per_seg} người dùng/phân khúc "
            f"phát hiện ~{actual_coverage:.0%} các lỗi khả dụng. Lưu ý: Kiểm thử khả năng sử dụng "
            f"chỉ tìm ra sự tồn tại của lỗi, KHÔNG phản ánh tỷ lệ phần trăm xảy ra trong toàn quần thể."
        )

        return SaturationPlanResult(
            method="usability",
            segments=segments,
            n_per_segment=n_per_seg,
            total_participants=n_per_seg * segments,
            expected_coverage=actual_coverage,
            confidence=confidence,
            limits_and_rationale=limits,
            disclaimer="Chỉ dẫn phương pháp luận định lượng. Không tự động suy diễn tỷ lệ đại trà.",
        )

    def plan_thematic_study(
        self,
        segments: int = 1,
        stakes_high_or_heterogeneous: bool = False,
    ) -> SaturationPlanResult:
        if segments < 1:
            raise ValueError("Segments must be at least 1.")

        n_per_seg = 15 if stakes_high_or_heterogeneous else 12
        confidence = "HIGH" if n_per_seg >= 12 else "MODERATE"

        limits = (
            f"Theo chuẩn Guest et al. (2006) và Faulkner (2003): Cần tối thiểu {n_per_seg} cuộc phỏng vấn "
            f"sâu cho mỗi nhóm đồng nhất để đạt điểm bão hòa chủ đề (Thematic Saturation). "
            f"Độ bão hòa phải được quan sát thực tế khi không còn phát hiện chủ đề mới (flattening curve)."
        )

        return SaturationPlanResult(
            method="thematic",
            segments=segments,
            n_per_segment=n_per_seg,
            total_participants=n_per_seg * segments,
            expected_coverage=0.90 if n_per_seg >= 12 else 0.70,
            confidence=confidence,
            limits_and_rationale=limits,
            disclaimer="Điểm bão hòa là kết quả quan sát thực tế, không phải giả định tĩnh.",
        )

    def lint_insight_claims(self, text_or_items: list[dict[str, Any]] | str) -> InsightLintReport:
        violations: list[InsightLintViolation] = []
        total_checked = 0
        anecdotes = 0
        insights = 0

        # Generalized phrasing patterns
        broad_assertion_regex = re.compile(
            r"\b(người dùng|khách hàng|toàn bộ|phần lớn|users|customers|everyone|all users|most customers)\b",
            re.IGNORECASE,
        )

        if isinstance(text_or_items, str):
            lines = text_or_items.splitlines()
            for idx, line in enumerate(lines, start=1):
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue
                total_checked += 1

                # Check if marked as insight or claims universal truth with only 1 participant cited
                is_single = bool(
                    re.search(
                        r"\b(1\s*người|1\s*user|1\s*khách hàng|participant\s*#?1|single\s*user)\b",
                        line_str,
                        re.IGNORECASE,
                    )
                )
                claims_universal = bool(broad_assertion_regex.search(line_str))
                labeled_insight = bool(
                    re.search(
                        r"\b(insight|hiểu biết sâu sắc|kết luận|quy luật)\b",
                        line_str,
                        re.IGNORECASE,
                    )
                )

                if (is_single and (claims_universal or labeled_insight)) or (
                    labeled_insight and "1/1" in line_str
                ):
                    anecdotes += 1
                    violations.append(
                        InsightLintViolation(
                            line_number=idx,
                            statement=line_str[:120],
                            participant_count=1,
                            classification="ANECDOTE",
                            violation_rule="SINGLE_PARTICIPANT_ASSERTION",
                            suggested_correction="Đổi nhãn thành 'Anecdote' (Giai thoại cá nhân) hoặc phỏng vấn thêm để kiểm chứng sự hội tụ.",
                        )
                    )
                else:
                    insights += 1
        else:
            for item in text_or_items:
                total_checked += 1
                statement = item.get("statement", "")
                p_count = int(item.get("participant_count", 0))
                claimed_label = (item.get("label") or "").upper()

                if p_count <= 1 and claimed_label in ("INSIGHT", "FINDING", "CONCLUSION"):
                    anecdotes += 1
                    violations.append(
                        InsightLintViolation(
                            line_number=item.get("id"),
                            statement=statement,
                            participant_count=p_count,
                            classification="ANECDOTE",
                            violation_rule="SINGLE_PARTICIPANT_ASSERTION",
                            suggested_correction="Một người dùng không tạo thành Insight. Đổi nhãn thành ANECDOTE.",
                        )
                    )
                else:
                    insights += 1

        return InsightLintReport(
            total_claims_checked=total_checked,
            anecdote_count=anecdotes,
            insight_count=insights,
            is_compliant=(len(violations) == 0),
            violations=violations,
        )


def render_human_saturation(plan: SaturationPlanResult) -> str:
    lines = [
        f"=== Kế Hoạch Cỡ Mẫu Bão Hòa Nghiên Cứu ({plan.method.upper()}) ===",
        f"Số phân khúc:               {plan.segments}",
        f"Số người dùng / phân khúc:  {plan.n_per_segment} người",
        f"TỔNG SỐ NGƯỜI CẦN THAM GIA: {plan.total_participants} người",
        f"Độ bao phủ kỳ vọng:         {plan.expected_coverage:.1%}",
        f"Mức độ tin cậy:             [{plan.confidence}]",
        "",
        f"Cơ sở phương pháp luận: {plan.limits_and_rationale}",
        f"Cảnh báo: {plan.disclaimer}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan research saturation and lint insight claims."
    )
    parser.add_argument("--method", choices=["usability", "thematic"], default="usability")
    parser.add_argument("--segments", type=int, default=1)
    parser.add_argument(
        "--high-stakes", action="store_true", help="High stakes / heterogeneous pool (thematic)"
    )
    parser.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args()

    modeler = ResearchSaturationModeler()
    if args.method == "usability":
        res = modeler.plan_usability_study(segments=args.segments)
    else:
        res = modeler.plan_thematic_study(
            segments=args.segments, stakes_high_or_heterogeneous=args.high_stakes
        )

    if args.output == "json":
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(render_human_saturation(res))

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
