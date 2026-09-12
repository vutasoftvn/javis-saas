"""Ánh xạ `agent_profile` (short, human-friendly — vd `"operations"`) sang
`AgentSpec` thật — bảng DUY NHẤT quyết định agent_profile nào ứng với
AgentSpec nào (CLAUDE.md: "Chọn spec nào cho 1 agent_profile là bảng ánh xạ
tường minh... thêm agent_profile mới PHẢI thêm vào bảng này, không dựa vào so
khớp chuỗi/fallback ngầm").

Tách RIÊNG khỏi `apps/cosa/worker/handlers.py` (module gốc định nghĩa bảng
này) để 2 caller khác nhau — `apps/cosa/worker/handlers.py` (dispatch run
thật) và `apps/cosa/api/model_policy_routes.py` (REST policy settings, final-
review fix cho finding #1: map `agent_profile` REST path param sang
`agent_spec_id` thật TRƯỚC khi đọc/ghi policy) — dùng CHUNG đúng 1 bảng mà
KHÔNG kéo theo toàn bộ import chain nặng của `handlers.py` (autopilot_run,
copilot_run, wga_run, httpx, event_stream, ...). Chỉ phụ thuộc
`apps/cosa/agents/specs.py` (nhẹ, chỉ định nghĩa `AgentSpec` constant)."""

from __future__ import annotations

from agent.contracts.spec import AgentSpec

from apps.cosa.agents.specs import (
    COSA_CODING_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
    COSA_EXECUTIVE_CPO_AGENT_SPEC,
    COSA_EXECUTIVE_VPE_AGENT_SPEC,
    COSA_FINANCE_AGENT_SPEC,
    COSA_MARKETING_AGENT_SPEC,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_PRODUCT_AGENT_SPEC,
    COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC,
    COSA_SALES_AGENT_SPEC,
    COSA_STRATEGY_AGENT_SPEC,
)

__all__ = ["AGENT_PROFILE_SPECS"]

# "founder_assistant" là default thật đang được Flutter gửi cho MỌI
# conversation mới (chat_controller.dart createNewConversation() không truyền
# agentProfile) — alias sang Operations để giữ đúng hành vi hiện tại, không
# phải bug cần sửa.
AGENT_PROFILE_SPECS: dict[str, AgentSpec] = {
    "operations": COSA_OPERATIONS_AGENT_SPEC,
    "founder_assistant": COSA_OPERATIONS_AGENT_SPEC,
    "finance": COSA_FINANCE_AGENT_SPEC,
    "marketing": COSA_MARKETING_AGENT_SPEC,
    "research_intelligence": COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC,
    "strategy": COSA_STRATEGY_AGENT_SPEC,
    "customer_support": COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
    "sales": COSA_SALES_AGENT_SPEC,
    "coding": COSA_CODING_AGENT_SPEC,
    "vpe": COSA_EXECUTIVE_VPE_AGENT_SPEC,
    "product": COSA_PRODUCT_AGENT_SPEC,
    "cpo": COSA_EXECUTIVE_CPO_AGENT_SPEC,
}
