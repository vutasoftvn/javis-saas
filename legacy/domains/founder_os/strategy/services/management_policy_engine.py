from typing import Dict, List, Any
from founder_os.strategy.schemas.stage_schemas import ProjectStageEnum, StagePolicySpec, StageSummaryResponse


class ManagementPolicyEngine:
    """COSA Management Policy Engine.
    
    Cung cấp cấu hình chính sách quản trị, mục tiêu, chỉ số, phương pháp và công cụ
    cho từng giai đoạn phát triển (S0 đến S6) theo chuẩn kiến trúc COSA Stage-Aware.
    """

    POLICIES: Dict[ProjectStageEnum, StagePolicySpec] = {
        ProjectStageEnum.S0_EXPLORE: StagePolicySpec(
            stage=ProjectStageEnum.S0_EXPLORE,
            code="S0",
            stage_name_vi="Khám Phá & Đánh Giá Cơ Hội",
            primary_goal="Khám phá cơ hội, xác định giả định cốt lõi và đánh giá sơ bộ độ khả thi",
            primary_questions=[
                "Có cơ hội đủ lớn và đáng để nghiên cứu sâu không?",
                "Các giả định cốt lõi về khách hàng, bài toán và thị trường là gì?",
                "Có rào cản pháp lý hoặc công nghệ nghiêm trọng nào không?"
            ],
            required_entities=["hypothesis", "assumption_map", "market_signal", "risk_map"],
            primary_metrics=["critical_assumptions_count", "feasibility_signals", "market_size_est"],
            deemphasized_tools=["bsc", "nps", "churn", "department_okrs", "full_sop", "full_crm", "paid_ads"],
            recommended_methods=["assumption_mapping", "market_research", "pestel_lite"],
            optional_lenses=["pestel_lite"],
            priority_agents=["Research Agent", "Customer Agent"],
            review_cadence="weekly"
        ),
        ProjectStageEnum.S1_PROBLEM_VALIDATION: StagePolicySpec(
            stage=ProjectStageEnum.S1_PROBLEM_VALIDATION,
            code="S1",
            stage_name_vi="Xác Thực Vấn Đề (Problem Validation)",
            primary_goal="Xác thực khách hàng mục tiêu (ICP) và nỗi đau thực tế đủ nghiêm trọng",
            primary_questions=[
                "Có khách hàng thật và nỗi đau thực tế đủ đau để đáng giải quyết không?",
                "Khách hàng đang dùng giải pháp tạm thời nào và tốn bao nhiêu chi phí/thời gian?",
                "Họ có sẵn sàng cam kết thời gian hoặc tham gia pilot không?"
            ],
            required_entities=["interview_plan", "interview_log", "icp", "problem_statement", "evidence_pack", "jtbd"],
            primary_metrics=["qualified_interviews_count", "problem_match_rate", "pain_severity_score", "pilot_interest_rate"],
            deemphasized_tools=["bsc", "nps", "crm_pipeline", "paid_ads", "full_sop", "scale_metrics"],
            recommended_methods=["customer_discovery", "jtbd", "learning_okr"],
            optional_lenses=["pestel"],
            priority_agents=["Customer Agent", "Research Agent"],
            review_cadence="weekly"
        ),
        ProjectStageEnum.S2_SOLUTION_VALIDATION: StagePolicySpec(
            stage=ProjectStageEnum.S2_SOLUTION_VALIDATION,
            code="S2",
            stage_name_vi="Xác Thực Giải Pháp (Solution Validation)",
            primary_goal="Xác thực giá trị giải pháp và mức độ sẵn sàng trả tiền của khách hàng",
            primary_questions=[
                "Giải pháp (Prototype/MVP) có tạo giá trị đủ mạnh để khách hàng đổi hành vi không?",
                "Khách hàng có cam kết dùng thử và sẵn sàng trả phí (willingness-to-pay) không?",
                "Thời gian đạt giá trị đầu tiên (time-to-value) có đủ nhanh không?"
            ],
            required_entities=["solution_hypothesis", "prototype_spec", "value_proposition", "pricing_hypothesis", "experiment_backlog"],
            primary_metrics=["activation_rate", "demo_acceptance", "pilot_commitment_rate", "paid_pilot_count", "time_to_value"],
            deemphasized_tools=["bsc", "departmental_okrs", "nps_large_scale", "growth_funnel", "full_crm"],
            recommended_methods=["lean_experiment", "value_proposition_test", "pricing_test", "validation_okr"],
            optional_lenses=["pestel"],
            priority_agents=["Product Agent", "Customer Agent", "Tech Agent"],
            review_cadence="weekly"
        ),
        ProjectStageEnum.S3_BUSINESS_VALIDATION: StagePolicySpec(
            stage=ProjectStageEnum.S3_BUSINESS_VALIDATION,
            code="S3",
            stage_name_vi="Xác Thực Mô Hình Kinh Doanh (Business Validation)",
            primary_goal="Xác thực tính khả thi của mô hình kinh doanh, Unit Economics và doanh thu thực",
            primary_questions=[
                "Doanh thu và chi phí đơn vị (Unit Economics) có đảm bảo doanh nghiệp sống được không?",
                "Quy trình bán hàng thử nghiệm có tạo ra khách hàng trả tiền thực tế không?",
                "Dòng tiền và thời gian sống sót (Runway) có đủ an toàn để tiến tới GTM không?"
            ],
            required_entities=["revenue_model", "pricing_model", "unit_economics", "sales_evidence", "runway_forecast"],
            primary_metrics=["paid_customers", "gross_margin", "cac_initial", "payback_period", "cash_burn", "runway_months"],
            deemphasized_tools=["bsc", "heavy_sop", "complex_org_hierarchy", "channel_scaling"],
            recommended_methods=["unit_economics_model", "cash_runway_model", "evidence_backed_swot"],
            optional_lenses=["swot", "tows"],
            priority_agents=["Finance Agent", "Sales Agent", "Product Agent"],
            review_cadence="weekly"
        ),
        ProjectStageEnum.S4_GO_TO_MARKET: StagePolicySpec(
            stage=ProjectStageEnum.S4_GO_TO_MARKET,
            code="S4",
            stage_name_vi="Đưa Ra Thị Trường (Go-to-Market)",
            primary_goal="Tìm kiếm và tối ưu hóa kênh tiếp cận và chuyển đổi khách hàng có khả năng lặp lại",
            primary_questions=[
                "Kênh marketing/sales nào có chi phí chuyển đổi (CAC) tối ưu và lặp lại được?",
                "Phễu bán hàng (Sales Funnel / CRM Pipeline) có vận hành ổn định không?",
                "Tỷ lệ chuyển đổi từ Lead sang Khách hàng trả tiền là bao nhiêu?"
            ],
            required_entities=["positioning", "channel_matrix", "sales_funnel", "crm_pipeline", "gtm_experiment", "sales_playbook"],
            primary_metrics=["lead_to_qualified_rate", "opportunity_win_rate", "cac", "mrr", "sales_cycle_days", "churn_rate"],
            deemphasized_tools=["bsc_org_wide", "deep_compliance_audit"],
            recommended_methods=["sales_playbook", "marketing_funnel", "tows_channel_strategy", "crm"],
            optional_lenses=["tows", "swot"],
            priority_agents=["Marketing Agent", "Sales Agent", "Finance Agent"],
            review_cadence="weekly"
        ),
        ProjectStageEnum.S5_OPERATE_GROWTH: StagePolicySpec(
            stage=ProjectStageEnum.S5_OPERATE_GROWTH,
            code="S5",
            stage_name_vi="Vận Hành & Tăng Trưởng (Operate & Grow)",
            primary_goal="Vận hành ổn định, có lợi nhuận và tăng trưởng doanh thu bền vững",
            primary_questions=[
                "Làm thế nào để duy trì nhịp độ thực thi 12 tuần và đạt mục tiêu OKRs?",
                "Quy trình SOP, tự động hóa và AI Workforce có tối ưu năng suất không?",
                "Chỉ số sức khỏe doanh nghiệp 4 trụ cột có ở mức an toàn không?"
            ],
            required_entities=["twelve_week_cycle", "okr_objective", "weekly_plan", "company_health_scorecard", "sop_map"],
            primary_metrics=["revenue_growth", "gross_margin", "net_retention_rate", "productivity_score", "company_health_index"],
            deemphasized_tools=[],
            recommended_methods=["twelve_week_year", "okr", "company_health_scorecard", "sop_automation", "pdca_review"],
            optional_lenses=["swot", "tows", "pestel", "bsc"],
            priority_agents=["Execution Agent", "Finance Agent", "Tech Agent", "Legal Agent"],
            review_cadence="weekly_and_quarterly"
        ),
        ProjectStageEnum.S6_SCALE_GOVERN: StagePolicySpec(
            stage=ProjectStageEnum.S6_SCALE_GOVERN,
            code="S6",
            stage_name_vi="Mở Rộng & Quản Trị (Scale & Govern)",
            primary_goal="Mở rộng quy mô tổ chức, phân bổ vốn và quản trị rủi ro danh mục toàn diện",
            primary_questions=[
                "Cơ cấu tổ chức và vốn có hỗ trợ mở rộng đa dự án mà không mất kiểm soát?",
                "Các rủi ro pháp lý, bảo mật và vận hành đã được kiểm soát theo chuẩn mực chưa?",
                "Phân bổ nguồn lực giữa các venture/dự án trong portfolio có cân bằng không?"
            ],
            required_entities=["portfolio_matrix", "governance_policy", "risk_register", "capital_allocation_plan", "compliance_audit"],
            primary_metrics=["portfolio_roi", "balanced_health_index", "compliance_score", "ebitda", "capital_efficiency"],
            deemphasized_tools=[],
            recommended_methods=["portfolio_management", "balanced_scorecard", "risk_governance", "tows_portfolio_strategy"],
            optional_lenses=["bsc", "tows", "pestel"],
            priority_agents=["Execution Agent", "Legal Agent", "Finance Agent"],
            review_cadence="monthly_and_quarterly"
        )
    }

    # The product-facing maturity vocabulary supersedes the old S0..S6 codes.
    # Keep the operational policy content while returning the requested enum,
    # so callers never receive a policy that claims to belong to another stage.
    MATURITY_POLICY_SOURCE: Dict[ProjectStageEnum, ProjectStageEnum] = {
        ProjectStageEnum.IDEA: ProjectStageEnum.S0_EXPLORE,
        ProjectStageEnum.VALIDATION: ProjectStageEnum.S1_PROBLEM_VALIDATION,
        ProjectStageEnum.MVP: ProjectStageEnum.S2_SOLUTION_VALIDATION,
        ProjectStageEnum.EARLY_TRACTION: ProjectStageEnum.S3_BUSINESS_VALIDATION,
        ProjectStageEnum.GROWTH: ProjectStageEnum.S5_OPERATE_GROWTH,
        ProjectStageEnum.SCALE: ProjectStageEnum.S6_SCALE_GOVERN,
        ProjectStageEnum.PAUSED: ProjectStageEnum.S0_EXPLORE,
        ProjectStageEnum.SUNSET: ProjectStageEnum.S6_SCALE_GOVERN,
    }

    @classmethod
    def get_policy(cls, stage: ProjectStageEnum | str) -> StagePolicySpec:
        """Lấy chính sách chi tiết cho một Stage cụ thể."""
        if isinstance(stage, str):
            try:
                stage = ProjectStageEnum(stage)
            except ValueError:
                stage = ProjectStageEnum.S1_PROBLEM_VALIDATION
        policy = cls.POLICIES.get(stage)
        if policy:
            return policy
        source_stage = cls.MATURITY_POLICY_SOURCE.get(stage, ProjectStageEnum.S1_PROBLEM_VALIDATION)
        return cls.POLICIES[source_stage].model_copy(update={"stage": stage})

    @classmethod
    def list_stage_summaries(cls) -> List[StageSummaryResponse]:
        """Danh sách tóm tắt cả 7 Stage."""
        return [
            StageSummaryResponse(
                stage=p.stage,
                code=p.code,
                name_vi=p.stage_name_vi,
                primary_goal=p.primary_goal,
                recommended_methods=p.recommended_methods,
                priority_agents=p.priority_agents
            )
            for p in cls.POLICIES.values()
        ]
