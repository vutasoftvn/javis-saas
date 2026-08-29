# Integration: MCP

## 1. Mục đích

Convert MCP tool discovery (`tools/list` wire format) thành `CapabilitySpec`, đăng ký vào `CapabilityRegistry` — MCP là transport/discovery, KHÔNG phải authorization system.

## 2. Khi nào sử dụng

Khi cần expose tool từ 1 MCP server bên ngoài như capability nội bộ, đi qua đúng governance/idempotency/approval.

## 3. Không dùng cho việc gì

Không tự thực thi side effect ngoài `CapabilityGateway` — `register_mcp_tools()` chỉ đăng ký, không tạo execution path riêng.

## 4. Kiến trúc và luồng dữ liệu

```
mcp_tool_to_capability_spec(tool_dict) → CapabilitySpec (risk mặc định MEDIUM, không phải LOW)
register_mcp_tools(registry, tools, caller) → đăng ký handler gọi caller(tool_name, args)
  → mọi execute() đi qua CapabilityGateway.execute() như capability nội bộ
```

**Không import package `mcp` chính thức** — package đó yêu cầu Python 3.10+ (môi trường phát triển 2026-08-24 chỉ có 3.9). Nhận `tool` dưới dạng dict thô đúng wire format JSON, không phụ thuộc API cụ thể của 1 SDK version.

## 5. Public contracts/API

`agent_integrations.mcp.capability_adapter.{mcp_tool_to_capability_spec, register_mcp_tools, McpToolCaller}`.

## 6. Database/schema liên quan

Không có — dùng chung `CapabilityRegistry`/`agent.run_tool_calls`.

## 7. Cấu hình

`caller: McpToolCaller` — client MCP thật tiêm từ ngoài, không hardcode 1 transport (stdio/SSE/HTTP) cụ thể.

## 8. Ví dụ sử dụng

```python
tools = await mcp_client.list_tools()  # client MCP thật, không thuộc package này
register_mcp_tools(cap_registry, tools, caller=mcp_client.call_tool)
```

## 9. Cách bổ sung implementation mới

Viết `McpToolCaller` thật gọi 1 MCP client SDK cụ thể — adapter này không đổi.

## 10. Security/governance

Risk mặc định MEDIUM (không phải LOW) — tool từ server ngoài chưa có evidence an toàn như capability nội bộ COSA.

## 11. Error handling

Không có exception riêng — lỗi từ `caller()` propagate qua Gateway pipeline bình thường (→ `tool.failed` event).

## 12. Observability

Cùng event taxonomy Gateway (`tool.requested`, `tool.completed`, ...) + `metadata.mcp_tool_name`/`mcp_source`.

## 13. Testing

`packages/agent_testkit/protocol_conformance/test_mcp_capability_adapter.py` — verify wire format mapping + tool đăng ký chạy đúng qua Gateway pipeline thật (governance/idempotency/ledger).

## 14. Migration/backward compatibility

Package mới, không dependency (nhận dict thô).

## 15. Troubleshooting

`mcp` package không cài được: dùng Python 3.10+ hoặc tiếp tục dùng adapter dict-thô này (không phụ thuộc SDK).

## 16. Definition of Done

- [x] Adapter + test qua Gateway pipeline thật
- [ ] Test với MCP server thật (timeout, protocol version negotiation chưa verify)
