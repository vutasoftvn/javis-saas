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

from apps.cosa.agents.catalog import public_profile_specs

__all__ = ["AGENT_PROFILE_SPECS"]

# Derived dynamically from canonical catalog (Task 4)
AGENT_PROFILE_SPECS: dict[str, AgentSpec] = public_profile_specs()
