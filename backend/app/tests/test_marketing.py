from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.db.models import (
    Brain, CampaignAsset, MarketingCampaign, MarketingExperiment, MarketingLearning,
    MarketingMetric, MarketingObjective, MetricSnapshot, PendingApproval, SkillExecution,
    WorkspaceMember, MarketingContext, MarketingLoop, MarketingDecision, MarketingRecommendation
)
from app.core.snowflake import generate_snowflake_id
from app.business.marketing.router import (
    ApprovalReviewRequest, CampaignAssetCreate, CampaignCreate, CampaignStatusUpdate,
    ExperimentCreate, ExperimentDecisionRequest, ExperimentEvaluateRequest, LearningCreate,
    MarketingContextCreate, MarketingObjectiveCreate, MetricUpsert, SkillExecuteRequest,
    CustomerResearchUpdate, ProductMarketingUpdate, OfferArchitectureUpdate, Plan12WUpdate,
    MarketingLoopCreate, MarketingLoopUpdate, AttributionCalculateRequest, DecisionCreate,
    DecisionUpdate, RecommendationCreate,
    change_campaign_status, create_campaign, create_campaign_asset, create_experiment,
    create_marketing_objective, create_or_update_marketing_context, decide_experiment,
    evaluate_experiment, execute_skill, get_funnel, resolve_brain_id, review_approval,
    upsert_metric, get_customer_research, update_customer_research, get_product_marketing,
    update_product_marketing, get_offer_architecture, update_offer_architecture,
    get_12w_plan, update_12w_plan, list_loops, create_loop, update_loop, trigger_loop,
    calculate_attribution as calculate_attribution_endpoint, list_decisions,
    create_decision, update_decision, list_recommendations, create_recommendation,
    update_recommendation_status
)
from app.business.marketing.services.analytics_engine import AnalyticsEngine
from app.business.marketing.services.context_adapter import ContextAdapter
from app.business.marketing.services.funnel_engine import FunnelEngine
from app.business.marketing.services.skill_router import SkillRouter
from app.tests.marketing_fakes import FakeDb


def mock_member(ws_id: int) -> WorkspaceMember:
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = generate_snowflake_id()
    m.workspace_id = ws_id
    m.role = "admin"
    return m


@pytest.fixture
def scope():
    ws_id = generate_snowflake_id()
    brain = Brain(id=generate_snowflake_id(), workspace_id=ws_id)
    return ws_id, brain, mock_member(ws_id)


# ==========================================
# Analytics Engine (§13, §15)
# ==========================================

def test_acquisition_and_conversion_metrics():
    assert AnalyticsEngine.calculate_conversion_rate(25, 1000) == 2.5
    assert AnalyticsEngine.calculate_cac(500.0, 10) == 50.0
    assert AnalyticsEngine.calculate_roas(3000.0, 1000.0) == 3.0
    assert AnalyticsEngine.calculate_ctr(50, 1000) == 5.0
    assert AnalyticsEngine.calculate_cpc(500.0, 250) == 2.0
    assert AnalyticsEngine.calculate_cpl(500.0, 25) == 20.0


def test_revenue_metrics_handle_zero_without_raising():
    assert AnalyticsEngine.calculate_arpu(1000.0, 0) == 0.0
    assert AnalyticsEngine.calculate_roas(1000.0, 0) == 0.0
    # churn = 0 nghĩa là LTV vô hạn về mặt toán học -> trả 0.0 thay vì bịa số lớn
    assert AnalyticsEngine.calculate_ltv(arpu=100.0, gross_margin_pct=80.0, monthly_churn_pct=0.0) == 0.0


def test_ltv_payback_and_ratio():
    ltv = AnalyticsEngine.calculate_ltv(arpu=100.0, gross_margin_pct=80.0, monthly_churn_pct=5.0)
    assert ltv == 1600.0
    assert AnalyticsEngine.calculate_payback_months(cac=400.0, arpu=100.0, gross_margin_pct=80.0) == 5.0
    assert AnalyticsEngine.calculate_ltv_cac_ratio(ltv, 400.0) == 4.0


def test_retention_metrics():
    assert AnalyticsEngine.calculate_churn_rate(200, 10) == 5.0
    assert AnalyticsEngine.calculate_retention_rate(customers_start=200, customers_end=210, new_customers=30) == 90.0
    assert AnalyticsEngine.calculate_nrr(
        starting_mrr=1000, expansion_mrr=200, contraction_mrr=50, churned_mrr=50
    ) == 110.0
    assert AnalyticsEngine.calculate_grr(starting_mrr=1000, contraction_mrr=50, churned_mrr=50) == 90.0


def test_funnel_conversion_and_bottleneck():
    values = [1000, 400, 300, 30]
    conversions = AnalyticsEngine.calculate_funnel_conversions(values)
    assert conversions[1]["step_conversion_pct"] == 40.0
    assert conversions[3]["overall_conversion_pct"] == 3.0
    # Bước rớt mạnh nhất là 300 -> 30 (10%), không phải 1000 -> 400 (40%)
    assert AnalyticsEngine.detect_funnel_bottleneck(values) == 3


def test_funnel_skips_stages_without_measurement():
    # Bước 3 chưa gắn chỉ số nào (None). Nếu coi nó là 0 thì bước 4 sẽ hiện 0% và bị gán
    # nhầm là nút thắt, dù thực tế 300 -> 90 mới là chỗ rớt.
    values = [1000.0, 400.0, None, 90.0]
    conversions = AnalyticsEngine.calculate_funnel_conversions(values)

    assert conversions[2]["step_conversion_pct"] is None
    assert conversions[2]["value"] is None
    # Bước 4 nối tiếp bước 2 (bước đo được gần nhất), không nối với khoảng trống
    assert conversions[3]["step_conversion_pct"] == 22.5
    assert conversions[3]["overall_conversion_pct"] == 9.0
    assert AnalyticsEngine.detect_funnel_bottleneck(values) == 3


def test_funnel_bottleneck_needs_at_least_two_measured_stages():
    assert AnalyticsEngine.detect_funnel_bottleneck([None, 500.0, None]) is None
    assert AnalyticsEngine.detect_funnel_bottleneck([None, None, None]) is None


def test_experiment_evaluation_win_lose_inconclusive():
    win = AnalyticsEngine.evaluate_experiment(2.0, 5.0, 1000, 1000)
    assert win["decision"] == "WIN"
    assert win["statistically_significant"] is True
    assert win["uplift_pct"] == 150.0
    assert 0.0 <= win["p_value"] <= 1.0

    lose = AnalyticsEngine.evaluate_experiment(5.0, 2.0, 1000, 1000)
    assert lose["decision"] == "LOSE"

    small_sample = AnalyticsEngine.evaluate_experiment(2.0, 5.0, 20, 20)
    assert small_sample["decision"] == "INCONCLUSIVE"
    assert small_sample["statistically_significant"] is False


def test_experiment_confidence_threshold_is_respected():
    # z ~ 1.8: đủ ở mức 90% nhưng chưa đủ ở mức 95%
    at_90 = AnalyticsEngine.evaluate_experiment(10.0, 13.0, 1000, 1000, confidence_threshold=0.90)
    at_95 = AnalyticsEngine.evaluate_experiment(10.0, 13.0, 1000, 1000, confidence_threshold=0.95)
    assert at_90["decision"] == "WIN"
    assert at_95["decision"] == "WIN"
    assert at_95["confidence_threshold"] == 0.95


def test_scorecard_reports_missing_execution_data_instead_of_zero():
    empty = AnalyticsEngine.build_scorecard(0, 0, [], 0, 0)
    assert empty["execution_score_pct"] == 0.0
    assert empty["has_execution_data"] is False

    real = AnalyticsEngine.build_scorecard(
        commitments_completed=9,
        total_commitments=12,
        objectives=[{"current_value": 150, "target_value": 300}, {"current_value": 600, "target_value": 300}],
        experiments_closed=6,
        weeks_elapsed=6,
    )
    assert real["execution_score_pct"] == 75.0
    # Objective vượt mục tiêu bị chặn ở 100% để không che objective đang trượt
    assert real["lag_kpi_score_pct"] == 75.0
    assert real["experiment_velocity_per_week"] == 1.0
    assert real["has_execution_data"] is True


def test_anomaly_detection():
    up = AnalyticsEngine.detect_anomaly(current=130.0, baseline=100.0)
    assert up["is_anomaly"] is True
    assert up["direction"] == "up"
    assert up["change_pct"] == 30.0

    stable = AnalyticsEngine.detect_anomaly(current=105.0, baseline=100.0)
    assert stable["is_anomaly"] is False

    assert AnalyticsEngine.detect_anomaly(current=10.0, baseline=0.0)["is_anomaly"] is False


# ==========================================
# Funnel Engine (§8)
# ==========================================

def test_funnel_chain_ignores_rate_metrics(scope):
    ws_id, brain, _ = scope
    db = FakeDb({
        MarketingCampaign: [],
        MarketingExperiment: [],
        MarketingMetric: [
            MarketingMetric(workspace_id=ws_id, brain_id=brain.id, metric_name="conversions",
                            current_value=900.0, previous_value=0.0, change_pct=0.0, unit="number"),
            # churn_rate là TỶ LỆ (%). Nếu bị dùng làm số lượng của bước "Giữ chân" thì
            # chuỗi thành 900 -> 4 = 0,44% và bước này bị gán nhầm là nút thắt.
            MarketingMetric(workspace_id=ws_id, brain_id=brain.id, metric_name="churn_rate",
                            current_value=4.0, previous_value=0.0, change_pct=0.0, unit="percentage"),
        ],
    })

    funnel = FunnelEngine.build_funnel(db, ws_id, brain.id)
    retain_stage = next(s for s in funnel["stages"] if s["key"] == "retain")

    assert retain_stage["value"] is None
    assert retain_stage["has_data"] is False
    # churn_rate vẫn được hiển thị trong danh sách chỉ số của bước, chỉ không dùng nối chuỗi
    assert any(m["metric_name"] == "churn_rate" for m in retain_stage["metrics_tracked"])
    assert funnel["bottleneck"] is None


def test_funnel_has_eight_stages_with_vietnamese_labels():
    assert len(FunnelEngine.STAGES) == 8
    assert FunnelEngine.STAGE_KEYS[0] == "discover"
    assert FunnelEngine.STAGE_KEYS[-1] == "advocate"
    assert FunnelEngine.label_for("convert") == "Chuyển đổi"
    assert FunnelEngine.is_valid_stage("retain") is True
    assert FunnelEngine.is_valid_stage("tofu") is False


def test_funnel_rollup_groups_campaigns_and_metrics(scope):
    ws_id, brain, _ = scope
    campaign = MarketingCampaign(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        name="Ra mắt", funnel_stage="convert", budget=1000.0, status="active",
    )
    db = FakeDb({
        MarketingCampaign: [campaign],
        MarketingExperiment: [],
        MarketingMetric: [
            MarketingMetric(workspace_id=ws_id, brain_id=brain.id, metric_name="impressions",
                            current_value=10000.0, previous_value=0.0, change_pct=0.0, unit="number"),
            MarketingMetric(workspace_id=ws_id, brain_id=brain.id, metric_name="conversions",
                            current_value=500.0, previous_value=0.0, change_pct=0.0, unit="number"),
        ],
    })

    funnel = FunnelEngine.build_funnel(db, ws_id, brain.id)
    convert_stage = next(s for s in funnel["stages"] if s["key"] == "convert")
    assert convert_stage["campaign_count"] == 1
    assert convert_stage["active_campaign_count"] == 1
    assert convert_stage["budget"] == 1000.0
    assert convert_stage["value"] == 500.0
    assert funnel["has_metric_data"] is True

    # Bước "Cân nhắc" chưa có chỉ số nào: phải báo là chưa đo được, không phải 0%
    consider_stage = next(s for s in funnel["stages"] if s["key"] == "consider")
    assert consider_stage["value"] is None
    assert consider_stage["step_conversion_pct"] is None
    assert 'Cân nhắc' in funnel["unmeasured_stages"]
    # 10000 -> 500 là bước rớt duy nhất đo được, nút thắt không được rơi vào bước mù số liệu
    assert funnel["bottleneck"]["stage_key"] == "convert"


def test_funnel_without_metrics_reports_no_bottleneck(scope):
    ws_id, brain, _ = scope
    db = FakeDb({MarketingCampaign: [], MarketingExperiment: [], MarketingMetric: []})
    funnel = FunnelEngine.build_funnel(db, ws_id, brain.id)
    # Không có số đo thì mọi bước đều bằng 0 - chỉ điểm bừa một "nút thắt" sẽ dẫn tới
    # quyết định tối ưu sai chỗ.
    assert funnel["bottleneck"] is None
    assert funnel["has_metric_data"] is False


# ==========================================
# Skill Router (§11, §20, §25)
# ==========================================

def test_capability_resolution_and_alias():
    db = FakeDb()
    ws_id = generate_snowflake_id()

    res = SkillRouter.resolve_capability(db, ws_id, "marketing.copywriting")
    assert res["capability_id"] == "marketing.copywriting"
    assert res["primary"]["source"] == "corey"

    # marketing.paid_ads là tên gọi cũ, phải quy về đúng một capability chuẩn (§3)
    alias = SkillRouter.resolve_capability(db, ws_id, "marketing.paid_ads")
    assert alias["capability_id"] == "marketing.ads"
    listed = {c["capability_id"] for c in SkillRouter.list_capabilities(db, ws_id)}
    assert "marketing.paid_ads" not in listed
    assert "marketing.ads" in listed



def test_skill_with_external_write_is_queued_not_executed():
    db = FakeDb()
    ws_id, brain_id = generate_snowflake_id(), generate_snowflake_id()

    status_str, result = SkillRouter.execute_or_enqueue_approval(
        db=db, workspace_id=ws_id, brain_id=brain_id,
        capability_id="marketing.paid_ads",
        task_input={"title": "Chạy quảng cáo Meta"},
    )

    assert status_str == "pending_approval"
    assert result["capability_id"] == "marketing.ads"
    assert len(db.of_type(PendingApproval)) == 1
    # Điều cốt lõi: không có bản ghi thực thi nào được tạo trước khi con người duyệt
    assert db.of_type(SkillExecution) == []


def test_read_only_skill_runs_and_is_logged_as_simulated():
    db = FakeDb()
    ws_id, brain_id = generate_snowflake_id(), generate_snowflake_id()

    status_str, result = SkillRouter.execute_or_enqueue_approval(
        db=db, workspace_id=ws_id, brain_id=brain_id,
        capability_id="marketing.research", task_input={"title": "Quét đối thủ"},
    )

    assert status_str == "executed"
    executions = db.of_type(SkillExecution)
    assert len(executions) == 1
    # Runtime provider chưa đấu nối -> không được báo "đã thực thi thành công"
    assert executions[0].status == "simulated"
    assert result["runtime_bound"] is False


def test_approved_action_executes_and_links_to_approval():
    db = FakeDb()
    ws_id, brain_id = generate_snowflake_id(), generate_snowflake_id()
    approval = PendingApproval(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain_id,
        action_type="marketing.ads", title="Chạy quảng cáo",
        details={"task_input": {"title": "Chạy quảng cáo"}}, status="approved",
    )

    result = SkillRouter.execute_approved_action(db, approval)

    executions = db.of_type(SkillExecution)
    assert len(executions) == 1
    assert executions[0].approval_id == approval.id
    assert result["capability_id"] == "marketing.ads"


# ==========================================
# Tenancy (CLAUDE.md §Security)
# ==========================================

def test_brain_from_another_workspace_is_rejected():
    ws_id, other_ws_id = generate_snowflake_id(), generate_snowflake_id()
    foreign_brain = Brain(id=generate_snowflake_id(), workspace_id=other_ws_id)
    # FakeDb chỉ trả brain khi query khớp; ở đây workspace không có brain nào
    db = FakeDb({Brain: []})

    with pytest.raises(HTTPException) as exc:
        resolve_brain_id(db, ws_id, foreign_brain.id)
    assert exc.value.status_code == 404


def test_workspace_without_brain_gets_clear_error():
    db = FakeDb({Brain: []})
    with pytest.raises(HTTPException) as exc:
        resolve_brain_id(db, generate_snowflake_id(), None)
    assert exc.value.status_code == 404
    assert "Brain" in exc.value.detail


# ==========================================
# Endpoints
# ==========================================

def test_create_context_objective_and_campaign(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    ctx = create_or_update_marketing_context(
        MarketingContextCreate(icp={"tier": "B2B SaaS"}, positioning={"category": "AI Marketing OS"}),
        ws_id, brain.id, member, db,
    )["context"]
    assert ctx["icp"] == {"tier": "B2B SaaS"}

    obj = create_marketing_objective(
        MarketingObjectiveCreate(title="300 lead đủ điều kiện", target_metric="mql", target_value=300, current_value=150),
        ws_id, brain.id, member, db,
    )["objective"]
    assert obj["progress_pct"] == 50.0

    camp = create_campaign(
        CampaignCreate(name="Chiến dịch Q3", budget=5000.0, funnel_stage="convert"),
        ws_id, brain.id, member, db,
    )["campaign"]
    assert camp["name"] == "Chiến dịch Q3"
    assert camp["funnel_stage_label"] == "Chuyển đổi"
    # Chiến dịch mới luôn bắt đầu ở draft, không tự chạy
    assert camp["status"] == "draft"


def test_campaign_creation_rejects_invalid_funnel_stage():
    with pytest.raises(ValueError):
        CampaignCreate(name="Sai bước phễu", funnel_stage="tofu")


def test_activating_campaign_requires_human_approval(scope):
    ws_id, brain, member = scope
    campaign = MarketingCampaign(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        name="Chiến dịch Q3", funnel_stage="convert", budget=5000.0, status="draft",
    )
    db = FakeDb({Brain: [brain], MarketingCampaign: [campaign]})

    res = change_campaign_status(campaign.id, CampaignStatusUpdate(status="active"), ws_id, member, db)

    assert res["status"] == "pending_approval"
    # Chiến dịch KHÔNG được chuyển sang active chỉ vì client yêu cầu
    assert res["campaign"]["status"] == "pending_approval"
    assert len(db.of_type(PendingApproval)) == 1


def test_approval_applies_campaign_status_only_after_review(scope):
    ws_id, brain, member = scope
    campaign = MarketingCampaign(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        name="Chiến dịch Q3", funnel_stage="convert", budget=5000.0, status="pending_approval",
    )
    approval = PendingApproval(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        action_type="campaign.active", title="Kích hoạt chiến dịch",
        details={"campaign_id": str(campaign.id), "from_status": "draft", "to_status": "active"},
        status="pending",
    )
    db = FakeDb({Brain: [brain], MarketingCampaign: [campaign], PendingApproval: [approval]})

    res = review_approval(approval.id, ApprovalReviewRequest(approved=True, review_notes="Đồng ý"), ws_id, member, db)

    assert res["approval"]["status"] == "approved"
    assert campaign.status == "active"
    assert res["execution"]["new_status"] == "active"


def test_rejected_approval_restores_previous_campaign_status(scope):
    ws_id, brain, member = scope
    campaign = MarketingCampaign(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        name="Chiến dịch Q3", funnel_stage="convert", budget=5000.0, status="pending_approval",
    )
    approval = PendingApproval(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        action_type="campaign.active", title="Kích hoạt chiến dịch",
        details={"campaign_id": str(campaign.id), "from_status": "draft", "to_status": "active"},
        status="pending",
    )
    db = FakeDb({Brain: [brain], MarketingCampaign: [campaign], PendingApproval: [approval]})

    review_approval(approval.id, ApprovalReviewRequest(approved=False, review_notes="Ngân sách chưa duyệt"), ws_id, member, db)

    assert campaign.status == "draft"


def test_approval_cannot_be_reviewed_twice(scope):
    ws_id, brain, member = scope
    approval = PendingApproval(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        action_type="marketing.ads", title="Chạy quảng cáo", details={}, status="approved",
    )
    db = FakeDb({Brain: [brain], PendingApproval: [approval]})

    with pytest.raises(HTTPException) as exc:
        review_approval(approval.id, ApprovalReviewRequest(approved=True), ws_id, member, db)
    assert exc.value.status_code == 409


def test_asset_starts_as_draft(scope):
    ws_id, brain, member = scope
    campaign = MarketingCampaign(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id, name="Chiến dịch Q3",
        funnel_stage="engage", status="draft",
    )
    db = FakeDb({Brain: [brain], MarketingCampaign: [campaign]})

    asset = create_campaign_asset(
        campaign.id,
        CampaignAssetCreate(asset_type="social_post", title="Bài đăng ra mắt", content="Nội dung nháp"),
        ws_id, member, db,
    )["asset"]

    # AI soạn nháp; con người mới là người bấm gửi
    assert asset["approval_status"] == "draft"
    assert db.of_type(CampaignAsset)[0].workspace_id == ws_id


def test_metric_upsert_tracks_previous_value_and_snapshot(scope):
    ws_id, brain, member = scope
    existing = MarketingMetric(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id, metric_name="cac",
        category="acquisition", current_value=100.0, previous_value=0.0, change_pct=0.0, unit="currency",
    )
    db = FakeDb({Brain: [brain], MarketingMetric: [existing]})

    metric = upsert_metric(
        MetricUpsert(metric_name="cac", value=130.0, category="acquisition", unit="currency"),
        ws_id, brain.id, member, db,
    )["metric"]

    assert metric["current_value"] == 130.0
    assert metric["previous_value"] == 100.0
    assert metric["change_pct"] == 30.0
    assert len(db.of_type(MetricSnapshot)) == 1


def test_experiment_evaluate_then_human_decision_creates_learning(scope):
    ws_id, brain, member = scope
    experiment = MarketingExperiment(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=brain.id,
        hypothesis="Tiêu đề ngắn tăng CVR", metric="cvr",
        variant_a="Tiêu đề dài", variant_b="Tiêu đề ngắn", sample_size=2000, status="running",
    )
    db = FakeDb({Brain: [brain], MarketingExperiment: [experiment]})

    evaluated = evaluate_experiment(
        experiment.id, ExperimentEvaluateRequest(baseline_cvr=2.0, variant_cvr=5.0, baseline_sample=1000, variant_sample=1000),
        ws_id, member, db,
    )
    assert evaluated["evaluation"]["decision"] == "WIN"
    assert evaluated["experiment"]["status"] == "win"

    decided = decide_experiment(
        experiment.id,
        ExperimentDecisionRequest(decision="ITERATE", learning="Tiêu đề ngắn thắng nhưng mẫu chỉ từ một kênh"),
        ws_id, member, db,
    )
    # Kết quả thống kê là đầu vào, quyết định cuối vẫn thuộc về con người
    assert decided["experiment"]["status"] == "iterate"
    assert decided["learning"]["learning"].startswith("Tiêu đề ngắn thắng")
    assert len(db.of_type(MarketingLearning)) == 1


def test_execute_skill_endpoint_returns_queue_status_for_spending_capability(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    res = execute_skill(
        SkillExecuteRequest(capability_id="marketing.ads", task_input={"title": "Tăng ngân sách"}),
        ws_id, brain.id, member, db,
    )

    assert res["status"] == "pending_approval"
    assert "approval_id" in res["result"]


def test_get_funnel_endpoint_returns_all_stages(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain], MarketingCampaign: [], MarketingExperiment: [], MarketingMetric: []})

    funnel = get_funnel(ws_id, brain.id, member, db)
    assert [s["key"] for s in funnel["stages"]] == FunnelEngine.STAGE_KEYS
    assert all(s["label"] for s in funnel["stages"])


# ==========================================
# Marketing OS v2 Extended Tests
# ==========================================

def test_attribution_models():
    touchpoints = [
        {"channel": "google_ads", "campaign": "brand_search"},
        {"channel": "facebook", "campaign": "retargeting"},
        {"channel": "email", "campaign": "onboarding_welcome"},
    ]

    # First touch: 100% to google_ads
    first = AnalyticsEngine.calculate_attribution(touchpoints, model_type="first_touch", conversion_value=300.0)
    assert first["channel_attribution"]["google_ads"] == 300.0
    assert first["channel_attribution"].get("email", 0.0) == 0.0

    # Last touch: 100% to email
    last = AnalyticsEngine.calculate_attribution(touchpoints, model_type="last_touch", conversion_value=300.0)
    assert last["channel_attribution"]["email"] == 300.0

    # Linear: 100.0 to each
    linear = AnalyticsEngine.calculate_attribution(touchpoints, model_type="linear", conversion_value=300.0)
    assert linear["channel_attribution"]["google_ads"] == 100.0
    assert linear["channel_attribution"]["facebook"] == 100.0
    assert linear["channel_attribution"]["email"] == 100.0

    # Position based (U-shape): 40% first, 40% last, 20% middle
    pos = AnalyticsEngine.calculate_attribution(touchpoints, model_type="position_based", conversion_value=100.0)
    assert pos["channel_attribution"]["google_ads"] == 40.0
    assert pos["channel_attribution"]["facebook"] == 20.0
    assert pos["channel_attribution"]["email"] == 40.0

    # Time decay
    decay = AnalyticsEngine.calculate_attribution(touchpoints, model_type="time_decay", conversion_value=100.0)
    assert decay["channel_attribution"]["email"] > decay["channel_attribution"]["google_ads"]


def test_cohort_retention():
    cohorts_input = [
        {"cohort": "2026-W01", "size": 200, "active_users": [200, 100, 50, 40]},
        {"cohort": "2026-W02", "size": 100, "active_users": [100, 60, 40]},
    ]
    results = AnalyticsEngine.calculate_cohort_retention(cohorts_input)
    assert len(results) == 2
    assert results[0]["retention_rates_pct"] == [100.0, 50.0, 25.0, 20.0]
    assert results[1]["retention_rates_pct"] == [100.0, 60.0, 40.0]


def test_progressive_context_slicing():
    db = FakeDb()
    ws_id, brain_id = generate_snowflake_id(), generate_snowflake_id()

    ctx = MarketingContext(
        workspace_id=ws_id,
        brain_id=brain_id,
        icp={"industry": "SaaS B2B", "team_size": "10-50"},
        positioning={"statement": "All-in-one Marketing OS"},
        value_proposition={"main": "Tăng MRR 30%"},
        pricing={"model": "subscription", "starter": 49},
        offer_architecture={"core_offer": "14-day free trial + AI CMO"},
        customer_research={"facts": ["Customer wants faster reporting"]},
        product_marketing={"category": "AI Operating System"},
    )
    db.add(ctx)

    # CRO capability slice
    cro_slice = ContextAdapter.get_minimal_context_package(db, ws_id, brain_id, "marketing.cro")
    assert cro_slice["slice_profile"] == "conversion_cro"
    assert "icp" in cro_slice["marketing_context"]
    assert "offer" in cro_slice["marketing_context"]
    assert "brand_voice" not in cro_slice["marketing_context"]

    # Copywriting capability slice
    copy_slice = ContextAdapter.get_minimal_context_package(db, ws_id, brain_id, "marketing.copywriting")
    assert copy_slice["slice_profile"] == "copywriting_content"
    assert "positioning" in copy_slice["marketing_context"]

    # Strategic research slice
    research_slice = ContextAdapter.get_minimal_context_package(db, ws_id, brain_id, "marketing.research")
    assert research_slice["slice_profile"] == "strategic_research"
    assert "customer_research" in research_slice["marketing_context"]


def test_canvas_subsections_endpoints(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    # Customer Research
    res = update_customer_research(
        CustomerResearchUpdate(customer_research={"segments": ["SMB", "Enterprise"], "facts": ["Needs automation"]}),
        ws_id, brain.id, member, db
    )
    assert res["customer_research"]["segments"] == ["SMB", "Enterprise"]
    read_res = get_customer_research(ws_id, brain.id, member, db)
    assert read_res["customer_research"]["facts"] == ["Needs automation"]

    # Product Marketing
    pm_res = update_product_marketing(
        ProductMarketingUpdate(product_marketing={"category": "Marketing OS", "differentiators": ["Deterministic analytics"]}),
        ws_id, brain.id, member, db
    )
    assert pm_res["product_marketing"]["category"] == "Marketing OS"

    # Offer Architecture
    offer_res = update_offer_architecture(
        OfferArchitectureUpdate(offer_architecture={"core_offer": "Free audit", "guarantee": "30-day money back"}),
        ws_id, brain.id, member, db
    )
    assert offer_res["offer_architecture"]["guarantee"] == "30-day money back"

    # 12W Plan
    plan_res = update_12w_plan(
        Plan12WUpdate(marketing_plan_12w={"weeks": [{"week": 1, "theme": "Customer Research"}]}),
        ws_id, brain.id, member, db
    )
    assert plan_res["marketing_plan_12w"]["weeks"][0]["theme"] == "Customer Research"


def test_marketing_loops_crud_and_trigger(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    # Create loop
    created = create_loop(
        MarketingLoopCreate(
            loop_type="content",
            name="Weekly Content Repurposing Loop",
            description="Signal -> Topic -> Create -> Publish -> Analytics -> Refresh",
            loop_config={"frequency": "weekly", "channels": ["blog", "linkedin"]},
        ),
        ws_id, brain.id, member, db
    )
    loop_id = int(created["loop"]["id"])
    assert created["loop"]["loop_type"] == "content"
    assert created["loop"]["status"] == "active"

    # List loops
    loops_list = list_loops(ws_id, brain.id, member, db)
    assert len(loops_list["loops"]) == 1

    # Update loop
    updated = update_loop(loop_id, MarketingLoopUpdate(status="paused"), ws_id, member, db)
    assert updated["loop"]["status"] == "paused"

    # Trigger loop
    triggered = trigger_loop(loop_id, ws_id, member, db)
    assert "execution_status" in triggered


def test_decision_and_recommendation_endpoints(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    # Decision
    dec = create_decision(
        DecisionCreate(
            title="Đổi kênh quảng cáo chính sang LinkedIn",
            context_summary="CPA Meta tăng 45% trong 2 tuần qua",
            decision="Dịch chuyển 50% ngân sách Meta sang LinkedIn Ads",
            reason="Tệp B2B trên LinkedIn có CVR cao hơn",
        ),
        ws_id, brain.id, member, db
    )
    dec_id = int(dec["decision"]["id"])
    assert dec["decision"]["title"] == "Đổi kênh quảng cáo chính sang LinkedIn"

    # Update decision outcome
    up_dec = update_decision(
        dec_id,
        DecisionUpdate(actual_outcome="CPA giảm 25%, qualified leads tăng 30%", learning="LinkedIn hiệu quả vượt trội cho phân khúc B2B"),
        ws_id, member, db
    )
    assert up_dec["decision"]["actual_outcome"] is not None

    # Recommendations
    rec = create_recommendation(
        RecommendationCreate(
            title="Tối ưu headline landing page đăng ký",
            problem="Drop-off 65% ở form đăng ký",
            hypothesis="Headline hiện tại quá kỹ thuật, cần tập trung vào kết quả",
            recommended_action="Chạy A/B test headline với Corey Copywriting Skill",
            confidence="high",
        ),
        ws_id, brain.id, member, db
    )
    rec_id = int(rec["recommendation"]["id"])
    assert rec["recommendation"]["confidence"] == "high"

    # Update recommendation status
    up_rec = update_recommendation_status(rec_id, "accepted", ws_id, member, db)
    assert up_rec["recommendation"]["status"] == "accepted"
