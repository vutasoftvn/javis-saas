# Idempotency

## 1. Mục đích

Đảm bảo 1 side effect chỉ xảy ra ĐÚNG 1 LẦN dù có nhiều worker/request cùng claim, thay thế check-then-act không atomic.

## 2. Khi nào sử dụng

Tự động — mọi lời gọi `CapabilityGateway.execute()` đi qua bước 5 (atomic claim) trước khi tới policy/approval/execute.

## 3. Không dùng cho việc gì

Không thay thế `run_tool_calls` (exact invocation ledger) — 2 bảng khác mục đích: `idempotency_claims` = "ai được quyền chạy side effect", `run_tool_calls` = ledger lưu vết mọi lần gọi.

## 4. Kiến trúc và luồng dữ liệu

```
IdempotencyClaimService.try_claim(run_id, tool_call_id, capability_id, idempotency_key, payload_hash)
  → repo.claim_idempotency() [INSERT ... ON CONFLICT DO NOTHING]
  → CLAIMED (mới) | CACHED_COMPLETED (đã xong, trả cached) | RETRIED (lần trước fail, cho thử lại)
  → IN_PROGRESS (worker/invocation KHÁC đang giữ claim) — trừ khi (run_id, tool_call_id) khớp claim hiện có
    (cùng invocation resume, không phải race thật) → coi như CLAIMED
```

## 5. Public contracts/API

`agent.capabilities.idempotency.IdempotencyClaimService`, `IdempotencyOutcome` enum. `RunRepository.claim_idempotency`/`complete_idempotency_claim`/`fail_idempotency_claim`/`retry_idempotency_claim`.

## 6. Database/schema liên quan

`agent.idempotency_claims` (migration `005_idempotency_claims.sql`) — `UNIQUE (scope_kind, scope_key, capability_id, idempotency_key)`.

## 7. Cấu hình

Không có config riêng.

## 8. Ví dụ sử dụng

Xem `docs/features/capability-gateway.md` bước 5 — wiring tự động, không cần gọi trực tiếp trong code nghiệp vụ thông thường.

## 9. Cách bổ sung implementation mới

Không cần — logic nằm hoàn toàn trong Gateway + `RunRepository`.

## 10. Security/governance

Atomic — không có window race giữa check và write (khác bug cũ: `get_tool_call_by_idempotency` rồi mới `save_tool_call`).

## 11. Error handling

DENY (governance) → claim `fail()` ngay (terminal, tránh kẹt "running" vĩnh viễn chặn retry hợp lệ sau này).

## 12. Observability

Không có event riêng — quan sát qua `idempotency_claims.status`.

## 13. Testing

`tests/agent/capabilities/test_gateway.py::test_concurrent_gateway_execute_same_idempotency_key_only_one_side_effect` — 2 request độc lập, `asyncio.gather`, handler có yield point thật (`await asyncio.sleep`), chứng minh handler chỉ chạy đúng 1 lần.

## 14. Migration/backward compatibility

Migration 005 additive, không đụng `run_tool_calls`.

## 15. Troubleshooting

Request bị chặn `in_progress` sai (dù là chính invocation đó resume): kiểm tra `tool_call_id` gửi lại có khớp CHÍNH XÁC với claim gốc không.

## 16. Definition of Done

- [x] Atomic claim, outcome đầy đủ, test concurrency thật (trong giới hạn InMemory)
- [ ] Chạy trên Postgres thật với 2 connection thật đua nhau
