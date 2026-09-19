from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

# Phân loại UNSPSC chuẩn cho SaaS & IT Operations
UNSPSC_DICTIONARY: dict[str, str] = {
    "43231500": "Business function specific software (CRM / ERP)",
    "43232800": "Network management software (Monitoring / Observability)",
    "43232400": "Development software (CI/CD / IDE / Code hosting)",
    "43233500": "Information exchange software (Messaging / Email / Chat)",
    "43232900": "Security and protection software (Identity / Auth / Endpoint)",
    "81112000": "Data services (Cloud Hosting / Storage / Database)",
}


@dataclass(frozen=True)
class SpendItem:
    vendor_name: str
    category_unspsc: str
    category_name: str
    annual_spend: float
    renewal_month: int  # 1 - 12
    tier: str = "TIER_3"  # "TIER_1" | "TIER_2" | "TIER_3"
    has_break_glass_plan: bool = False


@dataclass(frozen=True)
class ParetoCategory:
    category_unspsc: str
    category_name: str
    total_spend: float
    spend_share: float
    cumulative_share: float
    is_pareto_core: bool  # Thuộc top 80% chi phí

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpendAnalysisReport:
    total_spend: float
    category_breakdown: tuple[ParetoCategory, ...]
    pareto_categories_count: int
    duplicate_tools_by_category: dict[str, list[str]]
    single_source_tier1_risks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_spend": round(self.total_spend, 2),
            "category_breakdown": [c.to_dict() for c in self.category_breakdown],
            "pareto_categories_count": self.pareto_categories_count,
            "duplicate_tools_by_category": self.duplicate_tools_by_category,
            "single_source_tier1_risks": list(self.single_source_tier1_risks),
        }


class ProcurementSpendAnalyzer:
    """Bộ phân tích chi tiêu SaaS và tối ưu hóa mua sắm theo chuẩn UNSPSC và Pareto 80/20.
    100% Python stdlib tất định.
    """

    @classmethod
    def analyze_spend(cls, items: list[SpendItem]) -> SpendAnalysisReport:
        if not items:
            return SpendAnalysisReport(
                total_spend=0.0,
                category_breakdown=(),
                pareto_categories_count=0,
                duplicate_tools_by_category={},
                single_source_tier1_risks=(),
            )

        total_spend = sum(i.annual_spend for i in items)
        if total_spend <= 0.0:
            return SpendAnalysisReport(
                total_spend=0.0,
                category_breakdown=(),
                pareto_categories_count=0,
                duplicate_tools_by_category={},
                single_source_tier1_risks=(),
            )

        # Gom nhóm theo danh mục
        spend_by_cat: dict[str, float] = defaultdict(float)
        cat_names: dict[str, str] = {}
        vendors_by_cat: dict[str, list[str]] = defaultdict(list)
        single_source_risks: list[str] = []

        for item in items:
            code = item.category_unspsc
            spend_by_cat[code] += item.annual_spend
            cat_names[code] = item.category_name or UNSPSC_DICTIONARY.get(code, "Other Software")
            vendors_by_cat[code].append(item.vendor_name)

            # Kiểm tra rủi ro single-source ở Tier-1
            if item.tier == "TIER_1" and not item.has_break_glass_plan:
                single_source_risks.append(
                    f"Nhà cung cấp '{item.vendor_name}' (Danh mục {cat_names[code]}, {item.annual_spend:,.0f} USD/năm) "
                    "là phụ thuộc cốt lõi Tier-1 nhưng chưa có kế hoạch dự phòng chuyển mạch (Break-glass plan)."
                )

        # Sắp xếp danh mục theo chi tiêu giảm dần để tính Pareto
        sorted_cats = sorted(spend_by_cat.items(), key=lambda x: x[1], reverse=True)

        categories: list[ParetoCategory] = []
        running_spend = 0.0

        for code, cat_spend in sorted_cats:
            running_spend += cat_spend
            share = cat_spend / total_spend
            cum_share = running_spend / total_spend
            # Nằm trong top 80% (hoặc danh mục đầu tiên đẩy vượt qua 80%)
            is_core = (cum_share - share) < 0.80

            categories.append(
                ParetoCategory(
                    category_unspsc=code,
                    category_name=cat_names[code],
                    total_spend=round(cat_spend, 2),
                    spend_share=round(share, 4),
                    cumulative_share=round(cum_share, 4),
                    is_pareto_core=is_core,
                )
            )

        pareto_count = sum(1 for c in categories if c.is_pareto_core)

        # Phát hiện công cụ trùng lặp: Danh mục có từ 2 vendor trở lên
        duplicate_tools = {
            cat_names[code]: vends for code, vends in vendors_by_cat.items() if len(vends) > 1
        }

        return SpendAnalysisReport(
            total_spend=total_spend,
            category_breakdown=tuple(categories),
            pareto_categories_count=pareto_count,
            duplicate_tools_by_category=duplicate_tools,
            single_source_tier1_risks=tuple(single_source_risks),
        )
