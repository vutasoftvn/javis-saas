#!/usr/bin/env python3
"""Script to generate Tranche A skillpacks with complete manifest and SKILL.md governance."""

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"

PACKS = [
    # --- Task 7: 25 Core and P0 packs ---
    # Lifecycle (3)
    {
        "path": "lifecycle/context-resolver",
        "id": "lifecycle.context-resolver",
        "name": "Lifecycle Stage Context Resolver",
        "domain": "lifecycle",
        "category": "lifecycle",
        "desc": "Truy xuất và chuẩn hóa ngữ cảnh giai đoạn vòng đời dự án (P0-P6), gate policies và tiêu chuẩn bằng chứng.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.project.get"],
    },
    {
        "path": "lifecycle/next-best-action",
        "id": "lifecycle.next-best-action",
        "name": "Lifecycle Next Best Action Advisor",
        "domain": "lifecycle",
        "category": "lifecycle",
        "desc": "Đề xuất hành động tối ưu tiếp theo cho founder dựa trên giai đoạn hiện tại, khoảng trống bằng chứng và rủi ro tồn đọng.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.next_best_action.get"],
    },
    {
        "path": "lifecycle/gate-evaluator",
        "id": "lifecycle.gate-evaluator",
        "name": "Stage Gate Readiness Evaluator",
        "domain": "lifecycle",
        "category": "lifecycle",
        "desc": "Đánh giá mức độ sẵn sàng vượt gate dựa trên bằng chứng đã được duyệt (approved evidence) — chỉ mang tính khuyến nghị (recommendation-only).",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.gate_evaluation.create", "strategy.evidence.list"],
    },
    # Evidence (3)
    {
        "path": "evidence/intake-provenance",
        "id": "evidence.intake-provenance",
        "name": "Evidence Ingestion & Provenance Logger",
        "domain": "evidence",
        "category": "evidence",
        "desc": "Ghi nhận bằng chứng mới vào hệ thống dưới trạng thái candidate, lưu vết nguồn gốc (provenance) và liên kết artifact.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": ["strategy.evidence.create"],
    },
    {
        "path": "evidence/gap-analysis",
        "id": "evidence.gap-analysis",
        "name": "Evidence Gap Analysis & Deficiency Audit",
        "domain": "evidence",
        "category": "evidence",
        "desc": "Phân tích các lỗ hổng bằng chứng còn thiếu đối chiếu với yêu cầu của gate giai đoạn hiện tại.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.evidence.list"],
    },
    {
        "path": "evidence/artifact-review",
        "id": "evidence.artifact-review",
        "name": "Artifact Quality & Evidence Review",
        "domain": "evidence",
        "category": "evidence",
        "desc": "Đánh giá chất lượng và độ xác thực của các artifact dự án trước khi đệ trình duyệt làm bằng chứng chính thức.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.evidence.list"],
    },
    # Governance (7)
    {
        "path": "governance/approval-plan",
        "id": "governance.approval-plan",
        "name": "Governance Approval Plan Builder",
        "domain": "governance",
        "category": "governance",
        "desc": "Xây dựng kế hoạch phê duyệt phân tầng (founder, co-founder, admin) cho các quyết định chuyển stage và chi tiêu.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "governance/policy-resolution",
        "id": "governance.policy-resolution",
        "name": "Stage Policy Resolution Engine",
        "domain": "governance",
        "category": "governance",
        "desc": "Tra cứu và giải quyết các điều kiện tiên quyết của chính sách cổng kiểm soát cho từng dự án.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.project.get"],
    },
    {
        "path": "governance/risk-register",
        "id": "governance.risk-register",
        "name": "Venture Risk Register & Mitigation Log",
        "domain": "governance",
        "category": "governance",
        "desc": "Lập và theo dõi sổ đăng ký rủi ro dự án (thị trường, kỹ thuật, pháp lý, tài chính) kèm kế hoạch giảm thiểu.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "governance/privacy-assessment",
        "id": "governance.privacy-assessment",
        "name": "Privacy Impact & Data Governance Assessment",
        "domain": "governance",
        "category": "governance",
        "desc": "Đánh giá tuân thủ quyền riêng tư, ranh giới tenant, bảo vệ dữ liệu PII và phân loại dữ liệu khách hàng.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    {
        "path": "governance/security-assessment",
        "id": "governance.security-assessment",
        "name": "Security Posture & Vulnerability Review",
        "domain": "governance",
        "category": "governance",
        "desc": "Đánh giá mức độ an toàn thông tin, rủi ro cấu hình, ủy quyền phân quyền RBAC và ranh giới multi-tenant.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    {
        "path": "governance/human-handoff",
        "id": "governance.human-handoff",
        "name": "Human-in-the-Loop Escalation & Handoff",
        "domain": "governance",
        "category": "governance",
        "desc": "Chuẩn bị gói hồ sơ bàn giao cho con người (Founder/Admin) khi agent gặp giới hạn quyền hạn hoặc ngoại lệ.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "governance/compliance-gap-analysis",
        "id": "governance.compliance-gap-analysis",
        "name": "Regulatory & Policy Compliance Gap Analysis",
        "domain": "governance",
        "category": "governance",
        "desc": "Rà soát khoảng trống tuân thủ quy định ngành và chính sách bảo mật trước khi thương mại hóa.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    # Analytics (1)
    {
        "path": "analytics/metric-contract",
        "id": "analytics.metric-contract",
        "name": "Metric Contract & KPI Definition",
        "domain": "analytics",
        "category": "analytics",
        "desc": "Định nghĩa hợp đồng chỉ số (metric contract), công thức tính toán và nguồn dữ liệu tin cậy cho dự án.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    # Operations (1)
    {
        "path": "operations/weekly-review",
        "id": "operations.weekly-review",
        "name": "Weekly Operating Review & Progress Audit",
        "domain": "operations",
        "category": "operations",
        "desc": "Tổng hợp nhịp vận hành tuần, đánh giá tiến độ task, OKR và các quyết định chuyển tiếp giai đoạn.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"],
        "gates": ["G0", "G1", "G2", "G3", "G4", "G5", "G6"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["operations.task.list"],
    },
    # Strategy P0 (4)
    {
        "path": "strategy/venture-thesis",
        "id": "strategy.venture-thesis",
        "name": "Venture Thesis & Problem Discovery Formulation",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Soạn thảo và chuẩn hóa luận điểm khởi nghiệp (venture thesis), định vị cơ hội thị trường và tiền đề cốt lõi.",
        "stages": ["P0_DISCOVERY"],
        "gates": ["G0"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": ["strategy.project.get"],
    },
    {
        "path": "strategy/business-model",
        "id": "strategy.business-model",
        "name": "Business Model Canvas & Value Dynamics",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Thiết lập cấu trúc mô hình kinh doanh ban đầu (Lean / Business Model Canvas) và luồng giá trị kinh tế.",
        "stages": ["P0_DISCOVERY"],
        "gates": ["G0"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "strategy/decision-rights",
        "id": "strategy.decision-rights",
        "name": "Decision Rights & Governance Matrix (DACI/RACI)",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Xác lập ma trận quyền quyết định giữa các đồng sáng lập và hội đồng quản trị cho các cột mốc quan trọng.",
        "stages": ["P0_DISCOVERY"],
        "gates": ["G0"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "strategy/pestle-analysis",
        "id": "strategy.pestle-analysis",
        "name": "PESTLE Macro Environmental Analysis",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Phân tích các yếu tố vĩ mô (Chính trị, Kinh tế, Xã hội, Công nghệ, Pháp lý, Môi trường) ảnh hưởng tới luận điểm dự án.",
        "stages": ["P0_DISCOVERY"],
        "gates": ["G0"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["web.search"],
    },
    # Finance P0 (2)
    {
        "path": "finance/runway-forecast",
        "id": "finance.runway-forecast",
        "name": "Runway Forecast & Cash Flow Projection",
        "domain": "finance",
        "category": "finance",
        "desc": "Dự báo thời gian tồn tại của dòng tiền (runway), tỷ lệ đốt tiền (burn rate) và các kịch bản tài chính cho dự án.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION"],
        "gates": ["G0", "G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    {
        "path": "finance/budget-guardrails",
        "id": "finance.budget-guardrails",
        "name": "Budget Guardrails & Spending Policy",
        "domain": "finance",
        "category": "finance",
        "desc": "Thiết lập hàng rào ngân sách kiểm soát chi phí thực nghiệm và chi tiêu giai đoạn sớm.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION"],
        "gates": ["G0", "G1"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    # Research P0 (1)
    {
        "path": "research/industry-trends",
        "id": "research.industry-trends",
        "name": "Industry Trends & Market Signals Scan",
        "domain": "research",
        "category": "research",
        "desc": "Khảo sát xu hướng ngành, báo cáo thị trường và các tín hiệu công nghệ mới hỗ trợ luận điểm khám phá.",
        "stages": ["P0_DISCOVERY"],
        "gates": ["G0"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["web.search"],
    },
    # AI Governance P0 (2)
    {
        "path": "ai/data-rights-review",
        "id": "ai.data-rights-review",
        "name": "AI Data Rights & Intellectual Property Audit",
        "domain": "ai",
        "category": "ai",
        "desc": "Rà soát quyền sử dụng dữ liệu huấn luyện, bản quyền sở hữu trí tuệ và điều khoản cấp phép dữ liệu AI.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION"],
        "gates": ["G0", "G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    {
        "path": "ai/model-provider-risk",
        "id": "ai.model-provider-risk",
        "name": "Foundation Model Provider Risk & Dependency Review",
        "domain": "ai",
        "category": "ai",
        "desc": "Đánh giá rủi ro phụ thuộc vào nhà cung cấp mô hình nền tảng, độ trễ, chi phí token và tính sẵn sàng chuyển đổi.",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION"],
        "gates": ["G0", "G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },

    # --- Task 8: 12 P1 Problem Validation packs ---
    {
        "path": "research/market-sizing",
        "id": "research.market-sizing",
        "name": "TAM SAM SOM Market Sizing",
        "domain": "research",
        "category": "research",
        "desc": "Tính toán quy mô thị trường tổng thể (TAM), thị trường phục vụ được (SAM) và thị trường mục tiêu đạt được (SOM) từ dữ liệu thực nghiệm.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["web.search"],
    },
    {
        "path": "strategy/porters-five-forces",
        "id": "strategy.porters-five-forces",
        "name": "Porter's Five Forces Industry Competitiveness Analysis",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Phân tích 5 áp lực cạnh tranh của Porter đối với thị trường mục tiêu của dự án.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["web.search"],
    },
    {
        "path": "strategy/icp-definition",
        "id": "strategy.icp-definition",
        "name": "Ideal Customer Profile & Problem Fit",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Xác lập chân dung khách hàng lý tưởng (ICP) chi tiết dựa trên các bằng chứng phỏng vấn và dữ liệu khách hàng.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": ["strategy.evidence.list"],
    },
    {
        "path": "discovery/interview-script",
        "id": "discovery.interview-script",
        "name": "Customer Discovery Interview Script Generator",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Tạo kịch bản phỏng vấn khách hàng không thiên kiến tuân thủ The Mom Test và JTBD.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "discovery/interview-prep",
        "id": "discovery.interview-prep",
        "name": "Discovery Interview Brief & Subject Background",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Chuẩn bị hồ sơ bối cảnh và mục tiêu kiểm chứng trước buổi phỏng vấn khách hàng.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["web.search"],
    },
    {
        "path": "discovery/interview-summary",
        "id": "discovery.interview-summary",
        "name": "Discovery Interview Evidence Summarizer",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Tổng hợp transcript phỏng vấn thành các trích dẫn nguyên văn và bằng chứng candidate phục vụ kiểm chứng vấn đề.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": ["strategy.evidence.create"],
    },
    {
        "path": "discovery/jtbd-synthesis",
        "id": "discovery.jtbd-synthesis",
        "name": "Jobs-To-Be-Done & Outcome Synthesis",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Tổng hợp các nhiệm vụ cần hoàn thành (JTBD), kết quả mong đợi và lực cản chuyển đổi từ phỏng vấn.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.evidence.list"],
    },
    {
        "path": "discovery/pain-point-analysis",
        "id": "discovery.pain-point-analysis",
        "name": "Customer Pain Point Severity Ranking",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Phân loại và xếp hạng mức độ nghiêm trọng cũng như tần suất của các nỗi đau khách hàng.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": ["strategy.evidence.list"],
    },
    {
        "path": "discovery/assumption-mapping",
        "id": "discovery.assumption-mapping",
        "name": "Venture Assumption Mapping & Classification",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Phân loại các giả định dự án theo 4 trục: Khả năng mong muốn (Desirability), Tính khả thi (Feasibility), Khả năng sống sót (Viability), Tính trách nhiệm (Responsibility).",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "sales/founder-led-sales-copilot",
        "id": "sales.founder-led-sales-copilot",
        "name": "Founder-Led Sales Copilot & Call Preparation",
        "domain": "sales",
        "category": "sales",
        "desc": "Hỗ trợ founder chuẩn bị cuộc gọi bán hàng sớm, xử lý từ chối và ghi nhận nhu cầu thực tế.",
        "stages": ["P1_PROBLEM_VALIDATION"],
        "gates": ["G1"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    {
        "path": "marketing/channel-strategy",
        "id": "marketing.channel-strategy",
        "name": "Early Customer Acquisition Channel Strategy",
        "domain": "marketing",
        "category": "marketing",
        "desc": "Định hình chiến lược kênh tiếp cận khách hàng giai đoạn đầu (Outbound, Content, Community, Partnerships).",
        "stages": ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION"],
        "gates": ["G0", "G1"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },

    # --- Task 9: 10 P2 + 1 P3 packs ---
    {
        "path": "strategy/value-proposition",
        "id": "strategy.value-proposition",
        "name": "Value Proposition Canvas & Solution Fit",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Khớp nối giải pháp sản phẩm với các nỗi đau và lợi ích đã được kiểm chứng của khách hàng.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": ["strategy.evidence.list"],
    },
    {
        "path": "strategy/positioning",
        "id": "strategy.positioning",
        "name": "Strategic Solution Positioning & Messaging",
        "domain": "strategy",
        "category": "strategy",
        "desc": "Xác lập định vị giải pháp chiến lược và thông điệp cạnh tranh cốt lõi cho giai đoạn P2.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "discovery/assumption-prioritization",
        "id": "discovery.assumption-prioritization",
        "name": "Assumption Risk Matrix Prioritization",
        "domain": "discovery",
        "category": "discovery",
        "desc": "Xếp hạng ưu tiên giả định theo mức độ rủi ro tử huyệt (fatal if wrong) và mức độ thiếu bằng chứng.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "product/opportunity-solution-tree",
        "id": "product.opportunity-solution-tree",
        "name": "Opportunity Solution Tree Mapping",
        "domain": "product",
        "category": "product",
        "desc": "Xây dựng cây cơ hội - giải pháp (Teresa Torres) nối từ mục tiêu mong muốn đến các giải pháp và thực nghiệm kiểm chứng.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "product/core-workflow-map",
        "id": "product.core-workflow-map",
        "name": "Core User Workflow & Experience Journey",
        "domain": "product",
        "category": "product",
        "desc": "Vẽ luồng trải nghiệm người dùng cốt lõi (happy path) và các điểm ma sát tiềm ẩn của giải pháp.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "product/mvp-prioritization",
        "id": "product.mvp-prioritization",
        "name": "MVP Feature Scope & MoSCoW Prioritization",
        "domain": "product",
        "category": "product",
        "desc": "Thu gọn phạm vi MVP tối thiểu để kiểm chứng giải pháp, cắt bỏ tính năng không thiết yếu.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "product/mvp-experiment-selection",
        "id": "product.mvp-experiment-selection",
        "name": "Low-Cost Experiment Selection Guide",
        "domain": "product",
        "category": "product",
        "desc": "Lựa chọn loại hình thực nghiệm kiểm chứng giải pháp chi phí thấp nhất (Concierge, Wizard of Oz, Smoke Test, Prototype).",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "product/prototype-brief",
        "id": "product.prototype-brief",
        "name": "Interactive Prototype Specification Brief",
        "domain": "product",
        "category": "product",
        "desc": "Soạn thảo tài liệu yêu cầu cho prototype kiểm chứng tương tác người dùng.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
    {
        "path": "engineering/solution-feasibility",
        "id": "engineering.solution-feasibility",
        "name": "Technical Feasibility & Architecture Spike",
        "domain": "engineering",
        "category": "engineering",
        "desc": "Đánh giá tính khả thi kỹ thuật, rủi ro tích hợp kiến trúc và phân tích Build vs Buy vs Partner.",
        "stages": ["P2_SOLUTION_VALIDATION"],
        "gates": ["G2"],
        "autonomy": "L0_OBSERVE",
        "side_effect": "R",
        "tools": [],
    },
    {
        "path": "analytics/instrumentation-plan",
        "id": "analytics.instrumentation-plan",
        "name": "Product Analytics Instrumentation Plan",
        "domain": "analytics",
        "category": "analytics",
        "desc": "Kế hoạch cài đặt đo lường telemetry, taxonomy sự kiện, ánh xạ danh tính và kiểm tra chất lượng dữ liệu.",
        "stages": ["P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE"],
        "gates": ["G2", "G3"],
        "autonomy": "L1_PROPOSE",
        "side_effect": "A",
        "tools": [],
    },
]


def write_pack(pack: dict):
    pack_dir = SKILLPACKS_ROOT / pack["path"]
    pack_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {
            "id": pack["id"],
            "name": pack["name"],
            "version": "1.0.0",
            "description": pack["desc"],
        },
        "publisher": {
            "name": "javis",
            "type": "official",
        },
        "source": {
            "type": "local",
            "path": f"skillpacks/{pack['path']}",
        },
        "capability": {
            "domain": pack["domain"],
            "category": pack["category"],
            "intents": [pack["name"].lower(), pack["id"]],
        },
        "applicability": {
            "project_stages": pack["stages"],
            "gates": pack["gates"],
            "required_context": ["workspace", "project"],
            "outputs": ["artifact", "proposal"],
        },
        "autonomy": {
            "ceiling": pack["autonomy"],
            "side_effect_class": pack["side_effect"],
        },
        "evidence": {
            "min_source_refs": 1 if pack["domain"] in ("evidence", "discovery") else 0,
            "self_validation_forbidden": True,
        },
        "quality": {
            "eval_suite": f"evals/{pack['domain']}/{pack['id'].split('.')[-1]}.yaml",
            "required_negative_cases": ["missing-workspace", "cross-workspace"],
        },
        "runtime": {
            "entrypoint": "SKILL.md",
            "tools": pack["tools"],
        },
        "permissions": {
            "required": ["READ_LOCAL"],
        },
        "risk": {
            "level": "low",
        },
        "trust": {
            "tier": "T0",
        },
    }

    manifest_path = pack_dir / "manifest.yaml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest_data, f, sort_keys=False, allow_unicode=True)

    tool_mentions = ""
    if pack["tools"]:
        tool_mentions = "\n".join(f"- `{tool}`" for tool in pack["tools"])
    else:
        tool_mentions = "Không có công cụ trực tiếp (Artifact/Proposal only)."

    normalized_name = pack["id"].replace(".", "-")

    frontmatter_dict = {
        "name": normalized_name,
        "description": pack["desc"],
    }
    fm_yaml = yaml.dump(frontmatter_dict, sort_keys=False, allow_unicode=True).strip()

    skillmd_content = f"""---
{fm_yaml}
---

# {pack["name"]}

## Mục đích & Giới hạn Quyền hạn
{pack["desc"]}

> **Quy tắc an toàn & Quản trị vòng đời:**
> Không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate, không tự gọi external provider. Khi action cần quyền hoặc evidence đủ chuẩn, tạo proposal/handoff với ID evidence/artifact liên quan.

## Triggers
- Kích hoạt khi cần thực hiện nghiệp vụ `{pack["id"]}` trong giai đoạn {", ".join(pack["stages"])}.

## Anti-triggers
- Không kích hoạt ngoài phạm vi dự án hoặc khi thiếu ngữ cảnh `workspace_id` và `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Tuân thủ nguyên tắc anti-self-validation: Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Thu thập ngữ cảnh**: Đọc dữ liệu dự án và đối chiếu với chính sách giai đoạn hiện tại.
2. **Xử lý chuyên môn**: Thực hiện phân tích, trích xuất thông tin hoặc lập kế hoạch theo chuẩn.
3. **Đóng gói kết quả**: Tạo bản nháp artifact hoặc đề xuất (proposal) có bằng chứng dẫn chiếu.
4. **Bàn giao kiểm duyệt**: Trình duyệt qua kênh Human Handoff nếu cần hành động có side-effect.

## Allowed Tool Calls
{tool_mentions}

## Output Format
- Trả về cấu trúc Markdown tiêu chuẩn gồm: Tóm tắt nhận định, Bằng chứng đối chiếu (Evidence citations), Đề xuất hành động (Proposal), và Rủi ro tồn đọng.

## Fallback & Handoff
- Khi thiếu dữ liệu hoặc không đủ điều kiện an toàn, tạo thông báo Handoff đề xuất người dùng bổ sung thông tin.

## Eval Notes
- Suite: `evals/{pack["domain"]}/{pack["id"].split(".")[-1]}.yaml`
"""

    skillmd_path = pack_dir / "SKILL.md"
    with open(skillmd_path, "w", encoding="utf-8") as f:
        f.write(skillmd_content)


def main():
    print(f"Generating {len(PACKS)} Tranche A skillpacks...")
    for p in PACKS:
        write_pack(p)
    print("Done generating skillpacks.")


if __name__ == "__main__":
    main()
