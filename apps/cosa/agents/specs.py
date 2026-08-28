from __future__ import annotations

from agent_core.contracts.identity import PinnedSkillRef
from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import AutonomyLevel

__all__ = [
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
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
    ],
    prompt_ref=COSA_OPERATIONS_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Operations Specialist Agent"},
)


COSA_FINANCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.finance",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions="Chuyên viên tài chính kế toán, lập lệnh thanh toán và ghi nhận sổ cái giao dịch (Bắt buộc Human Approval cho các khoản chi).",
    capability_refs=[
        "finance.payout.execute",
        "finance.transaction.record",
    ],
    prompt_ref=COSA_FINANCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Finance Specialist Agent"},
)


COSA_MARKETING_AGENT_SPEC = AgentSpec(
    id="cosa.agents.marketing",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên chiến lược marketing và sáng tạo nội dung, xây dựng định vị sản phẩm và copywriting dựa trên bằng chứng thực nghiệm.",
    capability_refs=[
        "commercial.marketing_context.read",
        "web.search",
    ],
    pinned_skills=[
        PinnedSkillRef(
            skill_id="marketing.positioning",
            version="1.1.0",
            definition_hash="d5240b71c7958e06d84f7886614acf8646fa3c666984a5056a95b7ffa68daabb",
        ),
        PinnedSkillRef(
            skill_id="marketing.copywriting",
            version="1.1.0",
            definition_hash="cf2d69d751846b0365fbe9293144bccf8e77997165ae9cf4308fec17fbdf6a1c",
        ),
        PinnedSkillRef(
            skill_id="marketing.market-research",
            version="1.1.0",
            definition_hash="3942ecce51f3d89a709c8ae1d149f8a4538b9889ecb6cfad1c623a713a70eca5",
        ),
        PinnedSkillRef(
            skill_id="research.deep-research",
            version="1.0.0",
            definition_hash="c143319403eddd8f82dd235e61d0ef4b26ffc8f767a6876e67f0512c2bc8d960",
        ),
        PinnedSkillRef(
            skill_id="strategy.competitor-profiling",
            version="1.0.0",
            definition_hash="98e06c0d61535a1bb8398fceb30daf85c5380fd06ac843eef5dfb8eb5d026aa8",
        ),
    ],
    prompt_ref=COSA_MARKETING_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Marketing Specialist Agent"},
)
