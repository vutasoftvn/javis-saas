# 04 — Tool / MCP Spec

**Blueprint gốc:** §16–§17 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** cả hai — `agentos/tools/` (nói chuyện với `services/`) và `legacy/agent_runtime`/`backend/core/tool_registry.py` (canonical production, MCP thật) không xung đột trực tiếp.

## Trạng thái hiện tại

| Thành phần | File |
|---|---|
| Tool registry (agentos) | `agentos/tools/registry.py` (`ToolRegistry`, gắn `permission_class` mỗi tool) |
| Encore client | `agentos/tools/encore_client.py` — verified thật qua HTTP với `services/` (Giai đoạn 2 pilot, xem spec 05) |
| Tool registry (production) | `backend/core/tool_registry.py` + `tool_dispatch.py` — GovernanceKernel resolve `ToolSpec` qua đây |
| MCP adapter (production) | `legacy/agent_runtime/workforce/tools/transports/mcp_adapter.py` (`MCPToolAdapter`, JSON-RPC qua httpx) |

## MCP adapter (2026-08-22 — đã đóng gap)

`agentos/tools/mcp_adapter.py` (`MCPToolAdapter`, `make_mcp_tool_spec()`) — port từ `MCPToolAdapter` production, bỏ phần phụ thuộc `ExecutionContext`/`workforce.extensions.contracts` (không có khái niệm tương đương trong `agentos/`), tự chủ qua httpx theo đúng pattern các adapter khác. `make_mcp_tool_spec()` bọc 1 MCP tool thành `ToolSpec` để đăng ký vào `ToolRegistry` như mọi tool khác (đi qua PolicyEngine bình thường). 6 test (`tests/agentos/test_mcp_adapter.py`).

## Còn thiếu

- Chưa có MCP server thật nào được cấu hình/gọi trong `agentos/` — adapter đã sẵn sàng nhưng chưa có tool binding thật dùng nó (khác với `encore_client.py` đã có pilot HTTP thật, xem spec 05).

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A4.
