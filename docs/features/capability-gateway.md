# Capability Gateway

## 1. Mục đích

`CapabilityGateway` là **cổng thực thi capability duy nhất** của COSA — mọi side effect (đọc business data, ghi giao dịch, gọi MCP tool...) đi qua đây, không có execution path song song nào khác.

## 2. Khi nào sử dụng

Bất kỳ khi nào kernel/workflow engine cần thực thi 1 capability cụ thể (tool call). Runtime adapter (LangChain, MCP...) chỉ phát sinh **intent** (`GatewayExecutionRequest`), không tự thực thi.

## 3. Không dùng cho việc gì

Không dùng để đọc dữ liệu không qua registered capability (mọi truy cập phải khai báo `CapabilitySpec` trước).

## 4. Kiến trúc và luồng dữ liệu (pipeline 10 bước)

```
1. Resolve capability (CapabilityRegistry)
2. Validate input schema
3. Canonicalize payload, tính payload_hash
4. Construct InvocationIdentity + ExecutionTargetSnapshot
4.5. Capability readiness check
5. Atomic idempotency claim (packages/agent_core/capabilities/idempotency.py)
6. Policy evaluate
7. Accumulate governance — durable qua GovernanceStateStore (sửa 2026-08-24, trước đó in-memory riêng của Gateway)
8. Approval gate check
9-10. Execute handler, persist tool_call record, audit event
```

## 5. Public contracts/API

`agent_core.capabilities.gateway.CapabilityGateway(registry, repository, policy_evaluator, readiness_checker, governance_store)`. Method chính: `async execute(req: GatewayExecutionRequest) -> GatewayExecutionResult`.

## 6. Database/schema liên quan

`agent_core.run_tool_calls` (exact invocation ledger), `agent_core.idempotency_claims`, `agent_core_governance.invocation_governance_state`.

## 7. Cấu hình

`governance_store=` — mặc định `InMemoryGovernanceStateStore()`, production dùng `PostgresGovernanceStateStore` qua `apps/cosa/composition/agent_plane.py::build_cosa_agent_plane()`.

## 8. Ví dụ sử dụng

```python
gateway = CapabilityGateway(registry=cap_registry, repository=repo, governance_store=gov_store)
result = await gateway.execute(GatewayExecutionRequest(run_id=..., capability_id="operations.task.list", input_payload={...}))
```

## 9. Cách bổ sung implementation mới

Đăng ký `CapabilitySpec` + handler vào `CapabilityRegistry.register()`. Handler nhận `(payload, ctx) -> Any`, không tự quyết governance/idempotency — Gateway lo hết. MCP tool dùng `packages/agent_integrations/mcp/capability_adapter.py::register_mcp_tools()` để tự động có pipeline đầy đủ.

## 10. Security/governance

Governance accumulator monotonic theo `(run_id, tool_call_id)` — observation mới không làm yếu constraint đã tích luỹ. Idempotency atomic (`INSERT ... ON CONFLICT`), phân biệt "cùng invocation tiếp tục" vs "invocation khác đua giành".

## 11. Error handling

Handler exception → `tool.failed` event + idempotency claim `fail()` + `GatewayExecutionResult(status="failed")`. DENY → giải phóng idempotency claim (terminal, không kẹt "running" vĩnh viễn).

## 12. Observability

Event `tool.requested`/`policy.evaluated`/`tool.started`/`tool.completed`/`tool.failed` ghi vào `run_events`.

## 13. Testing

`tests/agent_core/capabilities/test_gateway.py` (bao gồm test concurrency thật qua `asyncio.gather` + yield point, test restart-durability governance).

## 14. Migration/backward compatibility

`governance_store` param optional, default in-memory — không breaking change cho call site cũ.

## 15. Troubleshooting

Request trả `status="in_progress"` bất ngờ: kiểm tra `tool_call_id` có bị đổi giữa các lần gọi cho CÙNG 1 invocation không (phải giữ nguyên để `IdempotencyClaimService` nhận diện đúng "cùng invocation tiếp tục").

## 16. Definition of Done

- [x] Public contract, implementation, migration, security, unit test
- [x] Governance durable (fix 2026-08-24)
- [ ] Conformance test riêng trong `agent_testkit/gateway_conformance/` (hiện test nằm ở `tests/agent_core/capabilities/`)
