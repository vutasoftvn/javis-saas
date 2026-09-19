from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategicOption:
    id: str
    title: str
    description: str
    scores: dict[str, float]  # criterion_id -> score (0.0 - 10.0)
    reversibility: str  # "high" | "medium" | "low"
    second_order_effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationCriterion:
    id: str
    label: str
    weight: float  # e.g. 0.3 (sum of weights should ideally be 1.0)


class StrategyAnalyzer:
    """Công cụ phân tích phương án chiến lược định lượng bằng ma trận trọng số.
    Hỗ trợ kỹ thuật Tree of Thought (ToT): upside, downside, reversibility, second-order effects.
    """

    @staticmethod
    def score_options(
        options: list[StrategicOption],
        criteria: list[EvaluationCriterion],
    ) -> list[dict[str, Any]]:
        """Tính điểm có trọng số cho từng phương án và xếp hạng."""
        total_weight = sum(c.weight for c in criteria)
        if total_weight <= 0:
            raise ValueError("Tổng trọng số của các tiêu chí phải lớn hơn 0")

        results: list[dict[str, Any]] = []
        for opt in options:
            weighted_sum = 0.0
            breakdown: dict[str, float] = {}
            for crit in criteria:
                raw_score = opt.scores.get(crit.id, 0.0)
                norm_weight = crit.weight / total_weight
                contrib = raw_score * norm_weight
                weighted_sum += contrib
                breakdown[crit.label] = round(raw_score, 2)

            results.append(
                {
                    "option_id": opt.id,
                    "title": opt.title,
                    "description": opt.description,
                    "weighted_score": round(weighted_sum, 2),
                    "reversibility": opt.reversibility,
                    "second_order_effects": list(opt.second_order_effects),
                    "breakdown": breakdown,
                }
            )

        # Sắp xếp từ điểm cao xuống thấp
        results.sort(key=lambda x: float(x["weighted_score"]), reverse=True)
        for rank, res in enumerate(results, start=1):
            res["rank"] = rank

        return results


class FinancialScenarioAnalyzer:
    """Mô hình hóa kịch bản tài chính đa chiều (Base / Bull / Bear) cho Founder/CEO.
    Tính toán số tháng runway, thời điểm cạn vốn và mốc kích hoạt gọi vốn.
    """

    @staticmethod
    def calculate_weeks_of_runway(
        current_cash: float,
        weekly_burn: float,
        weekly_revenue: float = 0.0,
    ) -> float:
        """Tính số tuần runway sinh tồn dựa trên burn rate và doanh thu mỗi tuần theo chuẩn 12WY."""
        if weekly_burn < 0:
            raise ValueError("weekly_burn không được là số âm")
        net_weekly_burn = max(0.0, weekly_burn - weekly_revenue)
        if net_weekly_burn == 0:
            return float("inf")
        return round(current_cash / net_weekly_burn, 1)

    @staticmethod
    def model_weekly_scenarios(
        current_cash: float,
        weekly_burn: float,
        weekly_revenue: float = 0.0,
        weekly_growth_pct: float = 0.0,
        forecast_weeks: int = 48,  # 4 chu kỳ 12WY (tương đương 48 tuần)
    ) -> dict[str, Any]:
        """Mô phỏng kịch bản dòng tiền và runway theo tuần chuẩn 12WY."""
        if weekly_burn < 0:
            raise ValueError("weekly_burn không được là số âm")

        def _simulate_weekly(burn_mult: float, growth_mult: float) -> dict[str, Any]:
            cash = current_cash
            burn = weekly_burn * burn_mult
            rev = weekly_revenue
            effective_growth = (weekly_growth_pct * growth_mult) / 100.0

            runway_weeks = 0
            weekly_balances: list[float] = []

            for w in range(1, forecast_weeks + 1):
                net_burn = max(0.0, burn - rev)
                cash -= net_burn
                weekly_balances.append(round(cash, 2))
                rev *= 1.0 + effective_growth

                if cash > 0:
                    runway_weeks = w
                else:
                    if runway_weeks == 0 and w == 1:
                        runway_weeks = 0
                    break

            if cash > 0:
                runway_weeks = forecast_weeks

            # Kích hoạt gọi vốn khi runway còn dưới 24 tuần (tương đương 2 chu kỳ 12WY)
            fundraising_trigger_week = max(1, runway_weeks - 24)

            return {
                "runway_weeks": runway_weeks,
                "ending_cash": round(max(0.0, cash), 2),
                "fundraising_trigger_week": fundraising_trigger_week,
                "cycle_12w_burn": round(max(0.0, burn - weekly_revenue) * 12, 2),
                "weekly_balances_sample": [
                    weekly_balances[i] for i in range(0, min(len(weekly_balances), 48), 4)
                ],
            }

        return {
            "current_cash": current_cash,
            "weekly_burn": weekly_burn,
            "weekly_revenue": weekly_revenue,
            "forecast_weeks": forecast_weeks,
            "scenarios": {
                "base": _simulate_weekly(burn_mult=1.0, growth_mult=1.0),
                "bull": _simulate_weekly(burn_mult=0.9, growth_mult=1.5),
                "bear": _simulate_weekly(burn_mult=1.2, growth_mult=0.5),
            },
        }

    @staticmethod
    def model_scenarios(
        current_cash: float,
        monthly_burn: float,
        monthly_revenue: float = 0.0,
        growth_rate_pct: float = 0.0,
        forecast_months: int = 12,
    ) -> dict[str, Any]:
        """Mô phỏng 3 kịch bản dựa trên dòng tiền hiện tại (Legacy compatibility)."""
        if monthly_burn < 0:
            raise ValueError("monthly_burn không được là số âm")

        def _simulate_path(burn_mult: float, growth_mult: float) -> dict[str, Any]:
            cash = current_cash
            burn = monthly_burn * burn_mult
            rev = monthly_revenue
            effective_growth = (growth_rate_pct * growth_mult) / 100.0

            runway_months = 0
            monthly_balances: list[float] = []

            for month in range(1, forecast_months + 1):
                net_burn = max(0.0, burn - rev)
                cash -= net_burn
                monthly_balances.append(round(cash, 2))
                rev *= 1.0 + effective_growth

                if cash > 0:
                    runway_months = month
                else:
                    if runway_months == 0 and month == 1:
                        runway_months = 0
                    break

            # Nếu sau forecast_months vẫn còn tiền
            if cash > 0:
                runway_months = forecast_months

            # Trigger gọi vốn khi runway còn dưới 6 tháng
            fundraising_needed_month = max(1, runway_months - 6)

            return {
                "runway_months": runway_months,
                "ending_cash": round(max(0.0, cash), 2),
                "fundraising_trigger_month": fundraising_needed_month,
                "projected_balances": monthly_balances[:12],
            }

        return {
            "current_cash": current_cash,
            "monthly_burn": monthly_burn,
            "monthly_revenue": monthly_revenue,
            "forecast_months": forecast_months,
            "scenarios": {
                "base": _simulate_path(burn_mult=1.0, growth_mult=1.0),
                "bull": _simulate_path(burn_mult=0.9, growth_mult=1.5),
                "bear": _simulate_path(burn_mult=1.2, growth_mult=0.5),
            },
        }


calculate_weeks_of_runway = FinancialScenarioAnalyzer.calculate_weeks_of_runway


@dataclass(frozen=True)
class TechDebtItem:
    id: str
    title: str
    category: str  # "architecture" | "code_quality" | "infrastructure" | "security" | "performance" | "ai_slop"
    severity: int  # 1 to 5 (P3=1, P2=2, P1=3, P0=4, Blocker=5)
    blast_radius: int  # 1 to 5 (số dịch vụ/phân hệ bị ảnh hưởng)
    cost_to_fix_days: float  # Số ngày công cần để xử lý (phải > 0)
    description: str = ""
    owner: str = ""


class TechDebtAnalyzer:
    """Công cụ đánh giá và sắp xếp ưu tiên danh mục nợ kỹ thuật cho CTO.
    Áp dụng công thức: Priority Score = (Severity * Blast Radius) / Cost to Fix Days.
    Phân loại hành động thành 3 cấp độ: Immediate Sprint, Next Milestone, Tracked Backlog.
    """

    @staticmethod
    def analyze_inventory(items: list[TechDebtItem]) -> dict[str, Any]:
        """Phân tích danh mục nợ kỹ thuật và phân bổ mức độ ưu tiên."""
        if not items:
            return {
                "total_items": 0,
                "total_cost_days": 0.0,
                "category_breakdown": {},
                "ranked_items": [],
                "action_buckets": {
                    "immediate_sprint": [],
                    "next_milestone": [],
                    "tracked_backlog": [],
                },
            }

        ranked_items: list[dict[str, Any]] = []
        category_costs: dict[str, float] = {}
        total_days = 0.0

        for it in items:
            if it.cost_to_fix_days <= 0:
                raise ValueError(f"cost_to_fix_days của item '{it.id}' phải lớn hơn 0")

            priority_score = (float(it.severity) * float(it.blast_radius)) / float(
                it.cost_to_fix_days
            )
            rounded_score = round(priority_score, 2)
            total_days += it.cost_to_fix_days
            category_costs[it.category] = category_costs.get(it.category, 0.0) + it.cost_to_fix_days

            ranked_items.append(
                {
                    "id": it.id,
                    "title": it.title,
                    "category": it.category,
                    "severity": it.severity,
                    "blast_radius": it.blast_radius,
                    "cost_to_fix_days": it.cost_to_fix_days,
                    "priority_score": rounded_score,
                    "owner": it.owner,
                    "description": it.description,
                }
            )

        # Sắp xếp theo priority_score giảm dần
        ranked_items.sort(key=lambda x: float(x["priority_score"]), reverse=True)

        # Phân loại vào 3 buckets:
        # - Top items (hoặc severity >= 4): immediate_sprint
        # - Next items (score >= 1.0 hoặc severity >= 3): next_milestone
        # - Còn lại: tracked_backlog
        immediate: list[dict[str, Any]] = []
        next_milestone: list[dict[str, Any]] = []
        backlog: list[dict[str, Any]] = []

        for item in ranked_items:
            if item["severity"] >= 4 or item["priority_score"] >= 2.0:
                immediate.append(item)
            elif item["severity"] >= 3 or item["priority_score"] >= 1.0:
                next_milestone.append(item)
            else:
                backlog.append(item)

        return {
            "total_items": len(items),
            "total_cost_days": round(total_days, 1),
            "category_breakdown": {k: round(v, 1) for k, v in category_costs.items()},
            "ranked_items": ranked_items,
            "action_buckets": {
                "immediate_sprint": immediate,
                "next_milestone": next_milestone,
                "tracked_backlog": backlog,
            },
        }


@dataclass(frozen=True)
class BuildVsBuyOption:
    id: str
    name: str  # Tên giải pháp: "Tự phát triển", "Nhà cung cấp A", "Agent Tự động hóa"
    option_type: str  # "build" | "buy" | "agentize"
    three_year_tco: float  # Tổng chi phí sở hữu 3 năm (License + Dev/Compute + Maint)
    scores: dict[str, float]  # criterion_id -> điểm 0.0 - 10.0
    migration_risk: str  # "low" | "medium" | "high"
    is_core_ip: bool = False  # Có thuộc sở hữu trí tuệ độc quyền cốt lõi hay không
    notes: str = ""
    tco_144_weeks: float | None = None  # Tổng chi phí sở hữu theo 144 tuần (chuẩn 12WY)


class BuildVsBuyAnalyzer:
    """Ma trận đánh giá Make vs Buy vs Agentize cho CTO.
    Quy tắc quyết định: Mặc định Buy hoặc Agentize trừ khi là Core IP hoặc không có vendor nào đạt >= 70% yêu cầu.
    """

    @staticmethod
    def evaluate(
        options: list[BuildVsBuyOption],
        criteria: list[EvaluationCriterion],
    ) -> dict[str, Any]:
        """Chấm điểm và đưa ra khuyến nghị lựa chọn kiến trúc."""
        if not options:
            raise ValueError("Cần ít nhất một phương án để đánh giá")
        total_weight = sum(c.weight for c in criteria)
        if total_weight <= 0:
            raise ValueError("Tổng trọng số tiêu chí phải lớn hơn 0")

        evaluated_options: list[dict[str, Any]] = []
        for opt in options:
            weighted_sum = 0.0
            breakdown: dict[str, float] = {}
            for crit in criteria:
                raw_score = opt.scores.get(crit.id, 0.0)
                norm_weight = crit.weight / total_weight
                weighted_sum += raw_score * norm_weight
                breakdown[crit.label] = round(raw_score, 2)

            tco = opt.tco_144_weeks if opt.tco_144_weeks is not None else opt.three_year_tco
            evaluated_options.append(
                {
                    "option_id": opt.id,
                    "name": opt.name,
                    "option_type": opt.option_type,
                    "three_year_tco": opt.three_year_tco,
                    "tco_144_weeks": tco,
                    "weighted_score": round(weighted_sum, 2),
                    "migration_risk": opt.migration_risk,
                    "is_core_ip": opt.is_core_ip,
                    "breakdown": breakdown,
                    "notes": opt.notes,
                }
            )

        evaluated_options.sort(key=lambda x: float(x["weighted_score"]), reverse=True)
        top_pick = evaluated_options[0]

        # Khuyến nghị chiến lược
        rationale: str
        if top_pick["is_core_ip"]:
            rationale = f"Khuyến nghị TỰ XÂY DỰNG ({top_pick['name']}) vì đây là Core IP chiến lược của doanh nghiệp."
        elif top_pick["option_type"] in ("buy", "agentize"):
            rationale = (
                f"Khuyến nghị {top_pick['option_type'].upper()} ({top_pick['name']}) "
                f"nhằm tối ưu thời gian ra mắt thị trường và TCO 144 tuần (${top_pick['tco_144_weeks']:,.0f})."
            )
        else:
            rationale = f"Khuyến nghị {top_pick['name']} đạt điểm tổng hợp cao nhất ({top_pick['weighted_score']}/10)."

        return {
            "top_pick": top_pick,
            "strategic_rationale": rationale,
            "ranked_options": evaluated_options,
        }


@dataclass(frozen=True)
class TeamScalingPlan:
    current_headcount: int
    target_headcount: int
    ramp_weeks_per_hire: int = 12  # Thời gian hòa nhập đạt 100% capacity (mặc định 1 chu kỳ 12WY)
    weekly_cost_per_head: float = (
        1250.0  # Chi phí lương/thưởng tuần/nhân sự ($5000/tháng ~ $1250/tuần)
    )
    hiring_fee_per_head: float = 3000.0  # Phí tuyển dụng và setup thiết bị mỗi nhân sự


class TeamScalingCalculator:
    """Mô hình hóa kế hoạch tăng trưởng đội ngũ kỹ sư theo chu kỳ 12WY cho CTO.
    Tính toán lộ trình tuyển dụng, năng suất hòa nhập (ramp latency) và chi phí theo tuần.
    """

    @staticmethod
    def calculate_trajectory(
        plan: TeamScalingPlan,
        cycles_count: int = 4,  # Số chu kỳ 12WY (mặc định 4 chu kỳ = 48 tuần)
    ) -> dict[str, Any]:
        """Tính toán lộ trình bổ sung nhân sự và ngân sách qua các chu kỳ 12WY."""
        if plan.current_headcount < 0 or plan.target_headcount < plan.current_headcount:
            raise ValueError("target_headcount phải lớn hơn hoặc bằng current_headcount")
        if cycles_count <= 0:
            raise ValueError("cycles_count phải lớn hơn 0")

        total_net_hires = plan.target_headcount - plan.current_headcount
        hires_per_cycle = total_net_hires / cycles_count

        cycles_breakdown: list[dict[str, Any]] = []
        running_headcount = float(plan.current_headcount)
        cumulative_cost = 0.0

        for c in range(1, cycles_count + 1):
            new_hires_this_cycle = (
                round(hires_per_cycle)
                if c < cycles_count
                else (plan.target_headcount - int(running_headcount))
            )
            # Nhân sự mới gia nhập giữa chu kỳ đóng góp trung bình 50% capacity trong chu kỳ đầu
            effective_capacity = running_headcount + (new_hires_this_cycle * 0.5)
            cycle_payroll = effective_capacity * plan.weekly_cost_per_head * 12
            cycle_hiring_cost = new_hires_this_cycle * plan.hiring_fee_per_head
            cycle_total_cost = cycle_payroll + cycle_hiring_cost
            cumulative_cost += cycle_total_cost

            running_headcount += new_hires_this_cycle

            cycles_breakdown.append(
                {
                    "cycle_number": c,
                    "cycle_name": f"12WY Cycle {c}",
                    "start_headcount": int(running_headcount - new_hires_this_cycle),
                    "new_hires": new_hires_this_cycle,
                    "end_headcount": int(running_headcount),
                    "effective_engineering_capacity": round(effective_capacity, 1),
                    "cycle_cost": round(cycle_total_cost, 2),
                    "cumulative_cost": round(cumulative_cost, 2),
                }
            )

        return {
            "current_headcount": plan.current_headcount,
            "target_headcount": plan.target_headcount,
            "total_net_hires": total_net_hires,
            "ramp_weeks": plan.ramp_weeks_per_hire,
            "total_projected_cost": round(cumulative_cost, 2),
            "cycles": cycles_breakdown,
        }


# ==============================================================================
# EXPANDED QUANTITATIVE ANALYZERS CHO 13 C-LEVEL ADVISORS CÒN LẠI (12WY)
# ==============================================================================

# --- 1. CFO Analyzers (Tài chính & Dòng tiền) ---


def calculate_cac_payback_weeks(cac: float, arpu_weekly: float, gross_margin_pct: float) -> float:
    """Tính số tuần hoàn vốn chi phí thu hút khách hàng (CAC Payback Weeks)."""
    if cac <= 0:
        return 0.0
    weekly_margin = arpu_weekly * (gross_margin_pct / 100.0)
    if weekly_margin <= 0:
        return float("inf")
    return round(cac / weekly_margin, 1)


def model_cash_runway_stress_test(
    cash: float,
    weekly_revenue: float,
    weekly_cogs: float,
    weekly_opex: float,
    shock_factor: float = 0.3,
) -> dict[str, Any]:
    """Mô phỏng áp lực tài chính (Stress Test) khi doanh thu giảm đột ngột shock_factor (mặc định 30%)."""
    base_net_burn = (weekly_cogs + weekly_opex) - weekly_revenue
    base_runway = calculate_weeks_of_runway(cash, base_net_burn)

    stressed_revenue = weekly_revenue * (1.0 - shock_factor)
    stressed_net_burn = (weekly_cogs + weekly_opex) - stressed_revenue
    stressed_runway = calculate_weeks_of_runway(cash, stressed_net_burn)

    emergency_cost_cut_needed = (
        max(0.0, stressed_net_burn - (cash / 16.0)) if cash > 0 else stressed_net_burn
    )

    return {
        "cash_in_bank": cash,
        "base_runway_weeks": base_runway,
        "shock_factor_pct": round(shock_factor * 100, 1),
        "stressed_runway_weeks": stressed_runway,
        "runway_reduction_weeks": round(base_runway - stressed_runway, 1)
        if base_runway != float("inf")
        else 0.0,
        "emergency_weekly_cut_target": round(emergency_cost_cut_needed, 2),
        "status": "critical" if stressed_runway < 16.0 else "safe",
    }


def calculate_unit_economics_health(
    cac: float, ltv: float, weekly_churn_rate: float
) -> dict[str, Any]:
    """Đánh giá sức khỏe kinh tế đơn vị (LTV/CAC và Churn Rate)."""
    ratio = round(ltv / cac, 2) if cac > 0 else 0.0
    status = (
        "healthy"
        if ratio >= 3.0 and weekly_churn_rate <= 0.01
        else ("warning" if ratio >= 2.0 else "underwater")
    )
    return {
        "ltv_to_cac_ratio": ratio,
        "weekly_churn_rate_pct": round(weekly_churn_rate * 100, 2),
        "status": status,
        "benchmark_met": ratio >= 3.0,
    }


# --- 2. CPO Analyzers (Sản phẩm & Feature Bets) ---


def score_product_bets_rice(
    reach_weekly: int, impact: float, confidence: float, effort_weeks: float
) -> float:
    """Chấm điểm RICE chuẩn hóa theo tuần công kỹ sư (Effort in Weeks).
    Impact: 3 (Massive), 2 (High), 1 (Medium), 0.5 (Low).
    Confidence: 1.0 (High), 0.8 (Medium), 0.5 (Low).
    """
    if effort_weeks <= 0:
        raise ValueError("effort_weeks phải lớn hơn 0")
    raw_score = (reach_weekly * impact * confidence) / effort_weeks
    return round(raw_score, 2)


def calculate_feature_adoption_rate(
    active_users: int, total_target_users: int, weeks_since_launch: int
) -> dict[str, Any]:
    """Tính tỷ lệ đón nhận tính năng sau N tuần ra mắt."""
    if total_target_users <= 0:
        return {"adoption_pct": 0.0, "status": "stalled"}
    rate = (active_users / total_target_users) * 100.0
    status = "strong" if rate >= 40.0 else ("moderate" if rate >= 20.0 else "at_risk")
    return {
        "weeks_since_launch": weeks_since_launch,
        "adoption_pct": round(rate, 1),
        "status": status,
        "kill_candidate": weeks_since_launch >= 6 and rate < 15.0,
    }


def calculate_compounded_churn(monthly_churn_pct: float) -> dict[str, Any]:
    """Tính Annual Churn chính xác qua công thức lãi kép: 1 - (1 - monthly_churn)^12.
    Tránh lỗi nhân 12 thông thường (3% tháng = ~31% năm chứ không phải 36%).
    """
    if monthly_churn_pct < 0 or monthly_churn_pct > 100:
        raise ValueError("monthly_churn_pct phải nằm trong khoảng [0, 100]")
    monthly_rate = monthly_churn_pct / 100.0
    annual_rate = 1.0 - ((1.0 - monthly_rate) ** 12)
    annual_churn_pct = round(annual_rate * 100.0, 2)
    simple_multiplication_pct = round(monthly_churn_pct * 12, 2)
    compounding_difference_pp = round(simple_multiplication_pct - annual_churn_pct, 2)

    if annual_churn_pct < 10.0:
        status = "great"
    elif annual_churn_pct <= 30.0:
        status = "ok"
    else:
        status = "crisis"

    return {
        "monthly_churn_pct": monthly_churn_pct,
        "annual_churn_pct": annual_churn_pct,
        "simple_multiplication_pct": simple_multiplication_pct,
        "compounding_difference_pp": compounding_difference_pp,
        "status": status,
    }


def diagnose_saas_health_scorecard(
    metrics: dict[str, Any], stage: str = "early"
) -> dict[str, Any]:
    """Chẩn đoán sức khỏe doanh nghiệp SaaS 4 chiều:
    1. Growth & Retention (Doanh thu YoY, NRR, Churn, Quick Ratio)
    2. Unit Economics (CAC, LTV, LTV:CAC, Payback, Gross Margin)
    3. Capital Efficiency (Burn, Runway, Rule of 40, Magic Number)
    4. Strategic Position (Top 10 concentration)

    Gắn cờ cảnh báo Red Flags phân cấp: Critical, High, Medium.
    """
    red_flags: list[dict[str, str]] = []

    # 1. Growth & Retention checks
    nrr = metrics.get("nrr_pct")
    if nrr is not None and nrr < 90.0:
        red_flags.append(
            {
                "severity": "critical",
                "metric": "nrr_pct",
                "issue": "NRR < 90%: Tổn thất doanh thu từ khách hàng hiện hữu",
            }
        )
    elif nrr is not None and nrr < 100.0:
        red_flags.append(
            {
                "severity": "medium",
                "metric": "nrr_pct",
                "issue": "NRR 90-100%: Chưa có động lực mở rộng doanh thu (Expansion)",
            }
        )

    quick_ratio = metrics.get("quick_ratio")
    if quick_ratio is not None and quick_ratio < 2.0:
        red_flags.append(
            {
                "severity": "high",
                "metric": "quick_ratio",
                "issue": "Quick Ratio < 2.0: Tốc độ tăng trưởng không bù đắp kịp lượng khách rời bỏ (leaky bucket)",
            }
        )

    monthly_churn = metrics.get("monthly_churn_pct")
    if monthly_churn is not None and monthly_churn > 5.0:
        red_flags.append(
            {
                "severity": "medium",
                "metric": "monthly_churn_pct",
                "issue": "Monthly Churn > 5%: Tỷ lệ rời bỏ hàng tháng ở mức báo động",
            }
        )

    # 2. Unit Economics checks
    ltv_cac = metrics.get("ltv_to_cac")
    if ltv_cac is not None and ltv_cac < 1.5:
        red_flags.append(
            {
                "severity": "critical",
                "metric": "ltv_to_cac",
                "issue": "LTV:CAC < 1.5: Đơn vị kinh tế không bền vững, đốt tiền không hoàn vốn",
            }
        )
    elif ltv_cac is not None and ltv_cac < 3.0:
        red_flags.append(
            {
                "severity": "medium",
                "metric": "ltv_to_cac",
                "issue": "LTV:CAC 1.5 - 3.0: Biên lợi nhuận cận biên, cần tối ưu CAC hoặc nâng LTV",
            }
        )

    payback_months = metrics.get("cac_payback_months")
    if payback_months is not None and payback_months > 24.0:
        red_flags.append(
            {
                "severity": "high",
                "metric": "cac_payback_months",
                "issue": "Payback > 24 tháng: Thu hồi vốn CAC quá chậm gây áp lực dòng tiền lớn",
            }
        )

    gross_margin = metrics.get("gross_margin_pct")
    if gross_margin is not None and gross_margin < 60.0:
        red_flags.append(
            {
                "severity": "high",
                "metric": "gross_margin_pct",
                "issue": "Gross Margin < 60%: Biên lợi nhuận gộp dưới chuẩn SaaS (chuẩn 70-85%)",
            }
        )

    # 3. Capital Efficiency checks
    runway_months = metrics.get("runway_months")
    if runway_months is not None and runway_months < 6.0:
        red_flags.append(
            {
                "severity": "critical",
                "metric": "runway_months",
                "issue": "Runway < 6 tháng: Nguy cơ cạn tiền khẩn cấp, cần gọi vốn hoặc cắt giảm burn",
            }
        )
    elif runway_months is not None and runway_months < 12.0:
        red_flags.append(
            {
                "severity": "medium",
                "metric": "runway_months",
                "issue": "Runway 6 - 12 tháng: Vùng cần chuẩn bị kế hoạch tài chính",
            }
        )

    rule_of_40 = metrics.get("rule_of_40")
    if rule_of_40 is not None and rule_of_40 < 25.0:
        red_flags.append(
            {
                "severity": "high",
                "metric": "rule_of_40",
                "issue": "Rule of 40 < 25: Tăng trưởng và biên lợi nhuận cộng gộp kém hiệu quả",
            }
        )

    magic_number = metrics.get("magic_number")
    if magic_number is not None and magic_number < 0.3:
        red_flags.append(
            {
                "severity": "critical",
                "metric": "magic_number",
                "issue": "Magic Number < 0.3: Hiệu quả chi tiêu S&M rất thấp, ngừng scale để sửa GTM",
            }
        )
    elif magic_number is not None and magic_number < 0.5:
        red_flags.append(
            {
                "severity": "medium",
                "metric": "magic_number",
                "issue": "Magic Number 0.3 - 0.5: Cần tối ưu hóa chuyển đổi trước khi rót thêm ngân sách",
            }
        )

    # Phân loại trạng thái tổng thể
    has_critical = any(f["severity"] == "critical" for f in red_flags)
    high_count = sum(1 for f in red_flags if f["severity"] == "high")
    if has_critical:
        overall_status = "critical"
    elif high_count >= 2:
        overall_status = "concerning"
    elif high_count == 1 or len(red_flags) >= 2:
        overall_status = "moderate"
    else:
        overall_status = "healthy"

    return {
        "stage": stage,
        "overall_status": overall_status,
        "red_flags": red_flags,
        "red_flag_count": len(red_flags),
    }


def score_growth_experiment_ice(impact: float, confidence: float, ease: float) -> float:
    """Chấm điểm ưu tiên thử nghiệm tăng trưởng theo khung ICE: (Impact + Confidence + Ease) / 3.
    Thang điểm: 1 đến 10 cho mỗi yếu tố.
    """
    for val, name in [(impact, "impact"), (confidence, "confidence"), (ease, "ease")]:
        if val < 1.0 or val > 10.0:
            raise ValueError(f"{name} phải nằm trong khoảng từ 1.0 đến 10.0")
    return round((impact + confidence + ease) / 3.0, 2)


def calculate_viral_k_factor(
    invites_sent_per_user: float, invite_conversion_rate_pct: float
) -> dict[str, Any]:
    """Tính hệ số lan truyền K-factor = (số lời mời gửi trên mỗi user) * (tỷ lệ chuyển đổi lời mời).
    K > 1.0: Tăng trưởng theo cấp số nhân (hiếm có).
    0.3 <= K <= 0.7: Viral-assisted (giúp giảm CAC 30-70%).
    """
    if invites_sent_per_user < 0 or invite_conversion_rate_pct < 0 or invite_conversion_rate_pct > 100:
        raise ValueError("Thông số lời mời hoặc tỷ lệ chuyển đổi không hợp lệ")
    k = round(invites_sent_per_user * (invite_conversion_rate_pct / 100.0), 3)
    if k > 1.0:
        tier = "exponential"
    elif k == 1.0:
        tier = "sustainable"
    elif k >= 0.3:
        tier = "viral_assisted"
    else:
        tier = "non_viral"

    cac_reduction_pct = round(min(1.0, k) * 100.0, 1)
    return {
        "k_factor": k,
        "tier": tier,
        "estimated_cac_reduction_pct": cac_reduction_pct,
    }


def analyze_feature_investment_roi(
    dev_cost: float,
    expected_annual_value: float,
    cogs_annual: float = 0.0,
    feature_type: str = "direct_monetization",
) -> dict[str, Any]:
    """Phân tích hiệu quả đầu tư tính năng (ROI) và kiểm tra tính bền vững biên lợi nhuận.
    feature_type: 'direct_monetization', 'retention', 'conversion', 'strategic'.
    """
    if dev_cost <= 0:
        raise ValueError("dev_cost phải lớn hơn 0")
    if expected_annual_value < 0 or cogs_annual < 0:
        raise ValueError("expected_annual_value và cogs_annual không được âm")

    net_annual_value = expected_annual_value - cogs_annual
    roi = round(net_annual_value / dev_cost, 2)
    contribution_margin_pct = (
        round((net_annual_value / expected_annual_value) * 100.0, 1)
        if expected_annual_value > 0
        else 0.0
    )

    if (feature_type == "direct_monetization" and roi >= 3.0 and contribution_margin_pct >= 50.0) or (
        feature_type == "retention" and roi >= 5.0
    ):
        decision = "build_now"
    elif feature_type == "strategic" or roi >= 1.5:
        decision = "build_with_governance"
    elif roi >= 1.0:
        decision = "validate_further"
    else:
        decision = "dont_build"

    return {
        "feature_type": feature_type,
        "dev_cost": dev_cost,
        "expected_annual_value": expected_annual_value,
        "cogs_annual": cogs_annual,
        "net_annual_value": net_annual_value,
        "roi": roi,
        "contribution_margin_pct": contribution_margin_pct,
        "decision": decision,
    }


# --- 3. CMO Analyzers (Tiếp thị & Kênh tăng trưởng) ---


def calculate_blended_cac(
    marketing_spend_weekly: float, sales_spend_weekly: float, new_customers_weekly: int
) -> float:
    """Tính CAC tổng hợp hàng tuần (Blended CAC)."""
    if new_customers_weekly <= 0:
        return 0.0
    return round((marketing_spend_weekly + sales_spend_weekly) / new_customers_weekly, 2)


def model_channel_efficiency_matrix(channels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Phân loại hiệu quả kênh tiếp thị dựa trên CAC và Conversion Rate."""
    results = []
    for ch in channels:
        spend = float(ch.get("spend_weekly", 0.0))
        acquired = int(ch.get("customers_acquired_weekly", 0))
        cac = round(spend / acquired, 2) if acquired > 0 else float("inf")
        results.append(
            {
                "channel_name": ch.get("name", "unknown"),
                "weekly_spend": spend,
                "weekly_customers": acquired,
                "cac": cac,
                "efficiency": "high" if cac < float(ch.get("target_cac", 100.0)) else "low",
            }
        )
    results.sort(key=lambda x: x["cac"])
    return results


# --- 4. CRO Analyzers (Doanh thu & Phễu bán hàng) ---


def calculate_pipeline_velocity_weekly(
    qualified_deals: int, win_rate: float, acv: float, cycle_length_weeks: float
) -> float:
    """Tính tốc độ dòng chảy phễu bán hàng (Pipeline Velocity $ / tuần)."""
    if cycle_length_weeks <= 0:
        raise ValueError("cycle_length_weeks phải lớn hơn 0")
    velocity = (qualified_deals * win_rate * acv) / cycle_length_weeks
    return round(velocity, 2)


def calculate_sales_capacity_model(
    reps_count: int, quota_per_rep_weekly: float, ramp_factor: float = 0.75
) -> dict[str, Any]:
    """Tính toán dung lượng bán hàng theo tuần có tính đến hệ số hòa nhập."""
    max_capacity = reps_count * quota_per_rep_weekly
    realistic_capacity = max_capacity * ramp_factor
    return {
        "reps_count": reps_count,
        "max_weekly_capacity": round(max_capacity, 2),
        "realistic_weekly_capacity": round(realistic_capacity, 2),
    }


# --- 5. CCO Analyzers (Khách hàng & Giữ chân) ---


def calculate_nrr_grr_weekly(
    starting_arr: float, expansion: float, contraction: float, churn: float
) -> dict[str, float]:
    """Tính tỷ lệ giữ chân doanh thu ròng (NRR) và gộp (GRR)."""
    if starting_arr <= 0:
        return {"nrr_pct": 100.0, "grr_pct": 100.0}
    nrr = ((starting_arr + expansion - contraction - churn) / starting_arr) * 100.0
    grr = ((starting_arr - contraction - churn) / starting_arr) * 100.0
    return {"nrr_pct": round(nrr, 1), "grr_pct": round(grr, 1)}


def calculate_customer_health_distribution(accounts: list[dict[str, Any]]) -> dict[str, Any]:
    """Phân bổ sức khỏe tài khoản khách hàng theo 3 nhóm: Green, Yellow, Red."""
    total = len(accounts)
    if total == 0:
        return {"total": 0, "green_pct": 0.0, "yellow_pct": 0.0, "red_pct": 0.0}
    green = sum(1 for a in accounts if a.get("health_score", 0) >= 80)
    yellow = sum(1 for a in accounts if 50 <= a.get("health_score", 0) < 80)
    red = sum(1 for a in accounts if a.get("health_score", 0) < 50)
    return {
        "total": total,
        "green_pct": round((green / total) * 100, 1),
        "yellow_pct": round((yellow / total) * 100, 1),
        "red_pct": round((red / total) * 100, 1),
        "high_risk_count": red,
    }


# --- 6. COO Analyzers (Vận hành & Kỷ luật 12WY) ---


def calculate_12wy_execution_score(
    weekly_commitments_done: int, weekly_commitments_total: int
) -> float:
    """Tính điểm thực thi tuần (Weekly Execution Scorecard - Chuẩn 12WY đạt >= 85%)."""
    if weekly_commitments_total <= 0:
        return 100.0
    score = (weekly_commitments_done / weekly_commitments_total) * 100.0
    return round(score, 1)


def identify_critical_path_bottlenecks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Phát hiện các tác vụ nằm trên đường găng (critical path) có nguy cơ trễ hạn tuần 12."""
    bottlenecks = []
    for t in tasks:
        if t.get("is_blocker") or (t.get("days_delayed", 0) > 3 and t.get("is_critical_path")):
            bottlenecks.append(
                {
                    "task_id": t.get("id"),
                    "task_name": t.get("name"),
                    "delay_days": t.get("days_delayed", 0),
                    "impacted_stream": t.get("stream"),
                }
            )
    return bottlenecks


# --- 7. VPE Analyzers (Phân phối kỹ thuật & DORA Metrics) ---


def calculate_dora_score(
    deployment_freq_weekly: float,
    lead_time_hours: float,
    change_failure_pct: float,
    mttr_hours: float,
) -> dict[str, Any]:
    """Tính điểm đánh giá DORA Metrics theo chuẩn High-Performing Engineering Team."""
    is_elite = (
        deployment_freq_weekly >= 7.0
        and lead_time_hours <= 24.0
        and change_failure_pct <= 5.0
        and mttr_hours <= 1.0
    )
    is_high = (
        deployment_freq_weekly >= 1.0
        and lead_time_hours <= 168.0  # 1 tuần
        and change_failure_pct <= 15.0
        and mttr_hours <= 24.0
    )
    tier = "elite" if is_elite else ("high" if is_high else "medium_or_low")
    return {
        "tier": tier,
        "deployment_freq_weekly": deployment_freq_weekly,
        "lead_time_hours": lead_time_hours,
        "change_failure_pct": change_failure_pct,
        "mttr_hours": mttr_hours,
    }


def calculate_team_sprint_velocity_stability(sprint_velocities: list[float]) -> dict[str, float]:
    """Tính độ ổn định vận tốc sprint qua các chu kỳ (Coefficient of Variation)."""
    if not sprint_velocities:
        return {"avg_velocity": 0.0, "cv_pct": 0.0}
    avg_v = sum(sprint_velocities) / len(sprint_velocities)
    variance = sum((v - avg_v) ** 2 for v in sprint_velocities) / len(sprint_velocities)
    std_dev = variance**0.5
    cv = (std_dev / avg_v * 100.0) if avg_v > 0 else 0.0
    return {"avg_velocity": round(avg_v, 1), "stability_cv_pct": round(cv, 1)}


# --- 8. CHRO Analyzers (Nhân sự & Văn hóa) ---


def calculate_hiring_ramp_cost(
    role_salary: float, recruiter_cost: float, ramp_weeks: int = 12
) -> float:
    """Tính tổng chi phí đưa một nhân sự mới đạt năng suất 100% (Ramp Cost)."""
    weekly_salary = role_salary / 52.0
    unproductive_salary = weekly_salary * ramp_weeks * 0.5
    return round(recruiter_cost + unproductive_salary, 2)


def calculate_talent_retention_risk(key_personnel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Xác định các nhân sự then chốt có nguy cơ nghỉ việc (Flight Risk)."""
    risky = []
    for p in key_personnel:
        risk_score = p.get("flight_risk_score", 0.0)  # 0.0 to 1.0
        is_spof = p.get("is_single_point_of_failure", False)
        if risk_score >= 0.7 or (risk_score >= 0.4 and is_spof):
            risky.append(
                {
                    "name": p.get("name"),
                    "role": p.get("role"),
                    "risk_level": "critical" if is_spof else "elevated",
                    "recommended_action": "Retention talk & Knowledge transfer sprint",
                }
            )
    return risky


# --- 9. CISO Analyzers (Bảo mật & Rủi ro) ---


def calculate_security_posture_score(
    critical_cves: int,
    high_cves: int,
    unpatched_weeks_avg: float,
    mfa_coverage_pct: float,
) -> dict[str, Any]:
    """Tính điểm tư thế an ninh mạng (Security Posture Score 0-100)."""
    deduction = (critical_cves * 25.0) + (high_cves * 10.0) + (unpatched_weeks_avg * 5.0)
    mfa_penalty = max(0.0, (100.0 - mfa_coverage_pct) * 0.5)
    score = max(0.0, min(100.0, 100.0 - deduction - mfa_penalty))
    status = "secure" if score >= 80.0 else ("warning" if score >= 50.0 else "critical_risk")
    return {"posture_score": round(score, 1), "status": status}


def calculate_attack_surface_expansion(
    new_endpoints: int, third_party_integrations: int, auth_bypass_risk: bool
) -> float:
    """Tính chỉ số gia tăng bề mặt tấn công sau thay đổi kiến trúc."""
    base = float(new_endpoints) * 1.5 + float(third_party_integrations) * 5.0
    if auth_bypass_risk:
        base *= 2.0
    return round(base, 1)


# --- 10. GC Analyzers (Pháp lý & Sở hữu trí tuệ) ---


def calculate_contract_legal_risk_score(
    indemnity_cap: float, sla_penalty_pct: float, ip_reversion_clause: bool
) -> float:
    """Chấm điểm rủi ro điều khoản hợp đồng (1.0 - 10.0)."""
    risk = 2.0
    if indemnity_cap <= 0:  # Không giới hạn bồi thường
        risk += 4.0
    if sla_penalty_pct > 20.0:
        risk += 2.0
    if ip_reversion_clause:
        risk += 2.0
    return min(10.0, risk)


def audit_ip_assignment_coverage(
    employees_count: int, signed_agreements_count: int
) -> dict[str, Any]:
    """Kiểm tra tỷ lệ ký kết thỏa thuận chuyển nhượng sở hữu trí tuệ (IP Assignment)."""
    if employees_count <= 0:
        return {"coverage_pct": 100.0, "status": "compliant"}
    coverage = (signed_agreements_count / employees_count) * 100.0
    return {
        "coverage_pct": round(coverage, 1),
        "unassigned_count": max(0, employees_count - signed_agreements_count),
        "status": "compliant" if coverage == 100.0 else "non_compliant_blocking",
    }


# --- 11. CDO Analyzers (Dữ liệu & Pipeline) ---


def calculate_data_quality_score(
    completeness_pct: float, accuracy_pct: float, freshness_hours: float
) -> float:
    """Tính điểm chất lượng dữ liệu tổng hợp (0 - 100)."""
    freshness_score = max(0.0, 100.0 - (freshness_hours * 2.0))
    overall = (completeness_pct * 0.4) + (accuracy_pct * 0.4) + (freshness_score * 0.2)
    return round(overall, 1)


def calculate_data_pipeline_downtime_impact(
    weekly_downtime_hours: float, impacted_users: int
) -> dict[str, Any]:
    """Ước tính thiệt hại từ thời gian chết của pipeline dữ liệu."""
    severity = "high" if weekly_downtime_hours > 4.0 or impacted_users > 1000 else "low"
    return {
        "weekly_downtime_hours": weekly_downtime_hours,
        "impacted_users": impacted_users,
        "severity": severity,
    }


# --- 12. CAIO Analyzers (Quản trị AI & Chi phí Token) ---


def calculate_llm_cost_per_work_unit(
    input_tokens_weekly: int, output_tokens_weekly: int, price_per_million: float
) -> float:
    """Tính chi phí suy luận mô hình ngôn ngữ lớn (LLM) hàng tuần."""
    total_tokens = input_tokens_weekly + output_tokens_weekly
    cost = (total_tokens / 1_000_000.0) * price_per_million
    return round(cost, 2)


def evaluate_agent_autonomy_risk_score(
    autonomy_level: str, tool_side_effects_count: int
) -> dict[str, Any]:
    """Đánh giá mức độ rủi ro tự trị của Agent dựa trên cấp độ và số lượng side-effects."""
    level_weights = {"L1_PROPOSE": 1.0, "L2_CONFIRM": 2.5, "L3_EXECUTE": 5.0}
    weight = level_weights.get(autonomy_level, 3.0)
    risk_score = round(weight * (1.0 + tool_side_effects_count * 0.5), 1)
    return {
        "autonomy_level": autonomy_level,
        "risk_score": risk_score,
        "governance_guardrail_needed": risk_score >= 10.0,
    }


# --- 13. Chief of Staff Analyzers (Đoàn kết phòng họp & Nghị trình) ---


def calculate_deliberation_consensus_index(votes: dict[str, str]) -> float:
    """Tính chỉ số đồng thuận phòng họp HĐQT (0.0 đến 1.0)."""
    if not votes:
        return 1.0
    total = len(votes)
    tallies: dict[str, int] = {}
    for opt in votes.values():
        tallies[opt] = tallies.get(opt, 0) + 1
    top_votes = max(tallies.values())
    return round(top_votes / total, 2)


def score_meeting_actionability(dissent_count: int, binding_criteria_present: bool) -> float:
    """Chấm điểm tính khả thi hành động của biên bản họp (0 - 10)."""
    score = 6.0
    if binding_criteria_present:
        score += 3.0
    if dissent_count > 0:  # Có phản biện đa chiều
        score += 1.0
    return min(10.0, score)
