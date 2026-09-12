from __future__ import annotations

from agent.contracts.identity import PinnedSkillRef
from agent.contracts.model_policy import ModelPolicySpec
from agent.contracts.prompt import PromptSpec
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel

__all__ = [
    "COSA_CUSTOMER_SUPPORT_AGENT_SPEC",
    "COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC",
    "COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT",
    "COSA_CUSTOMER_SUPPORT_PROMPT",
    "COSA_DEFAULT_MODEL_POLICY",
    "COSA_DEPLOYED_AGENT_SPECS",
    "COSA_EXECUTIVE_CPO_AGENT_SPEC",
    "COSA_EXECUTIVE_CPO_PROMPT",
    "COSA_FINANCE_AGENT_SPEC",
    "COSA_FINANCE_PROMPT",
    "COSA_KICKOFF_SUGGESTION_AGENT_SPEC",
    "COSA_KICKOFF_SUGGESTION_PROMPT",
    "COSA_MARKETING_AGENT_SPEC",
    "COSA_MARKETING_PROMPT",
    "COSA_OPERATIONS_AGENT_SPEC",
    "COSA_OPERATIONS_PROMPT",
    "COSA_PRODUCT_AGENT_SPEC",
    "COSA_PRODUCT_PROMPT",
    "COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC",
    "COSA_RESEARCH_INTELLIGENCE_PROMPT",
    "COSA_SALES_AGENT_SPEC",
    "COSA_SALES_PROMPT",
    "COSA_STRATEGY_AGENT_SPEC",
    "COSA_STRATEGY_PROMPT",
]

# ModelPolicySpec dùng chung cho mọi COSA agent — chỉ pin provenance/lineage
# (Wave M2b); runtime thật vẫn đọc DEEPSEEK_* env qua
# apps/cosa/composition/model_provider.py::build_deepseek_model(), KHÔNG đọc
# field này. Xem Global Constraints của plan Wave M2b.
COSA_DEFAULT_MODEL_POLICY = ModelPolicySpec(
    id="cosa.model_policy.default",
    version="1.0.0",
    model="deepseek-chat",
).with_hash()

COSA_OPERATIONS_PROMPT = PromptSpec(
    id="cosa.agents.operations.prompt",
    version="1.0.0",
    text="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
).with_hash()

COSA_FINANCE_PROMPT = PromptSpec(
    id="cosa.agents.finance.prompt",
    version="1.0.0",
    text="Chuyên viên tài chính kế toán, lập lệnh thanh toán và ghi nhận sổ cái giao dịch (Bắt buộc Human Approval cho các khoản chi).",
).with_hash()

COSA_MARKETING_PROMPT = PromptSpec(
    id="cosa.agents.marketing.prompt",
    version="1.0.0",
    text="Chuyên viên chiến lược marketing và sáng tạo nội dung, xây dựng định vị sản phẩm và copywriting dựa trên bằng chứng thực nghiệm.",
).with_hash()

COSA_OPERATIONS_AGENT_SPEC = AgentSpec(
    id="cosa.agents.operations",
    # 1.2.0 (WGA int. point #3): thêm operations.task.create_draft vào
    # capability_refs để agent trong workspace_task_sweep phân rã tiếp 1 task
    # thành sub-task nháp. task.advance KHÔNG nằm đây — worker sweep gọi trực
    # tiếp qua HTTP delegation, không qua kernel.
    # 1.3.0 (Task 10, plan local-first-enterprise-knowledge): thêm
    # workspace.context.read — đây là spec thật sự chạy cho founder chat mặc
    # định (conversation_routes.py: active_agent_profile hoặc "operations"),
    # không tạo agent "founder_assistant" riêng vì role sản phẩm không khác
    # biệt thật (CLAUDE.md rule 3 — không nhân bản kiến trúc khi chưa cần).
    version="1.3.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
        "operations.task.create_draft",
        "strategy.project.get",
        "strategy.next_best_action.get",
        "strategy.evidence.list",
        "analytics.metric_contract.get",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="lifecycle.context-resolver",
            version="1.0.0",
            definition_hash="d2cd448f9012ae55f12d20b40315b79f517136fc8b55577f651dd4e36d2bcb98",
        ),
        PinnedSkillRef(
            skill_id="lifecycle.next-best-action",
            version="1.0.0",
            definition_hash="4f554c271dcd05e47dfcb4480f10e760dc02c24e0b510046b220afe415527ab9",
        ),
        PinnedSkillRef(
            skill_id="operations.weekly-review",
            version="1.0.0",
            definition_hash="cd5f56dfdc6178f0fadafbcdf585a9787eeee8393a783d9f01393a771d761f56",
        ),
        # Tranche C (2026-08-31): L1_PROPOSE/artifact-only, no runtime.tools — safe
        # to pin freely per Tranche C DoD ("Pin L0/L1 skills freely only after
        # registry acceptance"). Acceptance: tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py.
        PinnedSkillRef(
            skill_id="operations.sop-builder",
            version="1.0.0",
            definition_hash="c5afab97b0fa930e1f02f6e23a114aa8a617a59516a727d9c149c0d302913d02",
        ),
        PinnedSkillRef(
            skill_id="operations.automation-design",
            version="1.0.0",
            definition_hash="148bb889f6220dafc4aa09445ca8534e4bb551016494e78d27782c2ecfe6ba93",
        ),
    ],
    prompt_ref=COSA_OPERATIONS_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Operations Specialist Agent"},
)


COSA_FINANCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.finance",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions="Chuyên viên tài chính kế toán, theo dõi và ghi nhận sổ cái giao dịch của doanh nghiệp.",
    capability_refs=[
        "finance.connection.read",
        "finance.transaction.read",
        "finance.transaction.record",
        "finance.transaction.classify.propose",
        "finance.accounting_document.create_draft",
        "finance.accounting_document.confirm",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="finance.runway-forecast",
            version="1.0.0",
            definition_hash="4110f57eb5088169680d96c5b03e32effd59365ae6c9915697f29c4a827688ee",
        ),
        PinnedSkillRef(
            skill_id="finance.budget-guardrails",
            version="1.0.0",
            definition_hash="e06cd67cb3704a5328fd02f4f5d29ae11c1c0f44619f79015102e462cccb017f",
        ),
        # Tranche C (2026-08-31): L1_PROPOSE/artifact-only, no runtime.tools — never
        # records a transaction itself, only labels CAC/LTV inputs as assumptions.
        PinnedSkillRef(
            skill_id="finance.unit-economics",
            version="1.1.0",
            definition_hash="055a7dfc94e9bf37ad06f36bafe8fc16d8d3187a5c250fd2b7acd231a97d6706",
        ),
    ],
    prompt_ref=COSA_FINANCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Finance Specialist Agent"},
)


COSA_MARKETING_AGENT_SPEC = AgentSpec(
    id="cosa.agents.marketing",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên chiến lược marketing và sáng tạo nội dung, xây dựng định vị sản phẩm và copywriting dựa trên bằng chứng thực nghiệm.",
    capability_refs=[
        "commercial.marketing_context.read",
        "commercial.marketing_context.write",
        "campaign.asset.write",
        "experiment.write",
        "web.search",
        "knowledge.profile.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="strategy.positioning",
            version="1.1.0",
            # 2026-08-31: nội dung nghiệp vụ ICP/JTBD/Switching-forces hợp nhất từ
            # marketing.positioning (đã retire) — xem skill-source-attribution.md.
            definition_hash="e3649b7d635f2d45ae56d9e2e2780364837708652e7541db2af0eb9eee54cc92",
        ),
        PinnedSkillRef(
            skill_id="research.deep-research",
            version="1.0.0",
            definition_hash="e84d6dbfbf4d6d1f868fcdfb9287e1a6b11187a4db0f3fba32076f1be1034619",
        ),
        PinnedSkillRef(
            skill_id="strategy.competitor-profiling",
            version="1.0.0",
            definition_hash="c3bc6ce06f41005b679dd1092a9060b9cc1c3064190d16638f322c27eaeb084f",
        ),
        PinnedSkillRef(
            skill_id="marketing.channel-strategy",
            version="1.0.0",
            definition_hash="d636130cf1c7dae3bdaadf1738e476421353d16c5bae3159dfa7ec62524f80a3",
        ),
        # Tranche C (2026-08-31): all L1_PROPOSE/artifact-only, no runtime.tools —
        # safe to pin freely per Tranche C DoD ("Pin L0/L1 skills freely only after
        # registry acceptance"). Acceptance: tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py.
        PinnedSkillRef(
            skill_id="marketing.gtm-funnel",
            version="1.0.0",
            definition_hash="eead9ea09375bd5059c7dcbaf42838f9a3bc97c796917cb0e70a8576d6dc5327",
        ),
        PinnedSkillRef(
            skill_id="marketing.content-strategy",
            version="1.0.0",
            definition_hash="fa10e76a98a0ecb0ab9e71508bdb53f4c3754abffbdfb2d8831e249d0513916c",
        ),
        PinnedSkillRef(
            skill_id="marketing.landing-cro",
            version="1.0.0",
            definition_hash="37190f9c706299294ce60240515c611403ab62a459d7aae2049ae16f15331ff5",
        ),
        PinnedSkillRef(
            skill_id="marketing.paid-experiments",
            version="1.0.0",
            definition_hash="6b3b3856d6f5049f4746c82f235e101237b5df40ae71e7e6c278d89418666730",
        ),
        PinnedSkillRef(
            skill_id="marketing.brand-narrative",
            version="1.0.0",
            definition_hash="c0ed3ea3babeb1aec9a086d81d383b9371309f414125889a96a2f6443b056fd4",
        ),
        PinnedSkillRef(
            skill_id="marketing.reputation-monitoring",
            version="1.0.0",
            definition_hash="2a35c36a8890cdf6bee3a4fe0be922caa185c02603a3128c47a959db607f76e0",
        ),
    ],
    prompt_ref=COSA_MARKETING_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Marketing Specialist Agent"},
)


COSA_CUSTOMER_SUPPORT_PROMPT = PromptSpec(
    id="cosa.agents.customer_support.prompt",
    version="1.0.0",
    text=(
        "Bạn là Copilot hỗ trợ nhân sự Customer Support. Chỉ ĐỌC context thread + hồ sơ khách 360 + "
        "knowledge đã duyệt, rồi TẠO ARTIFACT: tóm tắt, bản nháp trả lời (kèm evidence_refs), intent, "
        "thông tin còn thiếu, tín hiệu bán hàng. TUYỆT ĐỐI không gửi tin, không ghi CRM, không hứa "
        "chính sách/bồi thường. Nếu khách chưa xác thực danh tính, KHÔNG tiết lộ account/invoice/PII — "
        "đề xuất xác thực hoặc chuyển người."
    ),
).with_hash()

COSA_CUSTOMER_SUPPORT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.customer_support",
    version="1.2.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,  # artifact_only: chỉ read + tạo artifact
    instructions=COSA_CUSTOMER_SUPPORT_PROMPT.text,
    capability_refs=[
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
    ],
    model_input_capability_ref=None,
    prompt_ref=COSA_CUSTOMER_SUPPORT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Customer Support Copilot"},
)

COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT = PromptSpec(
    id="cosa.agents.customer_support_autopilot.prompt",
    version="1.0.0",
    text=(
        "Autopilot hẹp: CHỈ trả lời câu hỏi khớp CHÍNH XÁC một mục knowledge đã duyệt (FAQ) hoặc thu "
        "thập thông tin qualification theo form giới hạn. Nếu độ khớp thấp / có sắc thái / khách chưa "
        "xác thực / vượt phạm vi FAQ ⇒ handoff cho người (engagement.assignment.write op=handoff_human), "
        "KHÔNG tự trả lời. Không hứa chính sách, không refund/discount, không đổi CRM."
    ),
).with_hash()

COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.customer_support_autopilot",
    version="1.2.0",
    autonomy_level=AutonomyLevel.L2_EXECUTE,  # write mode: act / execute
    instructions=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.text,
    capability_refs=[
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
        "engagement.message.send",  # REQUIRE_APPROVAL trừ template pre-authorize
        "engagement.assignment.write",  # để handoff
    ],
    model_input_capability_ref=None,
    prompt_ref=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Customer Support Autopilot (narrow FAQ)"},
)

COSA_KICKOFF_SUGGESTION_PROMPT = PromptSpec(
    id="cosa.agents.kickoff_suggestion.prompt",
    version="1.0.0",
    text="AI Co-founder gợi ý kết quả và các hành động tuần đầu tiên của vòng khởi nghiệp từ thông tin Founder cung cấp.",
).with_hash()

COSA_KICKOFF_SUGGESTION_AGENT_SPEC = AgentSpec(
    id="cosa.agents.kickoff_suggestion",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=(
        "You are an AI Co-founder assisting in analyzing and suggesting a 1-sentence outcome "
        "and 1-3 key actions for the first week of a startup cycle based on provided context. "
        "Follow the language requirement in the user prompt and return strictly JSON format."
    ),
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_KICKOFF_SUGGESTION_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Kickoff Suggestion Specialist Agent"},
)

COSA_RESEARCH_INTELLIGENCE_PROMPT = PromptSpec(
    id="cosa.agents.research_intelligence.prompt",
    version="1.0.0",
    text="Chuyên viên nghiên cứu thị trường, thu thập dữ liệu và phân tích đối thủ cạnh tranh.",
).with_hash()

COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.research_intelligence",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=COSA_RESEARCH_INTELLIGENCE_PROMPT.text,
    capability_refs=[
        "strategy.evidence.list",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_RESEARCH_INTELLIGENCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Research & Intelligence Specialist Agent"},
)

COSA_STRATEGY_PROMPT = PromptSpec(
    id="cosa.agents.strategy.prompt",
    version="1.0.0",
    text="Chuyên viên hoạch định chiến lược kinh doanh và theo dõi mục tiêu OKRs.",
).with_hash()

COSA_STRATEGY_AGENT_SPEC = AgentSpec(
    id="cosa.agents.strategy",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=COSA_STRATEGY_PROMPT.text,
    capability_refs=[
        "strategy.project.get",
        "strategy.next_best_action.get",
        "strategy.evidence.list",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_STRATEGY_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Strategy Specialist Agent"},
)

COSA_SALES_PROMPT = PromptSpec(
    id="cosa.agents.sales.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên phát triển kinh doanh và quản lý cơ hội bán hàng (B2B Sales Specialist). "
        "Chỉ đọc dữ liệu pipeline và CRM được phân quyền của Project, phân tích nhu cầu khách hàng, "
        "soạn thảo kế hoạch tiếp cận và đề xuất bước tiếp theo (L1_PROPOSE). Tuyệt đối không tự ý gửi tin nhắn, "
        "thay đổi giá hay cam kết pháp lý/tài chính ngoài phạm vi."
    ),
).with_hash()

COSA_SALES_AGENT_SPEC = AgentSpec(
    id="cosa.agents.sales",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_SALES_PROMPT.text,
    capability_refs=[
        "project.crm.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_SALES_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Sales Specialist Agent"},
)

COSA_CODING_PROMPT = PromptSpec(
    id="cosa.agents.coding.prompt",
    version="1.0.0",
    text=(
        "Kỹ sư phát triển phần mềm (Software Engineering Specialist). "
        "Chỉ đọc bằng chứng thực thi kỹ thuật (Engineering Evidence) đã được xác thực, "
        "phân tích tính khả thi kiến trúc và rủi ro triển khai (L1_PROPOSE). "
        "Tuyệt đối không có quyền shell trực tiếp, không tự ý deploy hay sửa đổi hạ tầng/codebase."
    ),
).with_hash()

COSA_CODING_AGENT_SPEC = AgentSpec(
    id="cosa.agents.coding",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_CODING_PROMPT.text,
    capability_refs=[
        "engineering.evidence.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_CODING_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Coding Specialist Agent"},
)

COSA_PRODUCT_PROMPT = PromptSpec(
    id="cosa.agents.product.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên sản phẩm (Product Specialist). "
        "Chỉ đọc snapshot Product Decision Dossier (evidence_refs, assumptions, status) đã được "
        "Founder/thành viên xác nhận, phân tích và đề xuất quyết định sản phẩm dựa trên bằng chứng "
        "hiện có (L1_PROPOSE). Tuyệt đối không tự tạo hay xác nhận (append/confirm) Product Decision "
        "Dossier — quyết định sản phẩm luôn thuộc về con người."
    ),
).with_hash()

COSA_PRODUCT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.product",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_PRODUCT_PROMPT.text,
    capability_refs=[
        "product.decision.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_PRODUCT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Product Specialist Agent"},
)

COSA_EXECUTIVE_CPO_PROMPT = PromptSpec(
    id="cosa.executive.cpo.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Sản phẩm (Chief Product Officer Advisor). "
        "Đánh giá quyết định sản phẩm, câu hỏi về bằng chứng còn thiếu và đề xuất cân nhắc trong các "
        "phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền phát hành sản phẩm, chỉnh sửa roadmap, khởi chạy experiment hay "
        "giao tiếp trực tiếp với khách hàng."
    ),
).with_hash()

COSA_EXECUTIVE_CPO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cpo",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CPO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_EXECUTIVE_CPO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA CPO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_VPE_PROMPT = PromptSpec(
    id="cosa.executive.vpe.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Phó Chủ tịch Kỹ thuật (VP Engineering Advisor). "
        "Đánh giá tính khả thi kỹ thuật, kiến trúc hệ thống, rủi ro phát hành và chất lượng kỹ thuật "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền thực thi lệnh, deploy, chỉnh sửa hạ tầng hay truy cập secrets."
    ),
).with_hash()

COSA_EXECUTIVE_VPE_AGENT_SPEC = AgentSpec(
    id="cosa.executive.vpe",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_VPE_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_EXECUTIVE_VPE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA VP Engineering Advisor", "advisory_only": True},
)

EXECUTIVE_AGENT_SPECS: dict[str, AgentSpec] = {
    "cosa.executive.vpe": COSA_EXECUTIVE_VPE_AGENT_SPEC,
    "cosa.executive.cpo": COSA_EXECUTIVE_CPO_AGENT_SPEC,
}

# Toàn bộ AgentSpec đang triển khai thật của COSA — dùng để seed toàn bộ
# runtime specs (skillpacks + prompts/model_policy/agent) và verify mọi
# pinned_skills resolve được trước khi phục vụ traffic (Wave M2b).
COSA_DEPLOYED_AGENT_SPECS = (
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_FINANCE_AGENT_SPEC,
    COSA_MARKETING_AGENT_SPEC,
    COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC,
    COSA_STRATEGY_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
    COSA_KICKOFF_SUGGESTION_AGENT_SPEC,
    COSA_SALES_AGENT_SPEC,
    COSA_CODING_AGENT_SPEC,
    COSA_PRODUCT_AGENT_SPEC,
)
