#!/usr/bin/env python3
"""R&D CapEx vs OpEx Router - Decision Support for Software Development Capitalization.

100% Python Standard Library. Deterministic. No LLM dependencies.
Evaluates software R&D expenditures against International Accounting Standard (IAS 38)
and US GAAP (ASC 350-40 Internal-Use Software / ASC 985-20 Software to Be Sold).

Hard Governance Rule:
  This tool NEVER books accounting entries and NEVER auto-decides treatment.
  It provides audit-ready decision support and ROUTES each item to a named
  finance owner ("R&D Finance Controller") for final determination.

The 6 IAS 38 Criteria for Development Capitalization:
  1. technical_feasibility: Working model or proof-of-concept established.
  2. intention_to_complete: Clear organizational intent to complete the asset.
  3. ability_to_use_or_sell: Capability to deploy in production or commercialize.
  4. probable_future_benefit: Documented business case, revenue, or cost savings.
  5. adequate_resources: Technical, operational, and financial resources available.
  6. reliable_measurement: Direct cost attribution (developer hours, specific cloud dev infra).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Any

IAS38_CRITERIA: list[str] = [
    "technical_feasibility",
    "intention_to_complete",
    "ability_to_use_or_sell",
    "probable_future_benefit",
    "adequate_resources",
    "reliable_measurement",
]

CRITERIA_DESCRIPTIONS: dict[str, str] = {
    "technical_feasibility": "Tính khả thi kỹ thuật đã được chứng minh (working model / PoC thành công).",
    "intention_to_complete": "Doanh nghiệp có cam kết và ý định rõ ràng hoàn thành sản phẩm.",
    "ability_to_use_or_sell": "Có khả năng đưa sản phẩm vào vận hành nội bộ hoặc phát hành cho khách hàng.",
    "probable_future_benefit": "Dự kiến chắc chắn mang lại lợi ích kinh tế (doanh thu ARR hoặc tiết kiệm chi phí).",
    "adequate_resources": "Có đủ nhân lực, công nghệ và ngân sách để hoàn thiện tính năng.",
    "reliable_measurement": "Có hệ thống chấm công (timesheet) hoặc hóa đơn bóc tách chi phí phát triển tin cậy.",
}


@dataclass
class CostItemRouting:
    item_id: str
    name: str
    phase: str  # research, preliminary, development, maintenance, operation
    amount: float
    criteria_met: list[str]
    criteria_missing: list[str]
    verdict: str  # EXPENSE, CAPITALIZE-CANDIDATE, FINANCE-OWNER-REVIEW
    rationale: str
    named_owner: str
    accounting_standard: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RDCapexOpexReport:
    standard: str  # ifrs, usgaap
    total_spend: float
    total_expense_candidate: float
    total_capitalize_candidate: float
    total_review_needed: float
    items: list[CostItemRouting] = field(default_factory=list)
    disclaimer: str = (
        "CÔNG CỤ HỖ TRỢ RA QUYẾT ĐỊNH (DECISION SUPPORT ONLY). "
        "Không tự động hạch toán kế toán. Quyết định vốn hóa cuối cùng phải do "
        "R&D Finance Controller và Kiểm toán viên độc lập ký duyệt."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RDCapexOpexRouter:
    """Evaluates R&D software costs against capitalization criteria and routes to owners."""

    def __init__(
        self, standard: str = "ifrs", default_finance_owner: str = "R&D Finance Controller"
    ):
        self.standard = standard.lower()
        if self.standard not in ("ifrs", "usgaap"):
            raise ValueError("Standard must be 'ifrs' or 'usgaap'.")
        self.default_finance_owner = default_finance_owner

    def evaluate_item(self, item: dict[str, Any]) -> CostItemRouting:
        item_id = str(item.get("id", "UNSPECIFIED"))
        name = str(item.get("name", "Unnamed R&D Cost"))
        phase = (item.get("phase") or "research").lower()
        amount = float(item.get("amount", 0.0))
        criteria = item.get("criteria", {}) or {}

        met = [c for c in IAS38_CRITERIA if bool(criteria.get(c))]
        missing = [c for c in IAS38_CRITERIA if not bool(criteria.get(c))]

        # Accounting rules:
        # Phase 1: Research / Preliminary Project Stage -> MUST BE EXPENSED
        if phase in ("research", "preliminary", "ideation", "market-testing"):
            verdict = "EXPENSE"
            rationale = (
                "Giai đoạn nghiên cứu ý tưởng / sơ khởi (IAS 38.54 / ASC 350-40-25-1): "
                "Tuyệt đối không được vốn hóa, bắt buộc hạch toán toàn bộ vào chi phí hoạt động (OpEx)."
            )
            owner = self.default_finance_owner

        # Phase 3: Post-Implementation / Maintenance / Minor fixes -> EXPENSED
        elif phase in ("maintenance", "operation", "bugfix", "support"):
            verdict = "EXPENSE"
            rationale = (
                "Giai đoạn vận hành và bảo trì (Post-implementation): "
                "Chi phí duy trì tính năng hiện hữu hạch toán vào OpEx trong kỳ phát sinh."
            )
            owner = self.default_finance_owner

        # Phase 2: Application Development Stage
        elif phase in ("development", "software-development", "build"):
            if len(missing) == 0:
                verdict = "CAPITALIZE-CANDIDATE"
                rationale = (
                    "Giai đoạn phát triển đạt đủ 6/6 tiêu chí IAS 38 / ASC 350-40. "
                    "Ứng viên đủ điều kiện ghi nhận tài sản vô hình (CapEx). Chuyển hồ sơ kiểm toán ký duyệt."
                )
                owner = f"{self.default_finance_owner} + External Auditor Sign-off"
            else:
                verdict = "FINANCE-OWNER-REVIEW"
                missing_labels = [CRITERIA_DESCRIPTIONS.get(m, m) for m in missing]
                rationale = (
                    f"Đang trong giai đoạn phát triển nhưng còn thiếu {len(missing)} tiêu chí: "
                    f"{'; '.join(missing_labels)}. Cần rà soát hồ sơ chứng minh trước khi quyết định."
                )
                owner = self.default_finance_owner

        else:
            verdict = "FINANCE-OWNER-REVIEW"
            rationale = f"Giai đoạn không xác định ('{phase}'). Cần phân loại lại hạng mục."
            owner = self.default_finance_owner

        return CostItemRouting(
            item_id=item_id,
            name=name,
            phase=phase,
            amount=amount,
            criteria_met=met,
            criteria_missing=missing,
            verdict=verdict,
            rationale=rationale,
            named_owner=owner,
            accounting_standard=self.standard.upper(),
        )

    def route_budget(self, items: list[dict[str, Any]]) -> RDCapexOpexReport:
        evaluated = [self.evaluate_item(item) for item in items]

        total_spend = sum(i.amount for i in evaluated)
        exp = sum(i.amount for i in evaluated if i.verdict == "EXPENSE")
        cap = sum(i.amount for i in evaluated if i.verdict == "CAPITALIZE-CANDIDATE")
        rev = sum(i.amount for i in evaluated if i.verdict == "FINANCE-OWNER-REVIEW")

        return RDCapexOpexReport(
            standard=self.standard.upper(),
            total_spend=round(total_spend, 2),
            total_expense_candidate=round(exp, 2),
            total_capitalize_candidate=round(cap, 2),
            total_review_needed=round(rev, 2),
            items=evaluated,
        )


def render_human_rd_report(r: RDCapexOpexReport) -> str:
    lines = [
        f"=== Báo Cáo Định Tuyến Kế Toán R&D Phần Mềm (Chuẩn: {r.standard}) ===",
        f"Tổng ngân sách R&D:        ${r.total_spend:,.2f}",
        f"  - Chi phí OpEx (Expense): ${r.total_expense_candidate:,.2f} ({r.total_expense_candidate / r.total_spend:.1%})"
        if r.total_spend
        else "$0.00",
        f"  - Vốn hóa CapEx (Asset):  ${r.total_capitalize_candidate:,.2f} ({r.total_capitalize_candidate / r.total_spend:.1%})"
        if r.total_spend
        else "$0.00",
        f"  - Cần thẩm định thêm:     ${r.total_review_needed:,.2f}",
        "",
        "Chi tiết từng hạng mục chi phí:",
    ]
    for it in r.items:
        lines.append(f"[{it.verdict:20s}] {it.name} (${it.amount:,.2f}) - Giai đoạn: {it.phase}")
        lines.append(f"   -> Căn cứ: {it.rationale}")
        lines.append(f"   -> Chuyển giao đích danh cho: {it.named_owner}")
        lines.append("")

    lines.append(f"[!] {r.disclaimer}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate software R&D expenditures against capitalization criteria."
    )
    parser.add_argument("--standard", choices=["ifrs", "usgaap"], default="ifrs")
    parser.add_argument("--owner", default="R&D Finance Controller")
    parser.add_argument("--input", help="Path to JSON file containing R&D cost items")
    parser.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args()

    sample_items = [
        {
            "id": "RD-001",
            "name": "Nghiên cứu kiến trúc Vector Database & LLM Benchmark",
            "phase": "research",
            "amount": 15000,
            "criteria": {},
        },
        {
            "id": "RD-002",
            "name": "Phát triển module Workflow Execution Engine (đã qua PoC)",
            "phase": "development",
            "amount": 45000,
            "criteria": {
                "technical_feasibility": True,
                "intention_to_complete": True,
                "ability_to_use_or_sell": True,
                "probable_future_benefit": True,
                "adequate_resources": True,
                "reliable_measurement": True,
            },
        },
        {
            "id": "RD-003",
            "name": "Thử nghiệm tính năng Auto-Reporting mới",
            "phase": "development",
            "amount": 20000,
            "criteria": {
                "technical_feasibility": True,
                "intention_to_complete": True,
                "ability_to_use_or_sell": True,
                "probable_future_benefit": True,
                "adequate_resources": False,
                "reliable_measurement": False,
            },
        },
    ]

    items = sample_items
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            items = json.load(f)

    router = RDCapexOpexRouter(standard=args.standard, default_finance_owner=args.owner)
    report = router.route_budget(items)

    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_human_rd_report(report))

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
