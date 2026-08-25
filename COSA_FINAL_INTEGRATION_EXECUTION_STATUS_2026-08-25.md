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

**Đã verify thật:** 17 test Python (snapshot matching, HTTP client qua `MockTransport`, evaluator với current-gate/tenant-override). TS: `npx tsc --noEmit` sạch. **`encore test` PASS 18/18** — khi source `.env` root + convert `postgres:5432` (Docker) → `127.0.0.1:5432` (localhost). Tests: `agent-policy.test.ts` 9/9 PASS (policy matching, wildcard, upsert, isolation, snapshot hash), `control-plane.test.ts` 9/9 PASS (register, login, profile, company ops, membership). Endpoint `GET /platform/auth/me/agent-policy-snapshot` **VERIFIED wired sạch** — `encore run` thành công, curl trả 401 Unauthorized (expected, not 404), confirm route đã register.

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
**Commit:** `fa5f4b4` (core), `TBD` (E2E test).
**File chính (mới):** `packages/agent_core/migrations/011_run_stream_events.sql`, `packages/agent_core/runs/stream_events.py`, `apps/cosa/api/main.py` (uvicorn entry), `apps/cosa/api/test_main.py` (test entry with auth override), `tests/apps/cosa/test_sse_reconnect_e2e.py` (E2E-4 test), `tests/apps/cosa/conftest.py` (E2E fixture).
**File sửa:** `apps/cosa/api/event_stream.py` (viết lại hoàn toàn — xóa `_history`, `emit()`/`stream_events()` nhận `repository`), `apps/cosa/worker/handlers.py`, `apps/cosa/api/routes.py`, `apps/cosa/composition/agent_plane.py`.

**Phản biện quan trọng:** KHÔNG dùng chung `agent_core.run_events` như tài liệu gốc §7.2 đề xuất — kernel đã tự ghi vào bảng đó với vocabulary khác payload shape, ghi chung sẽ tạo event trùng khi replay. Bảng riêng `agent_conversation.run_stream_events` giữ nguyên 100% contract SSE hiện tại.

**Đã verify thật:** 
- Migration qua `pglite`; 6 test Python — quan trọng nhất: instance `CosaEventStreamManager` MỚI (mô phỏng process restart) vẫn replay đúng vì nguồn sự thật là repository, không phải RAM.
- **E2E-4 VERIFIED:** `test_sse_reconnect_survives_process_restart` (real uvicorn subprocesses, real Postgres): Start uvicorn subprocess 1 → read 2+ events via SSE → kill (SIGKILL) → start uvicorn subprocess 2 → reconnect with `Last-Event-ID` header → verify resumed stream picks up after last sequence (no duplicate, no gap), PIDs differ. PASS.

**Chưa làm:** None — Phase 5 COMPLETE.

---

### Phase 6 — Control-plane consumer verify thật
**Commit:** `a4fcddd`
**Trạng thái:** Sanity-check thành công (không phải E2E full). Encore CLI (v1.58.2) + Postgres thật (cosa_postgres container từ Task 1); `tsc --noEmit` sạch; `encore run` start thành công (API running http://127.0.0.1:4000); endpoint `GET /platform/auth/me/agent-policy-snapshot` respond đúng (401 auth, không 404/500); `control_plane` service wire thành công (endpoints respond, auth layer intact). Cập nhật comment/ADR cho đúng thực trạng (`leases`/`scheduled-tasks` có consumer production thật từ Phase 4; `missions/tasks/workers/watches/delivery` vẫn chưa).

---

### Phase 7 — Runtime hardening
**Commit:** `0e7c29b` (decision), `444525b` (conformance tests).
**Quyết định đã chốt:** **RETIRE `AdkCofounderWorkflow`** (`legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py`) — không port sang canonical, xóa cùng đợt dọn `legacy/` ở Phase 10.

**Trạng thái: COMPLETED — DeepSeek conformance verify thật, checkpoint-resume gap documented.**

**Đã verify thật (2 tests, 2 real API calls):**
- File: `tests/agent_core/kernel/test_deepseek_conformance.py` (2 integration tests).
- Test 1: `test_openai_agents_kernel_single_turn_with_real_deepseek` PASS (2.75s, real DeepSeek HTTP call via LiteLLM). Prompt "What is 1+1? Answer with number only." → DeepSeek response contains "2". Verified: `usage.total_tokens` populated (proves real API, not mock fallback).
- Test 2: `test_openai_agents_kernel_deepseek_model_policy_honored` PASS (2.06s, real API). Kernel passes `model` và `temperature` từ `spec.model_policy` đúng, DeepSeek accepts custom temperature=0.2.
- Cost: ~2 real API calls, ~50-80 tokens each, <$0.01 total.

**Checkpoint-Resume Gap (không phát hiện bug, tài liệu hạn chế):**
Kernel không pass `tools` parameter tới model API → DeepSeek không generate tool calls → không trigger REQUIRE_APPROVAL decision → không tạo checkpoint. Để test real checkpoint/resume end-to-end, kernel cần extend để pass tool schemas từ `model_policy` hoặc `spec.capabilities` — ngoài scope task này.

**Không thay đổi kernel source code** — conformance dùng public API, không phát hiện bug.

---

### Phase 8 — Controlled deployment cutover (add new COSA services alongside legacy)
**Commits:** `e5cc652` (boundary-check), `TBD` (this session — deployment convergence).
**Files:** 
- Created: `apps/cosa/Dockerfile.api`, `apps/cosa/Dockerfile.worker`
- Modified: `docker-compose.yml` (thêm 2 service mới `cosa-api`/`cosa-worker` với profile `cosa`, KHÔNG sửa/xóa 4 service legacy)

**Đã làm trong session này:**
1. **Viết 2 Dockerfiles (API + worker):** Copy `packages/agent_core` → `/app/agent_core` (đặt sạch cho import), install requirements qua `pip`, entrypoint: `uvicorn apps.cosa.api.main:app --host 0.0.0.0 --port 8000` (API) và `python -m apps.cosa.worker.main` (worker).
2. **Build và verify thật:** `docker compose --profile cosa build cosa-api cosa-worker` PASS. Images: `javis-saas-cosa-api:latest`, `javis-saas-cosa-worker:latest`.
3. **Kiểm tra environment + database URL:** API start thành công, respond HTTP 401 trên `/agent/conversations` (auth required, không crash). Worker start thành công, kết nối Postgres qua asyncpg (URL format `postgresql+asyncpg://...` — khác legacy sync `postgresql://...`), poll scheduler thất bại do scheduler service chưa run (expected, không phải bug).
4. **Thêm vào docker-compose.yml:** 2 service mới gán profile `cosa` (tách biệt khỏi legacy). cosa-api nghe port 8001 (brain-api legacy dùng 8000), cosa-worker phụ thuộc cosa-api (startup sequence). Env vars: DATABASE_URL/CONTROL_PLANE_DATABASE_URL (sync format), + AGENT_CORE_DATABASE_URL (asyncpg format cho worker).
5. **Boundary-check từ Phase 8 trước:** `test_deployment_configs_legacy_references_are_allowlisted` vẫn pass (quét `docker-compose.yml`, 4 legacy service `migrate/migrate-control-plane/brain-api/agent-worker` không bị sửa).

**CỐ Ý CHƯA làm (rủi ro cao, cần xác nhận riêng):**
- Xóa mount `legacy/backend` khỏi 4 service legacy trong `docker-compose.yml` (đây là cutover thật, không nằm trong scope task này).
- Xóa 4 service legacy khỏi compose (CLAUDE.md #10 yêu cầu xác nhận người dùng riêng).
- Chạy `docker compose --profile cosa up` toàn bộ end-to-end với tất cả service (chỉ test build + manual start qua docker run vì postgres container đã tồn tại).

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
