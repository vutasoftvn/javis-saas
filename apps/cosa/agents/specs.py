from __future__ import annotations

from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import AutonomyLevel

__all__ = [
    "COSA_FINANCE_AGENT_SPEC",
    "COSA_OPERATIONS_AGENT_SPEC",
]

COSA_OPERATIONS_AGENT_SPEC = AgentSpec(
    id="cosa.agents.operations",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
    ],
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
    metadata={"display_name": "COSA Finance Specialist Agent"},
)
