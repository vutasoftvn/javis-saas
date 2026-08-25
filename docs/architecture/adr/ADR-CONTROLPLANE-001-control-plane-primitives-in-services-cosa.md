# ADR-CONTROLPLANE-001: Control-plane primitives (lease/scheduler/mission/task/worker) chuyển sang `services/cosa`

- **Trạng thái:** ACCEPTED (quyết định người dùng, phiên plan-mode 2026-08-24) — **triển khai đã bắt đầu (2026-08-25)**: lease/scheduler endpoint (Wave 7 H.2, TS) giờ có consumer production thật lần đầu tiên — `apps/cosa/worker/main.py` (Phase 4, `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29.6) gọi qua `HttpControlPlaneLeaseClient`/`HttpControlPlaneSchedulerClient`, wired làm default trong `build_cosa_agent_plane()`. Static type-check (`tsc --noEmit`) sạch phía TS. **CHƯA runtime-verify bằng Encore CLI/Postgres thật** (môi trường phiên viết code không có Docker/Encore CLI) — cần CI/staging chạy `encore run` + `encore test` thật trước khi coi endpoint này production-ready.
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team (quyết định do người dùng chốt trực tiếp trong phiên phân tích Blueprint V2)
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §39, §71
  - `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần H (Wave 7)
  - `CLAUDE.md` mục "Quy tắc bắt buộc" #1 ("Business truth thuộc `services/*`... Agent Platform không tự quyết định authorization hay ghi business DB trực tiếp")

---

## 1. Bối cảnh

Tính đến 2026-08-24 (HEAD `fcfe387`), các control-plane primitive kiểu Paperclip đã có 2 implementation Python **hoàn toàn in-memory**, không durable:

- `packages/agent_core/runs/leases.py` — class `RunLeaseManager`: `dict[str, RunLease]` + `asyncio.Lock`, mất toàn bộ state khi process restart, không chống split-brain giữa nhiều process/replica (chỉ chống trong 1 process nhờ `asyncio.Lock`).
- `packages/agent_core/coordination/scheduler.py` — class `RunScheduler`: coalescing work queue cũng `dict` + `asyncio.Lock`, cùng vấn đề.

`services/cosa` (TypeScript/Encore) hiện chỉ có 4 handler (agent-policy, auth, company, index) phục vụ identity/license, chưa có bất kỳ bảng hay service nào cho mission/task/worker/lease/budget/watch/signal/delivery.

Đây là mâu thuẫn với quy tắc kiến trúc đã có sẵn trong `CLAUDE.md`: "Agent Platform không tự quyết định authorization hay ghi business DB trực tiếp — mọi side effect qua Capability Layer + Governance + Audit" và 4 vùng kiến trúc quy định `packages/agent_core` (Python) không nắm giữ business/shared cross-worker truth. Lease/scheduler hiện tại đang là state chia sẻ **giữa nhiều run/worker**, không phải state nội bộ 1 run — về bản chất là control-plane truth, không phải execution-plane mechanics thuần tuý.

---

## 2. Quyết định

1. **Di chuyển ownership của lease và scheduler sang `services/cosa`** (Encore/TypeScript), dưới dạng bảng + endpoint `expose: false` mới trong service Encore hiện có (không tách app Encore riêng, trừ khi phát sinh lý do isolation cụ thể sau này).
2. **Bảng mới** (namespace `control_plane`, migration tiếp theo sau `services/cosa/migrations/5_rename_company_roles.up.sql`, số thật xác nhận lại tại thời điểm PR):
   - `control_plane.missions`, `control_plane.tasks`, `control_plane.assignments`
   - `control_plane.workers`, `control_plane.runtime_leases` (thay `RunLeaseManager`), `control_plane.scheduled_tasks` (thay `RunScheduler`)
   - `control_plane.watches`, `control_plane.trigger_policies`, `control_plane.signal_observations`
   - `control_plane.delivery_policies`, `control_plane.delivery_attempts`, `control_plane.cost_ledger`
3. **`packages/agent_core` giữ nguyên interface hiện có, đổi implementation thành client mỏng:** `RunLeaseManager.acquire_lease/renew_lease/release_lease` và `RunScheduler.schedule/poll_due_tasks/complete_task` giữ nguyên chữ ký, nhưng bên trong gọi Encore internal endpoint thay vì thao tác `dict` in-process. Call site khác trong `agent_core` không cần đổi.
4. **Boundary rõ ràng cho phần còn lại của `coordination/`:** chỉ lease/scheduler (state chia sẻ cross-run/cross-worker) chuyển đi. `coordination/{supervisor,delegate,delegation_envelope,parallel,synthesis}.py` — audit riêng từng file ở Wave 7, chỉ phần nào thực sự sở hữu state chia sẻ giữa nhiều worker mới chuyển; orchestration logic thuần trong 1 run (vd. `parallel.py` xử lý wave/reducer nội bộ 1 workflow run đang chạy) ở lại `agent_core` vì đây là execution-plane mechanics, không phải business/control-plane truth.

### Điều kiện mở lại (rollback clause)

Nếu benchmark latency (Wave 7, Phần H.4 của Reconciled Plan) cho thấy network hop Python↔Encore trên hot path resume run vượt ngưỡng chấp nhận được (chưa định lượng — cần đo trước khi chốt số, đề xuất benchmark trước khi merge cutover) và không có cách khắc phục qua caching/batching hợp lý, quyết định này phải được xem xét lại bằng ADR bổ sung — không âm thầm quay lại in-memory Python.

---

## 3. Hệ quả

### Tích cực
- Đúng nguyên tắc CLAUDE.md: business/shared-state truth thuộc `services/*`, không thuộc LLM runtime layer.
- Lease/scheduler trở thành durable, chống mất state khi restart, chống split-brain thật giữa nhiều process/replica (hiện tại `asyncio.Lock` chỉ bảo vệ trong 1 process).
- Control-plane primitive mới (mission/task/worker/watch/signal/delivery) có sẵn nền tảng Encore chuẩn (migration, Drizzle schema, handlers/services tách bạch) thay vì phải tự xây durable layer trong Python.

### Rủi ro & biện pháp
- **Thêm network hop vào hot path resume run** (Python asyncio → Encore TS RPC) — có thể tăng latency so với gọi hàm in-process trực tiếp. Biện pháp: Wave 7 bắt buộc benchmark trước/sau, thiết kế retry/circuit breaker rõ ràng trong client Python, không giả định RPC an toàn tương đương gọi hàm in-process.
- **Cutover có thể làm mất lease/task đang active nếu không cẩn thận** — biện pháp: dual-write tạm thời (feature flag chọn backend in-memory cũ / Encore mới) trong giai đoạn chuyển tiếp, chỉ xoá backend in-memory sau khi xác nhận ổn định qua ít nhất 1 chu kỳ vận hành đầy đủ.
- **`coordination/*` còn lại có thể vô tình bị chuyển nhầm** nếu không audit kỹ ranh giới "state chia sẻ cross-worker" vs "orchestration logic nội bộ 1 run" — biện pháp: audit từng file riêng lẻ trước khi chuyển bất kỳ phần nào ngoài lease/scheduler, không chuyển hàng loạt theo tên thư mục `coordination/`.

---

## 4. Việc cần cập nhật kèm theo ADR này

- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` — thêm dòng "Control Plane (lease/scheduler/mission/task)" trỏ `services/cosa` + ADR này.
- `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` mục "Trạng thái triển khai" — đánh dấu Wave 0.1 (phần control-plane) hoàn tất sau khi ADR này được người dùng review.
