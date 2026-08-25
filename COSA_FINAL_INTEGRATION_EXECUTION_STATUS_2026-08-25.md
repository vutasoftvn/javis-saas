# COSA Final Integration — Execution Status (2026-08-25)

**Vai trò tài liệu:** bảng tra cứu nhanh cho phiên làm việc sau — liệt kê chính
xác đã làm gì / chưa làm gì, kèm file cụ thể và bằng chứng verify. Nội dung
tường thuật đầy đủ (lý do, phản biện, chi tiết kỹ thuật) nằm ở
`COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` mục 29
"Reconciliation Addendum" (đặc biệt §29.6) — tài liệu này KHÔNG lặp lại nội
dung đó, chỉ tóm tắt có thể scan nhanh + trỏ đúng chỗ.

**Phạm vi commit:** `c3f40fa..5f7b094` (10 commit, nhánh `main`, tất cả đã
commit — working tree sạch tại thời điểm viết tài liệu này). Chạy
`git log --oneline c3f40fa..HEAD` để xem lại nếu có commit mới hơn.

**Môi trường phiên này (quan trọng để hiểu giới hạn verify):** không có
Docker, không có Encore CLI, không có `DEEPSEEK_API_KEY`/`OPENAI_API_KEY`,
Python hệ thống chỉ 3.9 (dùng `eval_type_backport` shim qua venv scratchpad
để chạy test). Đã tự dựng `@electric-sql/pglite` (Postgres WASM thật, không
cần Docker) để verify SQL thật thay vì chỉ đọc bằng mắt — xem chi tiết trong
từng phase bên dưới.

---

## 1. Đã triển khai (Phase 0-9)

### Phase 0 — Phân tích, phản biện, khóa quyết định
**Commit:** `8053ee4`
**File:** `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` (+mục 29), `docs/architecture/adr/ADR-RUNTIME-002-*.md` (mới), `ADR-RUNTIME-001-*.md` (SUPERSEDED), `DB_FINAL_CUTOVER.md` (SUPERSEDED), `CLAUDE.md`.

**Quyết định đã chốt với người dùng (khóa cứng, không hỏi lại):**
1. ID strategy: Snowflake ID (app-generated) cho toàn bộ identity 2 domain (COSA + Company), không phải BIGSERIAL.
2. Seed `cosa.plans`: 4 tier `free/starter/pro/enterprise`.
3. CHECK `email IS NOT NULL OR phone IS NOT NULL` trên `cosa.users` và `core.user_projections`.
4. Không có data production quan trọng — baseline reset trực tiếp, không cần export/transform/import.
5. `control_plane.cost_ledger`: RETIRE, không migrate lịch sử từ `legacy.cost_ledger_entries`.
6. **Decision RUNTIME-001 = AMEND** → `ADR-RUNTIME-002`: OpenAI Agents SDK là primary execution runtime, DeepSeek là primary model provider, LangChain là optional adapter (đảo ngược ADR-RUNTIME-001 cũ).
7. **Tài liệu này supersede `DB_FINAL_CUTOVER.md`** (trùng ~80% phạm vi) — `CLAUDE.md` đã cập nhật để trỏ đúng.

---

### Phase 1 — DB baseline promotion
**Commit:** `4180127`
**File chính:** `services/cosa/migrations/1_baseline_identity_and_agent_policy.up.sql` (mới), `services/company/identity/migrations/1_baseline_workspace_user_workforce.up.sql` (mới), `services/{cosa,company/identity}/migrations/retired_pre_baseline_v1/` (migration cũ chuyển vào, nội dung bất biến), `docs/operations/migrations.md`.

**Đã verify thật:** fresh bootstrap qua `@electric-sql/pglite` — cosa (9+12 bảng) PASS, company full 4-service (32 file, đúng thứ tự `MIGRATION_DIRS`) PASS với đúng 50 bảng (khớp `DB_BASELINE_PREPARATION.md` §6). CHECK constraint + workforce invariant reject đúng input sai.

**Chưa làm:** chạy chính `node scripts/migrate.mjs` thật trên Postgres/Encore CLI thật (chỉ mô phỏng logic của nó qua pglite); Gate D (schema fingerprint tự động) chưa có tooling.

---

### Phase 2 — Identity & tenant auth
**Commit:** `19e43b6`
**File chính (mới):** `apps/cosa/auth/{jwt,cosa_client,dependency}.py`, `apps/cosa/requirements.txt`.
**File sửa:** `apps/cosa/api/routes.py` (8 endpoint wire `get_authenticated_identity`), `packages/agent_core/conversations/{models,repository}.py` (xóa default `user:default`, thêm filter `company_id`/`workspace_id` cho `list_conversations`).

**Đã verify thật:** 46 test (unit `httpx.MockTransport` + 5 test tenant-isolation qua `ASGITransport` thật — tenant B không đọc/sửa/cancel/xem-SSE/quyết-định được resource của tenant A).

**Chưa làm:** `workspace_id` chưa cross-check (Company có sẵn logic đầy đủ ở `identity/services/tenant-context.service.ts` nhưng chưa expose HTTP endpoint cho Python gọi); `list_approvals` chỉ filter `workspace_id`, chưa join `company_id`.

---

### Phase 3 — Policy wiring
**Commit:** `896e11d`
**File chính (mới):** `apps/cosa/policies/{snapshot,company_policy_client}.py`, `services/cosa/services/agent-policy.service.ts::getTenantPolicySnapshotForCaller` + endpoint mới `GET /platform/auth/me/agent-policy-snapshot`.
**File sửa:** `apps/cosa/policies/evaluator.py`, `packages/agent_core/kernel/openai_agents_kernel.py` (context giờ lấy từ `request.metadata`, không phải `dict(request.input)`), `apps/cosa/composition/agent_plane.py`, `apps/cosa/api/routes.py`.

**Đã verify thật:** 17 test Python (snapshot matching, HTTP client qua `MockTransport`, evaluator với current-gate/tenant-override). TS: `npx tsc --noEmit` sạch, nhưng **`npx vitest run` KHÔNG chạy được** (không có Encore CLI) — 4 test mới viết trong `services/cosa/tests/agent-policy.test.ts` chưa từng chạy thật.

**Chưa làm:** verify TS test thật qua `encore test`.

---

### Phase 4 — Durable dispatch/worker/lease
**Commit:** `aae4096`
**File chính (mới):** `apps/cosa/worker/{handlers,main}.py`, `packages/agent_core/coordination/control_plane_scheduler_client.py`.
**File sửa:** `apps/cosa/api/routes.py` (xóa hết `asyncio.create_task`, thay bằng `plane.scheduler.schedule(...)`), `apps/cosa/composition/agent_plane.py` (default = `HttpControlPlaneSchedulerClient`/`HttpControlPlaneLeaseClient`, không còn silent fallback in-memory).

**Đã verify thật:** 9 test (worker loop, lease mutual-exclusion giữa 2 worker_id, heartbeat renew). Phát hiện thật: lần đầu viết test mô phỏng "2 worker" sai (gọi `dispatch_one_task` 2 lần cùng process = cùng `WORKER_ID`) — tự sửa, minh chứng sống cho lý do CLAUDE.md #6 tồn tại.

**CHƯA làm — gap thật, không được coi "done":**
1. **Cross-process crash-recovery thật (CLAUDE.md #6)** — đã thử dựng `@electric-sql/pglite-socket` (Postgres wire-protocol thật) để 2 subprocess Python thật nói chuyện qua 1 DB; `asyncpg` treo vô thời hạn khi kết nối (không tương thích đủ handshake) — đã hủy sau khi xác nhận treo thật. Cần Docker Postgres thật.
2. Stuck-task sweeper chưa có (task kẹt "processing" nếu worker chết giữa chừng sau khi claim nhưng trước khi complete).
3. Deployment (docker-compose service cho `agent-worker`) — xem Phase 8.

---

### Phase 5 — Durable SSE
**Commit:** `fa5f4b4`
**File chính (mới):** `packages/agent_core/migrations/011_run_stream_events.sql`, `packages/agent_core/runs/stream_events.py`.
**File sửa:** `apps/cosa/api/event_stream.py` (viết lại hoàn toàn — xóa `_history`, `emit()`/`stream_events()` nhận `repository`), `apps/cosa/worker/handlers.py`, `apps/cosa/api/routes.py`, `apps/cosa/composition/agent_plane.py`.

**Phản biện quan trọng:** KHÔNG dùng chung `agent_core.run_events` như tài liệu gốc §7.2 đề xuất — kernel đã tự ghi vào bảng đó với vocabulary khác payload shape, ghi chung sẽ tạo event trùng khi replay. Bảng riêng `agent_conversation.run_stream_events` giữ nguyên 100% contract SSE hiện tại.

**Đã verify thật:** migration qua `pglite`; 6 test Python — quan trọng nhất: instance `CosaEventStreamManager` MỚI (mô phỏng process restart) vẫn replay đúng vì nguồn sự thật là repository, không phải RAM.

**Chưa làm:** E2E-4 thật (reconnect `Last-Event-ID` sau khi API process THẬT restart, qua uvicorn + Postgres thật).

---

### Phase 6 — Control-plane consumer verify thật
**Commit:** `a4fcddd`
**Trạng thái:** KHÔNG làm được — không có Docker/Encore CLI. Chỉ cập nhật comment/ADR cho đúng thực trạng (`leases`/`scheduled-tasks` giờ có consumer production thật từ Phase 4; `missions/tasks/workers/watches/delivery` vẫn chưa). `tsc --noEmit` vẫn sạch.

---

### Phase 7 — Runtime hardening
**Commit:** `0e7c29b`
**Quyết định đã chốt:** **RETIRE `AdkCofounderWorkflow`** (`legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py`) — không port sang canonical, xóa cùng đợt dọn `legacy/` ở Phase 10.
**Trạng thái:** Harden DeepSeek conformance/checkpoint-resume KHÔNG làm được — không có `DEEPSEEK_API_KEY`/`OPENAI_API_KEY` trong môi trường.

---

### Phase 8 — Legacy deployment convergence
**Commit:** `e5cc652`
**File:** `tests/apps/cosa/test_services_boundary_audit.py` (+`test_deployment_configs_legacy_references_are_allowlisted`).

**Đã làm:** boundary-check giờ quét `docker-compose*.yml`/`Dockerfile*`/`Makefile` cho path `legacy/`, so với allowlist theo số lượng — fail nếu có file mới/số lượng đổi. Tự kiểm chứng bằng cách chèn 1 dòng `legacy/` giả, xác nhận test fail đúng, rồi revert.

**CỐ Ý CHƯA làm — rủi ro cao, cần xác nhận riêng:** xóa mount `legacy/backend` khỏi 4 service (`migrate`, `migrate-control-plane`, `brain-api`, `agent-worker`) trong `docker-compose.yml`. Lý do: `make deploy-control-plane` (target production thật) đang phụ thuộc `migrate-control-plane` (Alembic, legacy) để migrate schema `cosa_control_plane`; không thể verify an toàn schema/dữ liệu tương đương khi không có Postgres thật trong môi trường này. Đây là thay đổi ảnh hưởng deployment thật (VPS) — không tự ý làm.

---

### Phase 9 — CI/E2E gate
**Commit:** `5f7b094`
**File:** `.github/workflows/quality.yml`.

**Đã làm:** thêm job `apps-cosa` (chạy toàn bộ `tests/apps/cosa/` — trước đây chỉ chạy 2 test boundary qua job `boundaries`). Phát hiện + sửa bug thật: job `agent-core` cũ thiếu `pytest`/`pytest-asyncio` trong dependency install, sẽ fail "command not found" — sửa cả 2 job.

**Chưa làm:** job `migration-baseline`/`full-stack-golden-path`/`restart-recovery` — cần Docker Compose orchestration nhiều service đồng thời, không viết vì không chạy thử được trong môi trường này (rủi ro "CI xanh giả"). E2E-1 đến E2E-7 (§20 tài liệu gốc) chưa có job nào.

---

## 2. Chưa triển khai

### Phase 10 — Xóa `legacy/`
**Trạng thái: KHÔNG ĐẠT điều kiện, đúng theo thiết kế (checklist §17/§24 phải 100% trước khi xóa).**

Các mục cụ thể chưa đạt:
- [ ] Zero Docker mount — `docker-compose.yml` vẫn mount `legacy/backend` cho 4 service (Phase 8 cố ý dừng lại).
- [ ] Zero deploy reference — `make deploy-control-plane` vẫn phụ thuộc `migrate-control-plane` (legacy).
- [ ] `AdkCofounderWorkflow` — quyết định RETIRE đã chốt (Phase 7) nhưng CHƯA THỰC HIỆN xóa.
- [ ] Behavior inventory L1-L5 (tài liệu gốc §23) — chưa audit/đóng dòng nào trong phiên này.
- [ ] Git tag `pre-cutover` — chưa tạo.
- [ ] Rollback procedure — chưa viết.
- [ ] Legacy-negative CI (rename `legacy/` tạm, chạy full stack) — chưa có.

### Hạ tầng thiếu, chặn nhiều việc xuyên suốt các phase
- **Docker + Encore CLI** — chặn: chạy `encore run`/`encore test` thật (Phase 3 TS test, Phase 6 toàn bộ, Phase 8 cutover, Phase 9 job orchestration).
- **Postgres thật (ngoài pglite)** — chặn: cross-process crash-recovery thật (Phase 4, CLAUDE.md #6), chạy `scripts/migrate.mjs`/`migrate.py` thật (Phase 1 Gate A/B/C/D đầy đủ).
- **`DEEPSEEK_API_KEY`/`OPENAI_API_KEY`** — chặn: Phase 7 conformance suite với model thật.

---

## 3. Việc cần làm tiếp theo (thứ tự đề xuất, cho phiên có Docker/Encore CLI/API key)

1. Chạy `node scripts/migrate.mjs` thật (cosa + company) + `python -m packages.agent_core.scripts.migrate` trên Postgres 16 thật — xác nhận baseline_v1 (Phase 1) áp dụng sạch, khớp đúng với kết quả `pglite` đã verify.
2. `encore run` local cho `services/cosa` — verify endpoint `agent-policy-snapshot` (Phase 3) và control-plane lease/scheduler (Phase 4/6) thật, chạy `encore test` cho 4 test TS mới.
3. Cross-process crash-recovery thật (Phase 4): kill worker process thật giữa run, worker process thật khác resume — dùng Postgres thật, không phải pglite/in-memory.
4. E2E-4 thật (Phase 5): API process restart, SSE reconnect `Last-Event-ID`.
5. Deployment cutover có kiểm soát (Phase 8): thêm service `migrate-cosa`/`migrate-company`/`agent-worker` (Python) MỚI vào `docker-compose.yml` song song với service cũ, xác nhận tương đương, rồi mới xóa 4 service legacy trong 1 thay đổi riêng.
6. Conformance suite DeepSeek thật (Phase 7) khi có API key.
7. Sau khi 1-6 xong: audit behavior inventory L1-L5, tag `pre-cutover`, viết rollback procedure, legacy-negative CI, rồi mới Phase 10.

---

## 4. Tài liệu/file tham chiếu nhanh

- Tường thuật đầy đủ, phản biện chi tiết từng phase: `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` mục 29 (§29.1-29.6).
- Quyết định runtime: `docs/architecture/adr/ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md`.
- Quyết định control-plane ownership: `docs/architecture/adr/ADR-CONTROLPLANE-001-control-plane-primitives-in-services-cosa.md`.
- Baseline DB (bằng chứng gốc trước khi Phase 1 promote): `docs/architecture/DB_BASELINE_PREPARATION.md`, `docs/architecture/LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md`.
- Migration mới: `services/cosa/migrations/1_baseline_identity_and_agent_policy.up.sql`, `services/company/identity/migrations/1_baseline_workspace_user_workforce.up.sql`, `packages/agent_core/migrations/011_run_stream_events.sql`.
