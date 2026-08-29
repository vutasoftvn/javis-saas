# Memory

## 1. Mục đích

Lưu trữ trí nhớ agent (WORKING/EPISODIC/SEMANTIC/PROCEDURAL/ORGANIZATIONAL) có scope generic, provenance, lifecycle — memory KHÔNG phải business truth (nếu mâu thuẫn với Company Service, Company Service thắng).

## 2. Khi nào sử dụng

Khi agent cần nhớ thông tin xuyên nhiều Run (preference, fact đã học, entity liên quan) — không phải nơi lưu business state hiện tại.

## 3. Không dùng cho việc gì

Không dùng thay company service để lấy trạng thái business hiện tại (số dư tài khoản, trạng thái task...).

## 4. Kiến trúc và luồng dữ liệu

`MemoryStore` Protocol: `put`/`search`/`delete`. `search()` mặc định chỉ trả `status=ACTIVE` (lọc SUPERSEDED/EXPIRED/RETRACTED/ARCHIVED) — áp dụng nhất quán cả `InMemoryMemoryStore` và `PostgresMemoryStore`.

**Lịch sử kỹ thuật (Wave 8, 2026-08-24):** `PostgresMemoryStore` ban đầu pack `tenant_id/company_id/sensitivity/provenance_run_id/expires_at` vào cột `metadata` JSONB (ghi chú rõ trong code: "tránh mở migration mới trong cùng epic"). Migration `009_memory_v2.sql` mở cột thật cho các field này + thêm scope/subject/provenance/lifecycle generic, backfill từ metadata packed cũ.

## 5. Public contracts/API

`agent.memory.models.MemoryItem`, `MemoryStatus`, `agent.memory.store.MemoryStore` (Protocol), `get_memory_store()` (factory, no-silent-fallback).

## 6. Database/schema liên quan

Schema `agent_memory` (migration 003, 009): `agent_memories` (cột thật cho scope/provenance/lifecycle), `memory_embeddings` (mới — trước đây memory KHÔNG có khả năng embedding nào).

## 7. Cấu hình

`AGENT_DATABASE_URL`.

## 8. Ví dụ sử dụng

```python
store = get_memory_store()
await store.put(MemoryItem(workspace_id="ws1", agent_key="finance-cfo", kind=MemoryKind.EPISODIC, content="..."))
results = await store.search(workspace_id="ws1", agent_key="finance-cfo")
```

## 9. Cách bổ sung implementation mới

Implement `MemoryStore` Protocol đầy đủ 3 method.

## 10. Security/governance

`sensitivity` field ("normal"/"confidential"/"restricted") — chưa có enforcement tự động, chỉ là metadata hiện tại.

## 11. Error handling

`MemoryNotFoundError` khi `delete()` item không tồn tại.

## 12. Observability

Không có event riêng.

## 13. Testing

`tests/agent/memory/test_memory_v2_lifecycle.py`, `tests/agent/memory/providers/test_postgres_store.py` (cần Postgres thật, hiện skip).

## 14. Migration/backward compatibility

Migration 009 additive + backfill — không xoá cột/dữ liệu cũ.

## 15. Troubleshooting

`search()` không trả memory vừa `put()`: kiểm tra `status` có phải `ACTIVE` không (mặc định đúng, nhưng nếu set `SUPERSEDED` thủ công sẽ bị lọc).

## 16. Definition of Done

- [x] Generic scope/provenance/lifecycle, embeddings table, backfill, test lifecycle filtering
- [ ] Chạy trên Postgres thật (roundtrip cột mới)
