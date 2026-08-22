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

## Còn thiếu

- `agentos/tools/` **chưa có MCP adapter** — xác nhận qua audit (`AI_AGENT_OS_AUDIT_NOTES.md` §0.5). Đây là feature gap thuần túy, không phải duplicate risk (agentos/ đơn giản chưa có).
- Nếu `agentos/` cần gọi MCP server, cân nhắc port cấu trúc từ `MCPToolAdapter` (production) thay vì viết lại từ đầu.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A4.
