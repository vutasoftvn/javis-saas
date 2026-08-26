from __future__ import annotations

from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import AutonomyLevel

__all__ = [
    "COSA_DEFAULT_MODEL_POLICY",
    "COSA_OPERATIONS_PROMPT",
    "COSA_FINANCE_PROMPT",
    "COSA_FINANCE_AGENT_SPEC",
    "COSA_OPERATIONS_AGENT_SPEC",
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
