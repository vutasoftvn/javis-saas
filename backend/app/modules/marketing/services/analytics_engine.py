from typing import Dict, Any, List, Optional
import math
from sqlalchemy.orm import Session

class AnalyticsEngine:
    """
    Deterministic Analytics Engine for Marketing OS (§13, §14, §38).

    Nguyên tắc: LLM không được tính KPI (anti-pattern §39.4). Mọi con số hiển thị trên
    cockpit đều đi qua các hàm ở đây - thuần Python, không phụ thuộc thư viện ngoài,
    không phụ thuộc model. Mọi hàm phải chịu được input rỗng/0 và trả về 0.0 thay vì raise.
    """

    # ==========================================
    # Acquisition
    # ==========================================

    @staticmethod
    def calculate_ctr(clicks: float, impressions: float) -> float:
        if impressions <= 0:
            return 0.0
        return round((clicks / impressions) * 100, 2)

    @staticmethod
    def calculate_cpc(total_spend: float, clicks: float) -> float:
        if clicks <= 0:
            return 0.0
        return round(total_spend / clicks, 2)

    @staticmethod
    def calculate_cpl(total_spend: float, leads: float) -> float:
        if leads <= 0:
            return 0.0
        return round(total_spend / leads, 2)

    @staticmethod
    def calculate_cac(total_spend: float, new_customers: float) -> float:
        if new_customers <= 0:
            return 0.0
        return round(total_spend / new_customers, 2)

    # ==========================================
    # Conversion
    # ==========================================

    @staticmethod
    def calculate_conversion_rate(conversions: float, total_visitors: float) -> float:
        if total_visitors <= 0:
            return 0.0
        return round((conversions / total_visitors) * 100, 2)

    # ==========================================
    # Revenue
    # ==========================================

    @staticmethod
    def calculate_roas(revenue: float, ad_spend: float) -> float:
        if ad_spend <= 0:
            return 0.0
        return round(revenue / ad_spend, 2)

    @staticmethod
    def calculate_arpu(revenue: float, active_customers: float) -> float:
        if active_customers <= 0:
            return 0.0
        return round(revenue / active_customers, 2)

    @staticmethod
    def calculate_ltv(arpu: float, gross_margin_pct: float, monthly_churn_pct: float) -> float:
        """LTV = ARPU × biên lợi nhuận gộp ÷ tỷ lệ rời bỏ hàng tháng.

        churn = 0 nghĩa là "giữ chân vĩnh viễn" - về toán học LTV vô hạn, nên trả 0.0
        thay vì chia cho 0 hoặc bịa một con số lớn (§39.10 tránh vanity metric).
        """
        if monthly_churn_pct <= 0:
            return 0.0
        return round(arpu * (gross_margin_pct / 100.0) / (monthly_churn_pct / 100.0), 2)

    @staticmethod
    def calculate_payback_months(cac: float, arpu: float, gross_margin_pct: float) -> float:
        monthly_gross_profit = arpu * (gross_margin_pct / 100.0)
        if monthly_gross_profit <= 0:
            return 0.0
        return round(cac / monthly_gross_profit, 1)

    @staticmethod
    def calculate_ltv_cac_ratio(ltv: float, cac: float) -> float:
        if cac <= 0:
            return 0.0
        return round(ltv / cac, 2)

    # ==========================================
    # Retention
    # ==========================================

    @staticmethod
    def calculate_retention_rate(customers_start: float, customers_end: float, new_customers: float) -> float:
        if customers_start <= 0:
            return 0.0
        retained = customers_end - new_customers
        return round(max(retained, 0.0) / customers_start * 100, 2)

    @staticmethod
    def calculate_churn_rate(customers_start: float, churned: float) -> float:
        if customers_start <= 0:
            return 0.0
        return round(churned / customers_start * 100, 2)

    @staticmethod
    def calculate_nrr(starting_mrr: float, expansion_mrr: float, contraction_mrr: float, churned_mrr: float) -> float:
        """Net Revenue Retention - đo cả mở rộng lẫn suy giảm trên tập khách hàng cũ."""
        if starting_mrr <= 0:
            return 0.0
        net = starting_mrr + expansion_mrr - contraction_mrr - churned_mrr
        return round(net / starting_mrr * 100, 2)

    @staticmethod
    def calculate_grr(starting_mrr: float, contraction_mrr: float, churned_mrr: float) -> float:
        if starting_mrr <= 0:
            return 0.0
        net = starting_mrr - contraction_mrr - churned_mrr
        return round(max(net, 0.0) / starting_mrr * 100, 2)

    # ==========================================
    # Funnel (§8)
    # ==========================================

    @staticmethod
    def calculate_funnel_conversions(stage_values: List[Optional[float]]) -> List[Dict[str, Any]]:
        """Tỷ lệ chuyển đổi giữa các bước phễu.

        `None` nghĩa là bước đó CHƯA CÓ SỐ ĐO - khác hẳn với "đo được và bằng 0". Bước
        chưa có số đo trả về None và bị bỏ qua khi nối chuỗi, nếu không một bước chưa gắn
        chỉ số sẽ kéo mọi bước sau xuống 0% và bịa ra một nút thắt không có thật.
        """
        results: List[Dict[str, Any]] = []
        measured = [v for v in stage_values if v is not None]
        top = measured[0] if measured else None
        prev: Optional[float] = None

        for idx, value in enumerate(stage_values):
            if value is None:
                results.append({
                    "index": idx,
                    "value": None,
                    "step_conversion_pct": None,
                    "overall_conversion_pct": None,
                    "drop_off": None,
                })
                continue

            if prev is None:
                step = 100.0
                drop_off = 0.0
            else:
                step = round(value / prev * 100, 2) if prev > 0 else 0.0
                drop_off = round(prev - value, 2)

            results.append({
                "index": idx,
                "value": value,
                "step_conversion_pct": step,
                "overall_conversion_pct": round(value / top * 100, 2) if top else 0.0,
                "drop_off": drop_off,
            })
            prev = value

        return results

    @staticmethod
    def detect_funnel_bottleneck(stage_values: List[Optional[float]]) -> Optional[int]:
        """Chỉ số bước phễu rớt mạnh nhất - đầu vào cho Growth/CRO Agent (§19).

        Chỉ so sánh các bước đã có số đo; bước chưa gắn chỉ số không phải nút thắt mà là
        khoảng trống đo lường, phải xử lý bằng cách bổ sung dữ liệu chứ không phải tối ưu.
        """
        measured = [(idx, v) for idx, v in enumerate(stage_values) if v is not None]
        if len(measured) < 2:
            return None

        worst_idx = None
        worst_rate = None
        for position in range(1, len(measured)):
            idx, value = measured[position]
            prev = measured[position - 1][1]
            if prev <= 0:
                continue
            rate = value / prev
            if worst_rate is None or rate < worst_rate:
                worst_rate = rate
                worst_idx = idx
        return worst_idx

    # ==========================================
    # Experiment (§15)
    # ==========================================

    @staticmethod
    def evaluate_experiment(
        baseline_cvr: float,
        variant_cvr: float,
        baseline_sample: int,
        variant_sample: int,
        confidence_threshold: float = 0.95
    ) -> Dict[str, Any]:
        """
        Evaluates A/B test results using Z-test for proportions.
        """
        if baseline_sample < 30 or variant_sample < 30:
            return {
                "decision": "INCONCLUSIVE",
                "reason": "Sample size too small for statistical significance (minimum 30 per variant required).",
                "uplift_pct": round(((variant_cvr - baseline_cvr) / baseline_cvr * 100) if baseline_cvr > 0 else 0, 2),
                "z_score": 0.0,
                "p_value": 1.0,
                "statistically_significant": False,
                "baseline_cvr": baseline_cvr,
                "variant_cvr": variant_cvr,
            }

        p1 = baseline_cvr / 100.0
        p2 = variant_cvr / 100.0
        n1 = baseline_sample
        n2 = variant_sample

        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
        if p_pooled == 0 or p_pooled == 1:
            se = 0.0
        else:
            se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        z_score = (p2 - p1) / se if se > 0 else 0.0
        uplift_pct = round(((p2 - p1) / p1 * 100) if p1 > 0 else 0.0, 2)
        p_value = round(math.erfc(abs(z_score) / math.sqrt(2)), 6)

        z_critical = AnalyticsEngine._z_critical(confidence_threshold)
        if z_score >= z_critical:
            decision = "WIN"
        elif z_score <= -z_critical:
            decision = "LOSE"
        else:
            decision = "INCONCLUSIVE"

        return {
            "decision": decision,
            "z_score": round(z_score, 4),
            "p_value": p_value,
            "uplift_pct": uplift_pct,
            "baseline_cvr": baseline_cvr,
            "variant_cvr": variant_cvr,
            "confidence_threshold": confidence_threshold,
            "statistically_significant": abs(z_score) >= z_critical
        }

    @staticmethod
    def _z_critical(confidence_threshold: float) -> float:
        """Ngưỡng z hai phía cho các mức tin cậy hay dùng; mặc định về 95% nếu lạ."""
        table = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        return table.get(round(confidence_threshold, 2), 1.96)

    @staticmethod
    def evaluate_experiment_from_events(
        db: Session,
        workspace_id: int,
        experiment_id: int,
        conversion_event_type: str = "form_submitted",
        confidence_threshold: float = 0.95,
    ) -> Dict[str, Any]:
        """
        Calculates conversion rates directly from recorded WebEvents and evaluates statistical significance.
        """
        from app.modules.marketing.form_models import WebEvent

        events = db.query(WebEvent).filter(
            WebEvent.workspace_id == workspace_id,
            WebEvent.experiment_id == experiment_id,
        ).all()

        variant_a_views = set()
        variant_a_conversions = set()
        variant_b_views = set()
        variant_b_conversions = set()

        for ev in events:
            variant = (ev.variant or "").lower()
            if "variant_a" in variant or "control" in variant or variant == "a":
                if ev.event_type == "page_view":
                    variant_a_views.add(ev.visitor_id)
                elif ev.event_type == conversion_event_type:
                    variant_a_conversions.add(ev.visitor_id)
            elif "variant_b" in variant or variant == "b":
                if ev.event_type == "page_view":
                    variant_b_views.add(ev.visitor_id)
                elif ev.event_type == conversion_event_type:
                    variant_b_conversions.add(ev.visitor_id)

        sample_a = len(variant_a_views)
        conv_a = len(variant_a_conversions)
        cvr_a = (conv_a / sample_a * 100.0) if sample_a > 0 else 0.0

        sample_b = len(variant_b_views)
        conv_b = len(variant_b_conversions)
        cvr_b = (conv_b / sample_b * 100.0) if sample_b > 0 else 0.0

        eval_result = AnalyticsEngine.evaluate_experiment(
            baseline_cvr=cvr_a,
            variant_cvr=cvr_b,
            baseline_sample=sample_a,
            variant_sample=sample_b,
            confidence_threshold=confidence_threshold,
        )

        eval_result.update({
            "variant_a_views": sample_a,
            "variant_a_conversions": conv_a,
            "variant_b_views": sample_b,
            "variant_b_conversions": conv_b,
            "conversion_event_type": conversion_event_type,
        })
        return eval_result

    # ==========================================
    # 12 Week Year scoring (§10)
    # ==========================================

    @staticmethod
    def calculate_12_week_execution_score(
        commitments_completed: int,
        total_commitments: int
    ) -> float:
        if total_commitments <= 0:
            return 0.0
        return round((commitments_completed / total_commitments) * 100, 1)

    @staticmethod
    def calculate_lag_kpi_score(objectives: List[Dict[str, float]]) -> float:
        """Điểm KPI kết quả: trung bình mức đạt mục tiêu (current/target), chặn trần 100%
        để một objective vượt xa không che lấp các objective đang trượt."""
        usable = [o for o in objectives if o.get("target_value", 0) > 0]
        if not usable:
            return 0.0
        total = sum(min(o["current_value"] / o["target_value"], 1.0) for o in usable)
        return round(total / len(usable) * 100, 1)

    @staticmethod
    def calculate_experiment_velocity(experiments_closed: int, weeks_elapsed: int) -> float:
        """Số thử nghiệm kết luận được mỗi tuần - chỉ số nhịp học của tổ chức (§10)."""
        if weeks_elapsed <= 0:
            return 0.0
        return round(experiments_closed / weeks_elapsed, 2)

    @staticmethod
    def build_scorecard(
        commitments_completed: int,
        total_commitments: int,
        objectives: List[Dict[str, float]],
        experiments_closed: int,
        weeks_elapsed: int,
    ) -> Dict[str, Any]:
        execution = AnalyticsEngine.calculate_12_week_execution_score(commitments_completed, total_commitments)
        lag = AnalyticsEngine.calculate_lag_kpi_score(objectives)
        velocity = AnalyticsEngine.calculate_experiment_velocity(experiments_closed, weeks_elapsed)
        return {
            "execution_score_pct": execution,
            "lag_kpi_score_pct": lag,
            "experiment_velocity_per_week": velocity,
            "weeks_elapsed": weeks_elapsed,
            "commitments_completed": commitments_completed,
            "total_commitments": total_commitments,
            # Không có cam kết nào thì không có gì để chấm - phải nói rõ thay vì hiện 0%
            # như thể đội ngũ trượt toàn bộ (nguồn gốc của con số 85% hard-code trước đây).
            "has_execution_data": total_commitments > 0,
        }

    # ==========================================
    # Anomaly detection (§18 event-driven)
    # ==========================================

    @staticmethod
    def detect_anomaly(current: float, baseline: float, threshold_pct: float = 20.0) -> Dict[str, Any]:
        """So sánh giá trị hiện tại với baseline, cờ lên khi lệch quá ngưỡng.

        Đây là đầu vào cho luật event-driven kiểu "CPA tăng > 20% → Ads Optimization Agent".
        """
        if baseline == 0:
            return {"is_anomaly": False, "change_pct": 0.0, "direction": "flat"}
        change_pct = round((current - baseline) / abs(baseline) * 100, 2)
        direction = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
        return {
            "is_anomaly": abs(change_pct) >= threshold_pct,
            "change_pct": change_pct,
            "direction": direction,
            "threshold_pct": threshold_pct,
        }

    # ==========================================
    # Attribution Engine (§28)
    # ==========================================

    @staticmethod
    def calculate_attribution(
        touchpoints: List[Dict[str, Any]],
        model_type: str = "last_touch",
        conversion_value: float = 1.0
    ) -> Dict[str, Any]:
        """
        Tính toán phân bổ chuyển đổi đa chạm (Multi-touch Attribution) bằng Python thuần:
        - first_touch: 100% cho điểm chạm đầu tiên
        - last_touch: 100% cho điểm chạm cuối cùng
        - linear: chia đều cho tất cả các điểm chạm (1/N)
        - position_based: 40% đầu, 40% cuối, 20% chia đều cho các điểm giữa (U-shape)
        - time_decay: phân rã bán rã theo thời gian gần chuyển đổi hơn
        """
        if not touchpoints:
            return {
                "model_type": model_type,
                "conversion_value": conversion_value,
                "touchpoint_count": 0,
                "channel_attribution": {},
                "campaign_attribution": {},
                "touchpoints_weighted": [],
            }

        n = len(touchpoints)
        weights: List[float] = []

        model_type = model_type.lower()
        if model_type == "first_touch":
            weights = [1.0] + [0.0] * (n - 1)
        elif model_type == "last_touch":
            weights = [0.0] * (n - 1) + [1.0]
        elif model_type == "linear":
            weights = [1.0 / n] * n
        elif model_type == "position_based":
            if n == 1:
                weights = [1.0]
            elif n == 2:
                weights = [0.5, 0.5]
            else:
                middle_weight = 0.20 / (n - 2)
                weights = [0.40] + [middle_weight] * (n - 2) + [0.40]
        elif model_type == "time_decay":
            # Bán rã luỹ thừa: điểm chạm sau cùng có trọng số cao nhất (2^0 = 1)
            raw_weights = [math.pow(2.0, (i - (n - 1)) / 2.0) for i in range(n)]
            sum_raw = sum(raw_weights)
            weights = [w / sum_raw for w in raw_weights]
        else:
            # Mặc định fallback về last_touch
            model_type = "last_touch"
            weights = [0.0] * (n - 1) + [1.0]

        channel_attr: Dict[str, float] = {}
        campaign_attr: Dict[str, float] = {}
        weighted_list: List[Dict[str, Any]] = []

        for tp, w in zip(touchpoints, weights):
            ch = tp.get("channel", "direct")
            cp = tp.get("campaign", "unassigned")
            attr_val = round(w * conversion_value, 4)
            attr_pct = round(w * 100, 2)

            channel_attr[ch] = round(channel_attr.get(ch, 0.0) + attr_val, 4)
            campaign_attr[cp] = round(campaign_attr.get(cp, 0.0) + attr_val, 4)

            weighted_list.append({
                **tp,
                "weight": round(w, 4),
                "weight_pct": attr_pct,
                "attributed_value": attr_val,
            })

        return {
            "model_type": model_type,
            "conversion_value": conversion_value,
            "touchpoint_count": n,
            "channel_attribution": channel_attr,
            "campaign_attribution": campaign_attr,
            "touchpoints_weighted": weighted_list,
        }

    # ==========================================
    # Cohort Analysis (§26, §27)
    # ==========================================

    @staticmethod
    def calculate_cohort_retention(cohorts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Tính toán bảng tỷ lệ giữ chân theo từng Cohort.
        Mỗi cohort gồm { 'cohort': '2026-W01', 'size': 100, 'active_users': [100, 45, 30, 25] }
        """
        results: List[Dict[str, Any]] = []
        for c in cohorts:
            size = c.get("size", 0)
            active_list = c.get("active_users", [])
            retention_rates: List[float] = []
            for active in active_list:
                if size <= 0:
                    retention_rates.append(0.0)
                else:
                    retention_rates.append(round((active / size) * 100, 2))
            results.append({
                "cohort": c.get("cohort", "unknown"),
                "size": size,
                "active_users": active_list,
                "retention_rates_pct": retention_rates,
            })
        return results

