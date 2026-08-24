# ADR-PROTOCOLS-MCP-A2A-AGUI: MCP/A2A/AG-UI là protocol layer, không phải authority

- **Trạng thái:** ACCEPTED — implement Wave 9 (2026-08-24)
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §10
  - `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Wave 9
  - `packages/agent_integrations/{mcp,a2a,ag_ui}/`

---

## 1. Bối cảnh

Blueprint V2 §10 quy định: MCP là tool/data transport (không phải authorization system), A2A dùng cho remote agent interoperability (child authority phải attenuate từ parent), AG-UI normalize event ra vocabulary chung cho UI client. Trước Wave 9, `packages/agent_core`/`packages/agent_integrations` chưa có implementation nào cho cả 3.

## 2. Quyết định

### MCP
`packages/agent_integrations/mcp/capability_adapter.py::register_mcp_tools()` convert MCP `tools/list` wire format (dict thô — **không** import package `mcp` chính thức, package đó yêu cầu Python 3.10+) thành `CapabilitySpec`, đăng ký vào `CapabilityRegistry` như capability nội bộ. **Không có execution path riêng cho MCP** — đăng ký vào registry chung nghĩa là mọi lời gọi tự động đi qua `CapabilityGateway.execute()` (governance/idempotency/approval/audit), đã verify bằng test.

### A2A
`packages/agent_integrations/a2a/authority.py::attenuate_authority()` — bất biến bắt buộc `Authority(child) ⊆ Authority(parent)` verify ở 4 chiều: `capability_refs` (wildcard prefix, chỉ giữ giao với parent), `max_risk` (min theo LOW<MEDIUM<HIGH<CRITICAL), `expires_at` (sớm hơn), `tenant_id` (LUÔN theo parent, không theo yêu cầu của child dù child cố tình gửi tenant khác). 5 test cố ý cho `requested` vượt parent ở từng chiều để chứng minh luôn bị chặn.

### AG-UI
`packages/agent_integrations/ag_ui/event_mapper.py::map_run_event_to_ag_ui()` map `RunEventRecord` (event_type string nội bộ COSA — KHÔNG đổi tên/version hoá theo Blueprint V2 §37 `run.started.v1` để tránh rename rủi ro trên diện rộng) sang vocabulary AG-UI best-effort (RUN_STARTED/RUN_FINISHED/RUN_ERROR/TEXT_MESSAGE_CONTENT/TOOL_CALL_START/TOOL_CALL_END/STATE_SNAPSHOT/CUSTOM). Sự kiện không có tương đương AG-UI rõ ràng (approval.required/resolved — AG-UI không có khái niệm approval sẵn) map về `CUSTOM`, giữ `cosa_event_type` gốc trong `data` để client vẫn phân biệt được.

## 3. Hệ quả & rủi ro

- **AG-UI mapping chưa certify chính thức với spec gốc** — không có kết nối tới tài liệu AG-UI spec trong môi trường phát triển phiên này, mapping dựa trên mô tả Blueprint V2 §10.3.
- **MCP adapter chưa test với MCP server thật** — chỉ test qua fake caller function; hành vi thật (timeout, protocol version negotiation) chưa verify.
- **Event taxonomy nội bộ COSA vẫn CHƯA versioned** (`run.started` không phải `run.started.v1` như Blueprint V2 §37 đề xuất) — quyết định không đổi tên hàng loạt trong Wave 9 để tránh rủi ro rename lan rộng qua nhiều file/test; nếu cần versioned taxonomy thật (đa client version khác nhau cùng lúc), cần 1 ADR/pass riêng.
