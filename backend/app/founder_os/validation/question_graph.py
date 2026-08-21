"""Question Graph: câu hỏi ưu tiên cao nhất cho từng stage, versioned trong code.

Đây là dữ liệu phương pháp luận (methodology content), giống ``seed_templates.py`` —
không phải cấu hình per-workspace nên KHÔNG lưu vào ``WorkspaceTemplateVersion.config_jsonb``
(field đó đã có chủ: capability packs qua ``TemplateService``, xem
``docs/architecture/COSA_STARTUP_METHODOLOGY_INTEGRATION_ANALYSIS.md``). Question Graph
chỉ có 1 bản cho toàn hệ thống, sửa bằng code review như mọi enum/prompt khác trong module
validation, không cần workspace tự chỉnh.

Thứ tự các câu hỏi trong mỗi stage LÀ thứ tự ưu tiên mặc định. S1 theo đúng Q1-Q10 của
Supplement §7.3 (context trước customer, hành vi quá khứ trước ý kiến, urgency sau cùng).
S0/S2-S6 không có sẵn danh sách Q1..N chi tiết trong Supplement — chỉ có "câu hỏi chính" +
danh sách chủ đề (§6.2, §8-§12, Appendix A) — nên được phân rã thủ công thành node theo cùng
format và tinh thần thứ tự (context/behavior trước, tương lai/chiến lược sau cùng).
``QuestionGraphService`` chỉ lệch khỏi thứ tự này khi một assumption liên quan có risk_score
ở mức tử huyệt.
"""

from typing import Optional, TypedDict


class QuestionNode(TypedDict):
    id: str
    stage: str
    dimension: str  # AssumptionCategory value — dùng để khớp với ValidationAssumption liên quan
    question_type: str  # QuestionTypeEnum value
    prompt_vi: str
    purpose: str


# S1 — PROBLEM VALIDATION (Supplement §7.3, Q1-Q10)
QUESTION_GRAPH_S1: list[QuestionNode] = [
    {
        "id": "s1.context",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Vấn đề này xảy ra trong bối cảnh cụ thể nào (ngành, quy mô, workflow, thời điểm)?",
        "purpose": "Xác định context cụ thể trước khi đi sâu, tránh problem statement chung chung.",
    },
    {
        "id": "s1.customer",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "CUSTOMER",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Ai là người trực tiếp chịu hậu quả của vấn đề này — user, buyer, decision maker hay influencer?",
        "purpose": "Phân biệt vai trò khách hàng trước khi thu thập bằng chứng, tránh nhầm user feedback với buyer signal.",
    },
    {
        "id": "s1.last_incident",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "PAST_BEHAVIOR",
        "prompt_vi": "Lần gần nhất vấn đề này xảy ra là khi nào, và cụ thể chuyện gì đã xảy ra?",
        "purpose": "Chuyển thảo luận từ ý kiến sang hành vi thực tế đã xảy ra (Action > Words).",
    },
    {
        "id": "s1.frequency",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "PAST_BEHAVIOR",
        "prompt_vi": "Trong 30-90 ngày gần đây, vấn đề này xảy ra bao nhiêu lần?",
        "purpose": "Đo tần suất thực tế, không phải ước lượng cảm tính.",
    },
    {
        "id": "s1.severity",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "COST_DISCOVERY",
        "prompt_vi": "Lần đó gây mất bao nhiêu tiền, thời gian, sản lượng, chất lượng hoặc rủi ro?",
        "purpose": "Định lượng mức độ nghiêm trọng bằng con số cụ thể, tránh 'rất đau' mơ hồ.",
    },
    {
        "id": "s1.current_alternative",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "ALTERNATIVE_DISCOVERY",
        "prompt_vi": "Hiện tại họ đang xử lý vấn đề này bằng cách nào?",
        "purpose": "Xác định baseline cạnh tranh thật, không phải 'chưa ai làm gì'.",
    },
    {
        "id": "s1.cost_of_alternative",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "COST_DISCOVERY",
        "prompt_vi": "Cách hiện tại đang tốn của họ bao nhiêu (tiền, thời gian, nhân lực)?",
        "purpose": "So sánh chi phí giải pháp hiện tại — cơ sở để đánh giá willingness-to-switch sau này.",
    },
    {
        "id": "s1.root_cause",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Tại sao cách hiện tại chưa giải quyết được triệt để vấn đề này?",
        "purpose": "Tìm root cause thay vì dừng ở triệu chứng bề mặt.",
    },
    {
        "id": "s1.decision_process",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "CUSTOMER",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Ai là người có quyền phê duyệt việc thay đổi cách xử lý vấn đề này?",
        "purpose": "Xác định decision maker trước khi coi problem evidence là đủ cho GTM.",
    },
    {
        "id": "s1.urgency",
        "stage": "S1_PROBLEM_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "HYPOTHETICAL_FUTURE",
        "prompt_vi": "Điều gì khiến họ phải xử lý vấn đề này trong 3-12 tháng tới, thay vì để tiếp tục như cũ?",
        "purpose": "Kiểm tra urgency thật — hỏi sau cùng vì đây là câu duy nhất chạm tương lai, cần context đủ dày trước đó để tránh câu trả lời hô hào.",
    },
]

# S0 — EXPLORE (Supplement §6.2: founder fit, problem landscape, opportunity)
QUESTION_GRAPH_S0: list[QuestionNode] = [
    {
        "id": "s0.founder_fit",
        "stage": "S0_EXPLORE",
        "dimension": "FOUNDER",
        "question_type": "OPINION",
        "prompt_vi": "Vì sao bạn/team quan tâm đến vấn đề này hơn các cơ hội khác?",
        "purpose": "Kiểm tra founder fit trước khi đầu tư thời gian khám phá sâu hơn.",
    },
    {
        "id": "s0.founder_advantage",
        "stage": "S0_EXPLORE",
        "dimension": "FOUNDER",
        "question_type": "OPINION",
        "prompt_vi": "Team có access đặc biệt, hiểu biết domain, công nghệ hay quan hệ gì mà người khác không dễ có?",
        "purpose": "Xác định lợi thế cạnh tranh xuất phát điểm, không phải ý tưởng.",
    },
    {
        "id": "s0.why_now",
        "stage": "S0_EXPLORE",
        "dimension": "FOUNDER",
        "question_type": "OPINION",
        "prompt_vi": "Tại sao bây giờ là thời điểm đúng để theo đuổi cơ hội này?",
        "purpose": "Loại trừ cơ hội đã tồn tại lâu nhưng founder mới để ý, chưa chắc có driver thời điểm thật.",
    },
    {
        "id": "s0.problem_observed",
        "stage": "S0_EXPLORE",
        "dimension": "PROBLEM",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Vấn đề bạn quan sát được là gì, và nó xảy ra ở đâu (ngành, quy mô, workflow)?",
        "purpose": "Ép problem statement từ mơ hồ sang có context cụ thể.",
    },
    {
        "id": "s0.who_affected",
        "stage": "S0_EXPLORE",
        "dimension": "CUSTOMER",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Ai là người chịu hậu quả trực tiếp của vấn đề này?",
        "purpose": "Tránh customer segment chung chung kiểu 'doanh nghiệp SME'.",
    },
    {
        "id": "s0.consequence_type",
        "stage": "S0_EXPLORE",
        "dimension": "PROBLEM",
        "question_type": "COST_DISCOVERY",
        "prompt_vi": "Hậu quả của vấn đề này là tiền, thời gian, chất lượng, rủi ro hay compliance?",
        "purpose": "Phân loại impact để đánh giá mức độ đáng theo đuổi.",
    },
    {
        "id": "s0.current_handling",
        "stage": "S0_EXPLORE",
        "dimension": "PROBLEM",
        "question_type": "ALTERNATIVE_DISCOVERY",
        "prompt_vi": "Hiện tại họ đang xử lý vấn đề này bằng cách nào?",
        "purpose": "Xác định baseline cạnh tranh thật, tránh giả định 'chưa ai làm gì'.",
    },
    {
        "id": "s0.urgency_trigger",
        "stage": "S0_EXPLORE",
        "dimension": "PROBLEM",
        "question_type": "PAST_BEHAVIOR",
        "prompt_vi": "Điều gì gần đây đã thay đổi khiến vấn đề này trở nên cấp bách hơn?",
        "purpose": "Tìm market driver thật (regulation/technology/cost/behavior shift), không phải trực giác.",
    },
    {
        "id": "s0.market_driver",
        "stage": "S0_EXPLORE",
        "dimension": "TECHNICAL",
        "question_type": "OPINION",
        "prompt_vi": "Có regulation, thay đổi công nghệ, áp lực chi phí hay thay đổi hành vi nào đang tạo ra cơ hội này?",
        "purpose": "Phân biệt cơ hội có driver thật với ý tưởng chỉ dựa trên sở thích founder.",
    },
    {
        "id": "s0.evidence_check",
        "stage": "S0_EXPLORE",
        "dimension": "PROBLEM",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Ngoài trực giác của founder, có bằng chứng sơ bộ nào (desk research, chuyên gia, dữ liệu công khai) không?",
        "purpose": "Chặn việc coi founder belief là market evidence.",
    },
]

# S2 — SOLUTION VALIDATION (Supplement §8: outcome/usability/feasibility/adoption/trust)
QUESTION_GRAPH_S2: list[QuestionNode] = [
    {
        "id": "s2.outcome_hypothesis",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "SOLUTION",
        "question_type": "OPINION",
        "prompt_vi": "Nếu 5 khách hàng mục tiêu dùng thử giải pháp trong 7 ngày, bạn kỳ vọng ít nhất bao nhiêu người đạt outcome cụ thể nào, đo bằng gì?",
        "purpose": "Ép outcome hypothesis mơ hồ thành chuẩn Action/Target/Metric/Threshold/Timeframe (§8.4).",
    },
    {
        "id": "s2.usability",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "SOLUTION",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Khách hàng có thể tự hoàn thành workflow chính mà không cần hướng dẫn ngoài onboarding không?",
        "purpose": "Kiểm tra usability thật, không phải feature checklist.",
    },
    {
        "id": "s2.technical_feasibility",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "TECHNICAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Có nguyên lý kỹ thuật nào của giải pháp chưa được kiểm chứng, cần test trước khi cam kết build full?",
        "purpose": "Tách technical unknown ra khỏi solution polish, tránh premature engineering.",
    },
    {
        "id": "s2.deployment_friction",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Triển khai giải pháp này cho 1 khách hàng thật mất bao lâu, và bước nào phức tạp nhất?",
        "purpose": "Đo deployment risk trước khi cam kết pilot/scale.",
    },
    {
        "id": "s2.adoption_friction",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "SOLUTION",
        "question_type": "HYPOTHETICAL_FUTURE",
        "prompt_vi": "Điều gì có thể khiến khách hàng dùng thử rồi bỏ giữa chừng?",
        "purpose": "Chủ động tìm switching friction trước khi pilot, không đợi churn thật xảy ra.",
    },
    {
        "id": "s2.switching_cost",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "SOLUTION",
        "question_type": "COST_DISCOVERY",
        "prompt_vi": "Khách hàng phải từ bỏ hoặc thay đổi công cụ/quy trình/thói quen nào để chuyển sang giải pháp này?",
        "purpose": "Định lượng switching cost — yếu tố hay bị bỏ qua khi chỉ hỏi về tính năng.",
    },
    {
        "id": "s2.trust",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "CUSTOMER",
        "question_type": "OPINION",
        "prompt_vi": "Điều gì khiến khách hàng đủ tin tưởng để thử một giải pháp mới thay vì tiếp tục cách cũ?",
        "purpose": "Xác định rào cản niềm tin (trust) trước khi thiết kế GTM.",
    },
    {
        "id": "s2.compliance_safety",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "LEGAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Có yêu cầu an toàn hoặc compliance nào liên quan tới giải pháp này chưa được xử lý?",
        "purpose": "Chặn fatal compliance issue trước khi mở rộng pilot.",
    },
    {
        "id": "s2.smallest_experiment",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "SOLUTION",
        "question_type": "OPINION",
        "prompt_vi": "Thử nghiệm nhỏ nhất có thể chứng minh giải pháp tạo ra outcome mong muốn là gì?",
        "purpose": "Ép chọn smallest useful experiment thay vì build full trước khi có evidence.",
    },
    {
        "id": "s2.solution_bias_check",
        "stage": "S2_SOLUTION_VALIDATION",
        "dimension": "PROBLEM",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Nếu 12 tháng tới không được dùng giải pháp này, khách hàng sẽ giải quyết vấn đề bằng cách nào?",
        "purpose": "Chống Solution Bias — cùng tinh thần counter-question trong risk_service.detect_solution_bias_risk.",
    },
]

# S3 — BUSINESS VALIDATION (Supplement §9: pricing/revenue/cost/channel/delivery)
QUESTION_GRAPH_S3: list[QuestionNode] = [
    {
        "id": "s3.who_pays",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "PRICING",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Ai thực sự trả tiền cho giải pháp này, và họ trả cho outcome hay cho output?",
        "purpose": "Phân biệt user khỏi economic buyer trước khi định giá.",
    },
    {
        "id": "s3.budget_owner",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "PRICING",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Ai là người nắm ngân sách để duyệt khoản chi này?",
        "purpose": "Xác định decision maker thật trước khi thiết kế pricing/GTM.",
    },
    {
        "id": "s3.current_price",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "PRICING",
        "question_type": "COST_DISCOVERY",
        "prompt_vi": "Giá hiện tại của giải pháp thay thế (alternative) mà họ đang trả là bao nhiêu?",
        "purpose": "Có anchor giá thật để test willingness-to-pay, không định giá trong chân không.",
    },
    {
        "id": "s3.payback_expectation",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "FINANCE",
        "question_type": "OPINION",
        "prompt_vi": "Khách hàng kỳ vọng thời gian hoàn vốn (payback) bao lâu là chấp nhận được?",
        "purpose": "Kiểm tra pricing có khả thi với chu kỳ ra quyết định của khách hàng không.",
    },
    {
        "id": "s3.revenue_model",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "REVENUE",
        "question_type": "OPINION",
        "prompt_vi": "Mô hình doanh thu phù hợp nhất là one-time, recurring, usage-based hay performance-based, và vì sao?",
        "purpose": "Ép chọn revenue model dựa trên hành vi khách hàng thật, không mặc định SaaS subscription.",
    },
    {
        "id": "s3.cost_structure",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "FINANCE",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Chi phí thực tế (COGS, deployment, support) để phục vụ 1 khách hàng là bao nhiêu, dựa trên dữ liệu pilot nào?",
        "purpose": "Unit economics phải dựa trên actual cost khi đã có, không phải ước lượng.",
    },
    {
        "id": "s3.channel_fit",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "CHANNEL",
        "question_type": "OPINION",
        "prompt_vi": "Kênh bán hàng nào (founder-led, partner, digital, enterprise outbound) phù hợp nhất với khách hàng mục tiêu?",
        "purpose": "Chọn channel trước khi đầu tư GTM, tránh thử tất cả kênh cùng lúc.",
    },
    {
        "id": "s3.delivery_time",
        "stage": "S3_BUSINESS_VALIDATION",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Từ lúc ký hợp đồng tới go-live mất bao lâu, và bước nào tốn nhiều công sức custom nhất?",
        "purpose": "Xác định phần nào chuẩn hoá được để tính vào cost structure và sales cycle.",
    },
]

# S4 — GO TO MARKET (Supplement §10: ICP, trigger, channel, sales cycle, proof)
QUESTION_GRAPH_S4: list[QuestionNode] = [
    {
        "id": "s4.icp_specificity",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "CUSTOMER",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "ICP cụ thể là gì — ngành, quy mô, khu vực, use case, trigger, đặc điểm ngân sách?",
        "purpose": "Chặn ICP mơ hồ kiểu 'nhà máy' — cần đủ cụ thể để targeting thật.",
    },
    {
        "id": "s4.trigger_event",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "CUSTOMER",
        "question_type": "PAST_BEHAVIOR",
        "prompt_vi": "Sự kiện/trigger cụ thể nào khiến khách hàng chủ động đi tìm giải pháp?",
        "purpose": "Xác định trigger thật để nhắm đúng thời điểm outreach.",
    },
    {
        "id": "s4.message_resonance",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "CHANNEL",
        "question_type": "OPINION",
        "prompt_vi": "Thông điệp nào khiến khách hàng phản hồi tích cực nhất khi tiếp cận?",
        "purpose": "Tìm message-market fit trước khi scale content/outreach.",
    },
    {
        "id": "s4.channel_signal",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "CHANNEL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Kênh tiếp cận nào đang cho tín hiệu chuyển đổi tốt nhất tính đến hiện tại?",
        "purpose": "Ưu tiên đầu tư vào kênh có evidence, không dàn trải.",
    },
    {
        "id": "s4.sales_cycle",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "CHANNEL",
        "question_type": "PAST_BEHAVIOR",
        "prompt_vi": "Chu kỳ bán hàng thực tế từ lần tiếp xúc đầu tới ký hợp đồng là bao lâu?",
        "purpose": "Đo sales cycle thật thay vì ước lượng, ảnh hưởng trực tiếp tới cash planning.",
    },
    {
        "id": "s4.proof_required",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "CUSTOMER",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Khách hàng cần bằng chứng gì (case study, ROI, reference) trước khi quyết định mua?",
        "purpose": "Xác định objection/proof requirement để chuẩn bị sales asset đúng.",
    },
    {
        "id": "s4.procurement",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Quy trình procurement/duyệt mua của khách hàng có bước nào có thể làm chậm deal?",
        "purpose": "Phát hiện procurement friction sớm, tránh deal bị treo cuối kỳ.",
    },
    {
        "id": "s4.onboarding_retention",
        "stage": "S4_GO_TO_MARKET",
        "dimension": "GROWTH",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Sau khi mua, điều gì quyết định khách hàng tiếp tục dùng hay rời bỏ?",
        "purpose": "Chuẩn bị onboarding/retention playbook dựa trên nguyên nhân churn thật.",
    },
]

# S5 — OPERATE & GROW (Supplement §11.2)
QUESTION_GRAPH_S5: list[QuestionNode] = [
    {
        "id": "s5.founder_dependency",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Sales có đang phụ thuộc 100% vào founder không, hay đã có người khác chốt được deal?",
        "purpose": "Đo mức độ founder-dependent traction trước khi coi là repeatable.",
    },
    {
        "id": "s5.delivery_sop",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Delivery/triển khai đã có SOP chuẩn hoá chưa, hay mỗi khách hàng làm một kiểu?",
        "purpose": "Kiểm tra repeatability vận hành trước khi scale.",
    },
    {
        "id": "s5.margin_stability",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "FINANCE",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Margin có ổn định qua các khách hàng gần đây, hay biến động mạnh?",
        "purpose": "Phát hiện unit economics chưa ổn định trước khi tăng trưởng thêm.",
    },
    {
        "id": "s5.cash_conversion",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "FINANCE",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Cash conversion cycle và working capital hiện đang ở mức nào?",
        "purpose": "Runway/growth capital planning cần số thật, không phải ước lượng.",
    },
    {
        "id": "s5.churn",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "GROWTH",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Tỷ lệ churn hiện tại là bao nhiêu, và nguyên nhân phổ biến nhất là gì?",
        "purpose": "Growth không nghĩa gì nếu churn cao hơn tốc độ mua mới.",
    },
    {
        "id": "s5.quality_reliability",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Có vấn đề chất lượng/reliability nào lặp lại nhiều lần gần đây không?",
        "purpose": "Risk control trước khi scale traffic/khách hàng.",
    },
    {
        "id": "s5.hiring_bottleneck",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Capability nào đang thiếu nhất, cản trở tăng trưởng ngay lúc này?",
        "purpose": "Đầu vào cho Build/Hire/Contractor/Advisor/Partner/AI decision (§27).",
    },
    {
        "id": "s5.compliance_incident",
        "stage": "S5_OPERATE_GROWTH",
        "dimension": "LEGAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Có incident hoặc rủi ro compliance nào phát sinh gần đây cần xử lý chưa?",
        "purpose": "Compliance/incident handling là điều kiện exit gate sang S6.",
    },
]

# S6 — SCALE & GOVERN (Supplement §12.2 scale dimensions)
QUESTION_GRAPH_S6: list[QuestionNode] = [
    {
        "id": "s6.repeatability",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "GROWTH",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Mô hình sản phẩm/bán hàng/triển khai đã lặp lại thành công ở bao nhiêu khách hàng độc lập?",
        "purpose": "NO_SCALE_WITHOUT_REPEATABLE_CUSTOMER_EVIDENCE (§12.4).",
    },
    {
        "id": "s6.unit_economics_visibility",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "FINANCE",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Unit economics hiện có visibility rõ ràng theo từng segment/kênh chưa?",
        "purpose": "NO_GEOGRAPHIC_EXPANSION_WITHOUT_UNIT_ECONOMIC_VISIBILITY (§12.4).",
    },
    {
        "id": "s6.org_readiness",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Tổ chức hiện tại có đủ năng lực để scale mà không phá vỡ chất lượng không?",
        "purpose": "Kiểm tra org design/hiring plan trước khi cam kết scale.",
    },
    {
        "id": "s6.tech_reliability",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "TECHNICAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Hệ thống công nghệ có chịu được tải tăng trưởng dự kiến không, đã test chưa?",
        "purpose": "Reliability là 1 trong các scale dimension bắt buộc kiểm tra.",
    },
    {
        "id": "s6.compliance_scale",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "LEGAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Compliance/quy định có thay đổi gì khi mở rộng sang thị trường hoặc khu vực mới?",
        "purpose": "Regulatory expansion risk khác với compliance ở stage sớm.",
    },
    {
        "id": "s6.capital_readiness",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "FINANCE",
        "question_type": "OPINION",
        "prompt_vi": "Kế hoạch vốn cho giai đoạn scale này dựa trên use-of-funds cụ thể nào?",
        "purpose": "Financing Plan phải gắn với milestone/use-of-funds, không chỉ 'cần thêm vốn'.",
    },
    {
        "id": "s6.expansion_strategy",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "GROWTH",
        "question_type": "OPINION",
        "prompt_vi": "Hướng mở rộng ưu tiên là đào sâu vertical hiện tại, mở địa lý mới, hay mở dòng sản phẩm mới — và đánh đổi là gì?",
        "purpose": "Ép founder chọn 1 strategic path rõ ràng thay vì làm cả 3 cùng lúc (§12.3).",
    },
    {
        "id": "s6.premature_scale_check",
        "stage": "S6_SCALE_GOVERN",
        "dimension": "OPERATIONAL",
        "question_type": "CURRENT_BEHAVIOR",
        "prompt_vi": "Có dấu hiệu nào cho thấy đang scale trước khi core delivery ổn định không?",
        "purpose": "NO_PRODUCT_LINE_EXPANSION_WHILE_CORE_DELIVERY_UNSTABLE (§12.4).",
    },
]

QUESTION_GRAPH_BY_STAGE: dict[str, list[QuestionNode]] = {
    "S0_EXPLORE": QUESTION_GRAPH_S0,
    "S1_PROBLEM_VALIDATION": QUESTION_GRAPH_S1,
    "S2_SOLUTION_VALIDATION": QUESTION_GRAPH_S2,
    "S3_BUSINESS_VALIDATION": QUESTION_GRAPH_S3,
    "S4_GO_TO_MARKET": QUESTION_GRAPH_S4,
    "S5_OPERATE_GROWTH": QUESTION_GRAPH_S5,
    "S6_SCALE_GOVERN": QUESTION_GRAPH_S6,
}


def get_graph_for_stage(stage: str) -> list[QuestionNode]:
    return QUESTION_GRAPH_BY_STAGE.get(stage, [])


def get_node(node_id: str) -> Optional[QuestionNode]:
    for nodes in QUESTION_GRAPH_BY_STAGE.values():
        for node in nodes:
            if node["id"] == node_id:
                return node
    return None
