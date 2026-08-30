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
            skill_id="marketing.positioning",
            version="1.1.0",
            definition_hash="05f65f8c04f42a1a5dea76f3e467ee22f9f38ab803557e1df4b91981d2a55e25",
        ),
        PinnedSkillRef(
            skill_id="marketing.copywriting",
            version="1.1.0",
            definition_hash="cec633990817dd05491b19266ec1c205e33ea8a7a7cfd5a2ead8d5a9e28af3b4",
        ),
        PinnedSkillRef(
            skill_id="marketing.market-research",
            version="1.1.0",
            definition_hash="fb17a38702638b4fcff15c6e5bdf1f64a080236844811372fb8d5e63cd8a2295",
        ),
        PinnedSkillRef(
            skill_id="research.deep-research",
            version="1.0.0",
            definition_hash="4bb8d06eb82dd9bc771a9402f92ca1abaaf89a9905bb8a47a2675d9852216f77",
        ),
        PinnedSkillRef(
            skill_id="strategy.competitor-profiling",
            version="1.0.0",
            definition_hash="3f3d352844862a297603f831dfa777b83d0e91db34af958c8636e30b648d0eb9",
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
