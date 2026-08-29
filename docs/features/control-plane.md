# Control Plane

## 1. Mục đích

Mission/Task/Assignment/Worker/Lease/Schedule (Paperclip-inspired, Blueprint V2 §39/§71) — durable Postgres thay 2 class Python in-memory (`RunLeaseManager`/`RunScheduler`) từng KHÔNG có consumer production nào.

## 2. Khi nào sử dụng

**Hiện tại: chưa nên dùng cho production** — xem §15.

## 3. Không dùng cho việc gì

Không dùng thay `agent.runs` cho Run lifecycle — control plane là tầng ĐIỀU PHỐI công việc (mission/task/worker), không phải durable substrate của 1 Run cụ thể.

## 4. Kiến trúc và luồng dữ liệu

```
control_plane.missions → tasks → assignments (atomic checkout qua unique partial index)
control_plane.workers → runtime_leases (thay RunLeaseManager)
control_plane.scheduled_tasks (thay RunScheduler, coalescing_key unique)
control_plane.watches → trigger_policies, → signal_observations (dedupe)
control_plane.delivery_policies → delivery_attempts
control_plane.cost_ledger
```

6 service file TypeScript (`services/cosa/services/control-plane-*.service.ts`), 1 handler file (`control-plane.handler.ts`, toàn bộ `expose: false`).

## 5. Public contracts/API

TypeScript: xem `services/cosa/services/control-plane-{lease,scheduler,mission,worker,watch,delivery}.service.ts`. Python client: `packages/agent/runs/control_plane_client.py::HttpControlPlaneLeaseClient` (CHƯA wire làm default — chưa có consumer thật).

## 6. Database/schema liên quan

Schema `control_plane` (services/cosa/migrations 6-9) — 12 bảng.

## 7. Cấu hình

Chưa có biến môi trường riêng — dùng chung Postgres connection của `services/cosa`.

## 8. Ví dụ sử dụng

```python
client = HttpControlPlaneLeaseClient(base_url="http://control-plane.internal")
result = await client.acquire_lease(run_id, worker_id, ttl_sec=90)
```

## 9. Cách bổ sung implementation mới

Thêm endpoint mới vào `control-plane.handler.ts`, đặt tên hậu tố `Endpoint` (tránh trùng symbol với service khi `api.ts` gộp export).

## 10. Security/governance

`assignments` dùng unique partial index (`WHERE status='leased'`) để atomic checkout — DB tự chặn double-checkout, không cần lock riêng ở application layer.

## 11. Error handling

Chưa có typed error taxonomy riêng cho control-plane (khác `AgentRuntimeError` bên Python) — TypeScript service throw Error trần ở vài chỗ (vd `checkoutTask` catch unique violation, coi là expected).

## 12. Observability

Chưa wire OpenTelemetry/audit event nào.

## 13. Testing

**KHÔNG chạy được trong môi trường phát triển 2026-08-24** — không có Encore CLI (`ENCORE_RUNTIME_LIB` không set được), kể cả test TypeScript CŨ trước phiên này cũng fail cùng lý do. Verify duy nhất: `npx tsc --noEmit` (0 lỗi ứng dụng).

## 14. Migration/backward compatibility

6 migration mới (services/cosa/migrations 6-9) additive, không đụng schema `cosa` (identity/license) hiện có.

## 15. Troubleshooting / Trạng thái thật

**Chưa có consumer production nào** — build theo yêu cầu người dùng dù xác nhận trước khi code rằng tiền đề gốc ("bảo vệ logic đang chạy thật") không còn đúng (`RunLeaseManager`/`RunScheduler` chỉ có test riêng gọi, không wire vào `agent_plane.py`). Trước khi coi là production-ready: (1) chạy migration trên Postgres thật, (2) chạy Encore CLI thật để verify code compile+run đúng, (3) benchmark latency network hop Python↔Encore, (4) wire `HttpControlPlaneLeaseClient` làm default khi có consumer thật.

## 16. Definition of Done

- [x] Schema, service logic, handler, Python client, `tsc --noEmit` sạch
- [ ] Chạy Postgres/Encore CLI thật
- [ ] Benchmark latency
- [ ] Consumer thật đầu tiên
