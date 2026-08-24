# Governance

## 1. Mục đích

Quyết định ALLOW/REQUIRE_APPROVAL/DENY cho từng invocation, tích luỹ monotonic theo `(run_id, tool_call_id)` — không cho phép observation mới làm yếu constraint đã có.

## 2. Khi nào sử dụng

Mọi lần `CapabilityGateway.execute()` (bước 6-7) và mọi lần `DurableApprovalService.verify_and_prepare_resume()` (đánh giá lại governance trước khi resume).

## 3. Không dùng cho việc gì

Không phải nơi lưu business truth — nếu governance context (tenant/principal status) mâu thuẫn với Company Service, Company Service thắng.

## 4. Kiến trúc và luồng dữ liệu

`InvocationGovernanceState.start(initial)` / `.accumulate(observation)` — pure function, immutable, dùng `combine_decisions()` để conjoin. Persist qua `GovernanceStateStore` Protocol:

```
Gateway/ApprovalService
  → governance_store.load_governance_state(run_id, tool_call_id)
  → state.accumulate(new_observation)
  → governance_store.save_governance_state(state, observation=..., source=...)
```

2 implementation: `InMemoryGovernanceStateStore` (test), `PostgresGovernanceStateStore` (production, schema `agent_core_governance`).

**Lưu ý lịch sử (2026-08-24):** `packages/agent_core/workflows/{engine,tool_step}.py` đã dùng đúng store này từ trước; `CapabilityGateway` từng có `_gov_states` dict in-memory RIÊNG, vi phạm invariant monotonic-across-restart — đã sửa để dùng chung 1 store.

## 5. Public contracts/API

`agent_core.governance.store.GovernanceStateStore` (Protocol), `agent_core.governance.store.get_governance_store()` (factory, no-silent-fallback), `agent_core.governance.accumulator.InvocationGovernanceState`.

## 6. Database/schema liên quan

Schema `agent_core_governance` (migration `002_governance_temporal_model.sql`): `invocation_governance_state`, `invocation_governance_history`, `spec_resolution_manifest_entries`, `approval_evidence`.

## 7. Cấu hình

`AGENT_CORE_DATABASE_URL` — `get_governance_store()` raise nếu thiếu và không truyền `database_url=`.

## 8. Ví dụ sử dụng

Xem `docs/features/capability-gateway.md` §8.

## 9. Cách bổ sung implementation mới

Implement `GovernanceStateStore` Protocol đầy đủ 6 method. Không tạo state riêng ngoài Protocol này cho bất kỳ subsystem nào cần governance accumulator.

## 10. Security/governance

Đây CHÍNH LÀ tầng governance — không có tầng nào khác quyết định thay.

## 11. Error handling

Không có typed error riêng — governance decision (ALLOW/REQUIRE_APPROVAL/DENY) là data, không phải exception.

## 12. Observability

`invocation_governance_history` là append-only — mọi observation ghi lại kèm `source` (vd `"capability_gateway"`, `"workflow_tool_step"`).

## 13. Testing

`tests/agent_core/governance/`, `tests/agent_core/capabilities/test_gateway.py::test_governance_accumulator_survives_gateway_restart`.

## 14. Migration/backward compatibility

`CapabilityGateway(governance_store=...)` optional param, default in-memory — backward compatible.

## 15. Troubleshooting

Governance "reset" sau restart (Run cũ không nhớ đã REQUIRE_APPROVAL): kiểm tra Gateway có được khởi tạo với `governance_store=PostgresGovernanceStateStore(...)` (không phải default in-memory) trong production.

## 16. Definition of Done

- [x] Public contract, 2 implementation, migration, test restart-durability
- [ ] Chạy trên Postgres thật
