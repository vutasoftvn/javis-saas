from __future__ import annotations

from agent.contracts.identity import PinnedSkillRef
from agent.contracts.model_policy import ModelPolicySpec
from agent.contracts.prompt import PromptSpec
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel

__all__ = [
    "COSA_CUSTOMER_SUPPORT_AGENT_SPEC",
    "COSA_CUSTOMER_SUPPORT_PROMPT",
    "COSA_DEFAULT_MODEL_POLICY",
    "COSA_FINANCE_AGENT_SPEC",
    "COSA_FINANCE_PROMPT",
    "COSA_MARKETING_AGENT_SPEC",
    "COSA_MARKETING_PROMPT",
    "COSA_OPERATIONS_AGENT_SPEC",
    "COSA_OPERATIONS_PROMPT",
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
    version="1.1.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
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
        "finance.transaction.record",
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
            version="1.0.0",
            definition_hash="f9fcc77c264b1ad08a532d856e6cb9ccc65aaf00dfe7ff1e2dcbc9cd8b053341",
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
        "web.search",
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
