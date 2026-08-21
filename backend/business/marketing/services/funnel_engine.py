from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from business.marketing.models import MarketingCampaign, MarketingExperiment, MarketingMetric
from business.marketing.services.analytics_engine import AnalyticsEngine


class FunnelEngine:
    """
    Chuẩn hoá phễu 8 giai đoạn theo §8 (không dùng AARRR hay TOFU/MOFU/BOFU).

    Mỗi giai đoạn khai báo mục tiêu, trạng thái khách hàng và metric chuẩn để cockpit
    có thể rollup chiến dịch/thử nghiệm về đúng bước phễu mà không cần bảng cấu hình riêng.
    Nhãn tiếng Việt nằm ở đây (server-side) để chat/voice và UI dùng chung một bộ từ vựng.

    `volume_metrics` và `metrics` KHÁC NHAU có chủ đích: chuỗi chuyển đổi chỉ được nối
    bằng chỉ số dạng SỐ LƯỢNG. Lấy một tỷ lệ (churn_rate = 4%) làm số lượng của bước sẽ
    sinh ra "900 → 4 = 0,44%" và gán nhầm nút thắt - đã tái hiện được trên dữ liệu thật.
    """

    STAGES: List[Dict[str, Any]] = [
        {
            "key": "discover",
            "label": "Khám phá",
            "goal": "Tiếp cận đúng tệp khách hàng mục tiêu lần đầu",
            "customer_state": "Chưa biết đến thương hiệu",
            "volume_metrics": ["impressions", "reach", "search_impressions"],
            "metrics": ["impressions", "reach", "search_impressions"],
        },
        {
            "key": "engage",
            "label": "Tương tác",
            "goal": "Tạo tương tác đầu tiên với nội dung",
            "customer_state": "Biết đến nhưng chưa quan tâm sâu",
            "volume_metrics": ["clicks", "sessions"],
            "metrics": ["clicks", "ctr", "sessions", "engagement_rate"],
        },
        {
            "key": "consider",
            "label": "Cân nhắc",
            "goal": "Đưa vào danh sách lựa chọn khi so sánh giải pháp",
            "customer_state": "Đang so sánh với phương án thay thế",
            "volume_metrics": ["leads", "mql", "demo_requests"],
            "metrics": ["leads", "mql", "demo_requests"],
        },
        {
            "key": "convert",
            "label": "Chuyển đổi",
            "goal": "Chốt đơn / đăng ký trả phí",
            "customer_state": "Sẵn sàng ra quyết định mua",
            "volume_metrics": ["conversions", "new_customers"],
            "metrics": ["conversions", "cvr", "new_customers", "cac"],
        },
        {
            "key": "activate",
            "label": "Kích hoạt",
            "goal": "Khách đạt khoảnh khắc giá trị đầu tiên",
            "customer_state": "Đã mua nhưng chưa dùng thành thạo",
            "volume_metrics": ["activated_customers", "onboarding_completed"],
            "metrics": ["activated_customers", "activation_rate", "onboarding_completion"],
        },
        {
            "key": "retain",
            "label": "Giữ chân",
            "goal": "Duy trì sử dụng và hạn chế rời bỏ",
            "customer_state": "Đang sử dụng thường xuyên",
            "volume_metrics": ["retained_customers", "active_customers"],
            "metrics": ["retained_customers", "active_customers", "retention_rate", "churn_rate", "grr"],
        },
        {
            "key": "expand",
            "label": "Mở rộng",
            "goal": "Tăng doanh thu trên khách hàng hiện hữu",
            "customer_state": "Hài lòng, có nhu cầu mở rộng",
            "volume_metrics": ["expansion_customers"],
            "metrics": ["expansion_customers", "expansion_mrr", "nrr", "arpu"],
        },
        {
            "key": "advocate",
            "label": "Lan toả",
            "goal": "Khách hàng giới thiệu và bảo chứng thương hiệu",
            "customer_state": "Trung thành, sẵn sàng giới thiệu",
            "volume_metrics": ["referrals", "reviews"],
            "metrics": ["referrals", "reviews", "nps"],
        },
    ]

    STAGE_KEYS = [s["key"] for s in STAGES]

    @classmethod
    def is_valid_stage(cls, stage: str) -> bool:
        return stage in cls.STAGE_KEYS

    @classmethod
    def label_for(cls, stage: str) -> str:
        for s in cls.STAGES:
            if s["key"] == stage:
                return s["label"]
        return stage

    @classmethod
    def build_funnel(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
    ) -> Dict[str, Any]:
        """Rollup chiến dịch, thử nghiệm và metric thật về từng bước phễu."""
        campaigns = db.query(MarketingCampaign).filter(
            MarketingCampaign.workspace_id == workspace_id,
            MarketingCampaign.brain_id == brain_id,
        ).all()

        experiments = db.query(MarketingExperiment).filter(
            MarketingExperiment.workspace_id == workspace_id,
            MarketingExperiment.brain_id == brain_id,
        ).all()

        metrics = db.query(MarketingMetric).filter(
            MarketingMetric.workspace_id == workspace_id,
            MarketingMetric.brain_id == brain_id,
        ).all()

        metric_by_name = {m.metric_name: m for m in metrics}

        stages: List[Dict[str, Any]] = []
        for definition in cls.STAGES:
            key = definition["key"]
            stage_campaigns = [c for c in campaigns if c.funnel_stage == key]
            campaign_ids = {c.id for c in stage_campaigns}
            stage_experiments = [e for e in experiments if e.campaign_id in campaign_ids]

            stage_metrics = []
            for metric_name in definition["metrics"]:
                m = metric_by_name.get(metric_name)
                if not m:
                    continue
                stage_metrics.append({
                    "metric_name": m.metric_name,
                    "value": m.current_value,
                    "previous_value": m.previous_value,
                    "change_pct": m.change_pct,
                    "unit": m.unit,
                })

            # None = chưa có chỉ số SỐ LƯỢNG nào cho bước này, khác với "đo được và bằng 0".
            primary_value: Optional[float] = None
            primary_metric: Optional[str] = None
            for metric_name in definition["volume_metrics"]:
                m = metric_by_name.get(metric_name)
                if m:
                    primary_value = m.current_value
                    primary_metric = m.metric_name
                    break

            stages.append({
                **definition,
                "campaign_count": len(stage_campaigns),
                "active_campaign_count": len([c for c in stage_campaigns if c.status == "active"]),
                "budget": round(sum(c.budget or 0.0 for c in stage_campaigns), 2),
                "experiment_count": len(stage_experiments),
                "metrics_tracked": stage_metrics,
                "value": primary_value,
                "value_metric": primary_metric,
                "has_data": primary_value is not None,
            })

        values: List[Optional[float]] = [s["value"] for s in stages]
        conversions = AnalyticsEngine.calculate_funnel_conversions(values)
        for stage, conv in zip(stages, conversions):
            stage["step_conversion_pct"] = conv["step_conversion_pct"]
            stage["overall_conversion_pct"] = conv["overall_conversion_pct"]
            stage["drop_off"] = conv["drop_off"]

        # Nút thắt chỉ được kết luận từ các bước đã có số đo; bước chưa gắn chỉ số là
        # khoảng trống đo lường, cần bổ sung dữ liệu chứ không phải tối ưu chuyển đổi.
        bottleneck_idx = AnalyticsEngine.detect_funnel_bottleneck(values)
        bottleneck = None
        if bottleneck_idx is not None:
            bottleneck = {
                "stage_key": stages[bottleneck_idx]["key"],
                "stage_label": stages[bottleneck_idx]["label"],
                "step_conversion_pct": stages[bottleneck_idx]["step_conversion_pct"],
            }

        unmeasured = [s["label"] for s in stages if not s["has_data"]]
        return {
            "stages": stages,
            "bottleneck": bottleneck,
            "total_campaigns": len(campaigns),
            "has_metric_data": any(s["has_data"] for s in stages),
            # Nói thẳng bước nào đang mù số liệu để người dùng biết cần nhập gì tiếp theo.
            "unmeasured_stages": unmeasured,
        }
