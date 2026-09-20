#!/usr/bin/env python3
"""Disconfirming Evidence Checker - Anti-Confirmation-Bias Analyzer.

100% Python Standard Library. Deterministic. No LLM dependencies.
Monitors the balance of supporting vs. disconfirming searches and evidence in deep research,
dossier due diligence, and market analyses.

Rules:
  - Ratio = disconfirming / total_searches
  - PASS: ratio >= 30% (Decision-grade objective balance)
  - WARN: 20% <= ratio < 30% (Confirmation bias risk present, recommend counter-queries)
  - FAIL: ratio < 20% (HALT: Severe confirmation bias risk, cannot certify supported verdict)

Uses Antonym-Pivot heuristics to generate structured disconfirming search queries.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

MIN_RATIO = 0.30
WARN_RATIO = 0.20

# Antonym-pivot heuristics for constructing disconfirming queries
DISCONFIRMING_PIVOTS: dict[str, list[str]] = {
    "consolidating": ["diversifying", "splitting", "decentralizing", "abandoning"],
    "growing": ["shrinking", "declining", "stagnating", "slowing down"],
    "winning": ["losing", "failing", "underperforming", "losing market share"],
    "successful": ["failed", "unsuccessful", "struggling", "troubled"],
    "expanding": ["contracting", "exiting", "retreating from", "downsizing"],
    "strong": ["weak", "missing", "vulnerable", "fragile"],
    "leading": ["trailing", "lagging behind", "overtaken by"],
    "innovating": ["copying", "falling behind", "obsolete"],
    "investing in": ["divesting", "cancelling", "cutting spend on"],
    "hiring": ["laying off", "firing", "turnover at", "departures from"],
    "profitable": ["loss-making", "burning cash", "unprofitable"],
    "reliable": ["outages", "unreliable", "incident history", "security breach"],
    "adopted by": ["churned from", "rejected by", "migrating away from"],
}


@dataclass
class EvidenceBalanceReport:
    hypothesis: str
    verdict: str  # PASS, WARN, FAIL, INSUFFICIENT_DATA
    ratio: float
    rule_floor: float
    total_searches: int
    supporting: int
    disconfirming: int
    inconclusive: int
    disconfirming_needed_to_reach_floor: int
    message: str
    remediation_needed: bool
    suggested_disconfirming_queries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DisconfirmingEvidenceChecker:
    """Evaluates search/evidence balance and generates counter-hypotheses."""

    def __init__(self, min_ratio: float = MIN_RATIO, warn_ratio: float = WARN_RATIO):
        self.min_ratio = min_ratio
        self.warn_ratio = warn_ratio

    def suggest_disconfirming_queries(
        self, hypothesis: str, supporting_queries: list[str] | None = None
    ) -> list[str]:
        suggestions: list[str] = []
        hyp_lower = hypothesis.lower()

        # 1. Antonym-pivot match on hypothesis
        for pivot, antonyms in DISCONFIRMING_PIVOTS.items():
            if re.search(r"\b" + re.escape(pivot) + r"\b", hyp_lower):
                for antonym in antonyms[:2]:
                    counter = re.sub(
                        r"\b" + re.escape(pivot) + r"\b",
                        antonym,
                        hyp_lower,
                        flags=re.IGNORECASE,
                    )
                    if counter not in suggestions:
                        suggestions.append(counter)

        # 2. Antonym-pivot on supporting queries if available
        if supporting_queries:
            for q in supporting_queries:
                q_lower = q.lower()
                for pivot, antonyms in DISCONFIRMING_PIVOTS.items():
                    if re.search(r"\b" + re.escape(pivot) + r"\b", q_lower):
                        for antonym in antonyms[:1]:
                            counter = re.sub(
                                r"\b" + re.escape(pivot) + r"\b",
                                antonym,
                                q_lower,
                                flags=re.IGNORECASE,
                            )
                            if counter not in suggestions:
                                suggestions.append(counter)

        # 3. Canonical fallback counter-patterns
        if len(suggestions) < 3:
            clean_hyp = hypothesis.rstrip(".?!")
            canonical_fallbacks = [
                f"counter-evidence against {clean_hyp}",
                f"critics and objections to {clean_hyp}",
                f"failures, risks and downsides of {clean_hyp}",
                f"alternatives proving false: {clean_hyp}",
            ]
            for fb in canonical_fallbacks:
                if fb not in suggestions:
                    suggestions.append(fb)

        return suggestions[:5]

    def evaluate_balance(
        self,
        hypothesis: str,
        supporting: int,
        disconfirming: int,
        inconclusive: int = 0,
        supporting_queries: list[str] | None = None,
    ) -> EvidenceBalanceReport:
        total = supporting + disconfirming + inconclusive

        if total == 0:
            return EvidenceBalanceReport(
                hypothesis=hypothesis,
                verdict="INSUFFICIENT_DATA",
                ratio=0.0,
                rule_floor=self.min_ratio,
                total_searches=0,
                supporting=0,
                disconfirming=0,
                inconclusive=0,
                disconfirming_needed_to_reach_floor=0,
                message="Chưa có dữ liệu tìm kiếm hoặc bằng chứng được ghi nhận.",
                remediation_needed=True,
                suggested_disconfirming_queries=self.suggest_disconfirming_queries(hypothesis),
            )

        ratio = round(disconfirming / total, 4)
        needed = max(0, int(math.ceil(self.min_ratio * total) - disconfirming))

        if ratio >= self.min_ratio:
            verdict = "PASS"
            message = (
                f"Tỷ lệ bằng chứng phản biện đạt {ratio:.1%}, vượt ngưỡng tối thiểu "
                f">={self.min_ratio:.0%}. Báo cáo đạt độ khách quan chuẩn thẩm định ra quyết định."
            )
            remediation = False
            suggested: list[str] = []
        elif ratio >= self.warn_ratio:
            verdict = "WARN"
            message = (
                f"Tỷ lệ bằng chứng phản biện ({ratio:.1%}) dưới ngưỡng chuẩn >={self.min_ratio:.0%} "
                f"nhưng trên ngưỡng cảnh báo {self.warn_ratio:.0%}. Khuyến nghị thực hiện thêm "
                f"{needed} truy vấn phản biện để cân bằng góc nhìn."
            )
            remediation = True
            suggested = self.suggest_disconfirming_queries(hypothesis, supporting_queries)
        else:
            verdict = "FAIL"
            message = (
                f"Tỷ lệ bằng chứng phản biện ({ratio:.1%}) quá thấp (<{self.warn_ratio:.0%}). "
                f"Cảnh báo rủi ro thiên vị xác nhận (Confirmation Bias) rất cao. "
                f"DỪNG XUẤT BÁO CÁO và bổ sung tối thiểu {needed} truy vấn phản biện trước khi kết luận."
            )
            remediation = True
            suggested = self.suggest_disconfirming_queries(hypothesis, supporting_queries)

        return EvidenceBalanceReport(
            hypothesis=hypothesis,
            verdict=verdict,
            ratio=ratio,
            rule_floor=self.min_ratio,
            total_searches=total,
            supporting=supporting,
            disconfirming=disconfirming,
            inconclusive=inconclusive,
            disconfirming_needed_to_reach_floor=needed,
            message=message,
            remediation_needed=remediation,
            suggested_disconfirming_queries=suggested,
        )


import math


def render_human_balance(r: EvidenceBalanceReport) -> str:
    lines = [
        "=== Kiểm Tra Cân Bằng Bằng Chứng Phản Biện (Anti-Confirmation Bias) ===",
        f'Giả thuyết: "{r.hypothesis}"',
        f"Trạng thái đánh giá: [{r.verdict}]",
        f"  Tổng số truy vấn/bằng chứng:   {r.total_searches}",
        f"  - Bằng chứng ủng hộ:           {r.supporting}",
        f"  - Bằng chứng phản biện:        {r.disconfirming}",
        f"  - Bằng chứng chưa kết luận:    {r.inconclusive}",
        f"  Tỷ lệ phản biện (Disconfirming): {r.ratio:.1%} (Ngưỡng chuẩn: >={r.rule_floor:.0%})",
    ]
    if r.disconfirming_needed_to_reach_floor > 0:
        lines.append(f"  Số truy vấn phản biện cần thêm: {r.disconfirming_needed_to_reach_floor}")

    lines.append("")
    lines.append(f"Nhận xét: {r.message}")

    if r.suggested_disconfirming_queries:
        lines.append("")
        lines.append("Gợi ý truy vấn đối lập (Antonym-Pivot Suggestions):")
        for q in r.suggested_disconfirming_queries:
            lines.append(f'  - "{q}"')

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check disconfirming evidence ratio and suggest counter-queries."
    )
    parser.add_argument("--hypothesis", required=True, help="Research hypothesis statement")
    parser.add_argument(
        "--supporting", type=int, default=0, help="Number of supporting searches/evidence"
    )
    parser.add_argument(
        "--disconfirming", type=int, default=0, help="Number of disconfirming searches/evidence"
    )
    parser.add_argument(
        "--inconclusive", type=int, default=0, help="Number of inconclusive searches/evidence"
    )
    parser.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args()

    checker = DisconfirmingEvidenceChecker()
    report = checker.evaluate_balance(
        hypothesis=args.hypothesis,
        supporting=args.supporting,
        disconfirming=args.disconfirming,
        inconclusive=args.inconclusive,
    )

    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_human_balance(report))

    return 0 if report.verdict in ("PASS", "WARN") else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
