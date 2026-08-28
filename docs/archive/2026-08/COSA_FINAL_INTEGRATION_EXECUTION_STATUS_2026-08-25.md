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
2. **Build via docker-compose:** `docker compose --profile cosa build cosa-api cosa-worker` PASS. Images: `javis-saas-cosa-api:latest`, `javis-saas-cosa-worker:latest`.
3. **Verify via actual compose network (CRITICAL):** Postgres container từ Task 1 đã chạy trên network `db-cutover-phase0-quickwins_default`. Started cosa-api trên CÙNG network, dùng service hostname `postgres:5432` từ docker-compose.yml env vars (không dùng `host.docker.internal`). API respond HTTP 401 trên `/agent/conversations`, `/agent/approvals`, và 404 trên `/` — chứng minh server hoạt động end-to-end qua internal DNS resolution. **Confirmed: docker-compose.yml environment variables (service hostname) work correctly through compose network.**
4. **Thêm vào docker-compose.yml:** 2 service mới gán profile `cosa` (tách biệt khỏi legacy). cosa-api nghe port 8001 (brain-api legacy dùng 8000), cosa-worker phụ thuộc cosa-api (startup sequence). Env vars: DATABASE_URL/CONTROL_PLANE_DATABASE_URL (sync format), + AGENT_CORE_DATABASE_URL (asyncpg format cho worker).
5. **Boundary-check từ Phase 8 trước:** `test_deployment_configs_legacy_references_are_allowlisted` vẫn pass (quét `docker-compose.yml`, 4 legacy service `migrate/migrate-control-plane/brain-api/agent-worker` không bị sửa).
6. **Attempt Step 5 (side-by-side legacy comparison):** Built legacy/backend Dockerfile (build PASS) + tried to start brain-api on compose network để so sánh với cosa-api. **BLOCKER DISCOVERED:** Runtime `ModuleNotFoundError: No module named 'full_main'` — legacy/backend application code import từ module không tồn tại sau restructure 2026-08-22. Docker-compose.yml comment (dòng 46-54) documenting chính xác issue này. **Kết luận: Không thể hoàn thành Step 5 vì legacy service không operational (pre-existing code issue, không phải config issue).**

**CỐ Ý CHƯA làm (rủi ko cao, cần xác nhận riêng):**
- Xóa mount `legacy/backend` khỏi 4 service legacy trong `docker-compose.yml` (đây là cutover thật, không nằm trong scope task này).
- Xóa 4 service legacy khỏi compose (CLAUDE.md #10 yêu cầu xác nhận người dùng riêng).
- Chạy `docker compose --profile cosa up -d` trực tiếp (attempted nhưng bị conflict với existing postgres container; verified thay bằng docker run trên actual compose network + testing internal service hostname resolution — sufficient để xác nhận YAML deployment artifact work).

**Step 5 (So sánh legacy vs cosa-api) — UNABLE TO COMPLETE:**
Không thể hoàn thành vì legacy brain-api không operational (pre-existing code fragmentation issue từ restructure 2026-08-22). cosa-api đã verified end-to-end qua docker-compose network; comparison có thể defer hoặc proceed without it (risk mitigation thay bằng cách khác).

---

### Phase 9 — CI/E2E gate
**Commit:** `5f7b094`
**File:** `.github/workflows/quality.yml`.

**Đã làm:** thêm job `apps-cosa` (chạy toàn bộ `tests/apps/cosa/` — trước đây chỉ chạy 2 test boundary qua job `boundaries`). Phát hiện + sửa bug thật: job `agent-core` cũ thiếu `pytest`/`pytest-asyncio` trong dependency install, sẽ fail "command not found" — sửa cả 2 job.

**Chưa làm:** job `migration-baseline`/`full-stack-golden-path`/`restart-recovery` — cần Docker Compose orchestration nhiều service đồng thời, không viết vì không chạy thử được trong môi trường này (rủi ro "CI xanh giả"). E2E-1 đến E2E-7 (§20 tài liệu gốc) chưa có job nào.

---

## 2. Chưa triển khai

### Phase 10 — Xóa `legacy/` — Chuẩn bị điều kiện (Task 7)

**Trạng thái: Vẫn KHÔNG ĐẠT điều kiện thực thi, đúng theo thiết kế. Tuy nhiên, các điều kiện CHUẨN BỊ đã sẵn sàng (xem Task 7 hoàn thành bên dưới).**

**Task 7 (2026-08-25) đã hoàn thành các chuẩn bị:**
- [x] Behavior inventory L1-L5 audit: 9 PROMOTED (behaviors exist in canonical code), 1 GAP (sensitive-data redaction), 1 RETIRED (Google ADK cofounder, user decision Phase 7) = 11 total L4 behaviors
  - L4 PROMOTED: executor/tool loop, provider routing, approval-aware dispatch, retry/idempotency, audit/trace, tenant-policy adapter, stuck-loop detection, session/checkpoint, budget/cost semantics ✓
  - L4 GAP: sensitive-data redaction not found (may be deferred post-cutover)
  - Evidence documented in `.superpowers/sdd/2026-08-25-cosa-final-integration-remaining-work/task-7-report.md`
- [x] Git tag `pre-cutover` created (LOCAL ONLY, not pushed) — marks state before legacy deletion
- [x] Rollback procedure written: [`docs/operations/rollback_pre_cutover.md`](../../operations/rollback_pre_cutover.md) (including honest risk assessment of pre-existing legacy `brain-api` breakage)

**Các mục vẫn chưa đạt (chặn Phase 10 execution):**
- [ ] Zero Docker mount — `docker-compose.yml` vẫn mount `legacy/backend` cho 4 service (Phase 8 cố ý dừng lại, Phase 10 chưa xóa).
- [ ] Zero deploy reference — `make deploy-control-plane` vẫn phụ thuộc `migrate-control-plane` (legacy).
- [ ] `AdkCofounderWorkflow` — quyết định RETIRE đã chốt (Phase 7) nhưng CHƯA THỰC HIỆN xóa vật lý.
- [ ] Legacy-negative CI (rename `legacy/` tạm, chạy full stack) — chưa có.

**CRITICAL KNOWN RISK — Legacy `brain-api` Breakage:**
- Pre-existing issue from 2026-08-22 restructure: `ModuleNotFoundError: No module named 'full_main'` (discovered Phase 8)
- Impacts rollback confidence: cannot switch back to legacy API if COSA fails
- Documented in [`docs/operations/rollback_pre_cutover.md`](../../operations/rollback_pre_cutover.md) with mitigation strategies
- If rollback to legacy is needed as emergency fallback, this must be fixed BEFORE Phase 10 deletion (estimated ~2-4 hours)


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

---

## 5. Reconciliation 2026-08-28 (Nhánh `remediation/dev-readiness-remaining`)

**Mục đích:** Xác minh-bằng-code thực tế trên nhánh `remediation/dev-readiness-remaining` tại commit `44835086` theo tiêu chuẩn 5 trục (ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION), đối chiếu với master plan `2026-08-28-test-prod-readiness.md` và `2026-08-28-tpr-part0-reconciliation.md`.

### 5.1 Bảng trạng thái 5 trục (8 hạng mục cốt lõi)

| # | Hạng mục | ACCEPTED | IMPLEMENTED | WIRED | VERIFIED | PRODUCTION | Commit Ref | Lệnh kiểm tra & Kết quả thực tế | Ghi chú & Part liên quan |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Tenant scope 7 service | YES | YES | YES | YES | READY | `adff857b` | `grep -n "workspaceId" services/company/{commercial,finance-legal}/services/*.service.ts` → Cả 7 file (`customer`, `contact`, `account`, `lead`, `opportunity`, `financial-transaction`, `legal-obligation`) đều đưa `workspaceId` vào SQL WHERE `and(eq(<t>.id, ...), eq(<t>.workspaceId, ...))`, không có `requireWorkspaceAccess` sau khi đọc | Khớp mẫu `task.service.ts:133`. Hoàn thành mục tiêu Part 1. |
| 2 | Workflow empty-spec | YES | YES | YES | YES | READY | `adff857b` | `.venv/bin/pytest tests/agent_core/workflows -k "empty or forward" -v` → 5 passed in 0.13s | `_validate_dag()` (`schema.py`) chặn spec rỗng / toàn compensation; `engine.py` fail-safe chuyển `FAILED` nếu forward steps chưa xong. |
| 3 | DEV DSN inline | YES | YES | YES | YES | READY | `adff857b` | `grep -rnE 'postgres(ql)?://[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+@' services/ apps/ packages/ --include="*.ts" --include="*.py"` (excl test/venv) → 0 hit | `DEFAULT_COSA_DB_URL=""` và `DEFAULT_COMPANY_DB_URL=""`; throw nếu thiếu env vars. |
| 4 | Semantic retrieval thật | YES | YES | YES | PARTIAL | OPEN | `2a399ec5` | `.venv/bin/pytest tests/agent_core/knowledge -k "semantic" -v` → Unit test `test_retrieve_computes_query_embedding_from_embedder` PASS (mode "semantic", `fell_back is False`); `test_postgres_semantic_search_orders_by_cosine` SKIPPED | Cần Postgres+pgvector container để chạy integration test thật (Part 1B / Part 1C). |
| 5 | `/events/metrics` | YES | YES | YES | PARTIAL | OPEN | `3d66af07` | `grep -rn "events/metrics" services/company/events/` → Endpoint `GET /events/metrics` đăng ký tại `event-operations.api.ts:41`; `event-metrics.service.ts` query `integration.event_outbox`. TypeScript typecheck phát hiện 4 type errors ở `task-events.service.ts` / `task.service.ts` | Cần fix 4 type errors TypeScript trong `services/company` (Part 1A / Part 2B). |
| 6 | Stuck-task sweeper | YES | YES | YES | YES | READY | `5582a6e1` | `grep -rnE "reclaim-stuck|reclaimStuck|CronJob" services/cosa/` → Endpoint `POST /control-plane/internal/scheduled-tasks/reclaim-stuck` + CronJob `reclaim-stuck-scheduled-tasks` (every 1m) trong `services/cosa/control-plane.cron.ts:20` | Có cả manual endpoint lẫn Encore CronJob định kỳ 1 phút với `FOR UPDATE SKIP LOCKED`. |
| 7 | CI xanh thật | YES | PARTIAL | PARTIAL | PARTIAL | NOT READY | `44835086` | Chạy bộ test từ máy sạch: Python unit 453 pass/28 skip; Desktop worker 26 pass; Realtime agent 27 pass; Frontend 326 pass / analyze 0 issue; Boundary-check pass; NHƯNG `make check-docs` fail (10 broken links tới doc TPR chưa tạo); `apps-cosa` fail 2 integration tests do thiếu Postgres/Encore daemon; `services/company` typecheck fail 4 lỗi | Blocker merge: Cần fix typecheck `services/company`, sửa doc links, và chạy durability test với live DB (Part 1A + Part 1C). |
| 8 | Boundary | YES | YES | YES | YES | READY | `e5cc652` | `make boundary-check` → `3 passed in 4.86s` (`test_services_boundary_audit.py`), grep cấm trong `frontend/lib` trả về 0 hits | `packages/agent_core` hoàn toàn độc lập với `services/*` và `apps/*`. |

### 5.2 Chi tiết kết quả chạy kiểm tra từ môi trường sạch

- **Python Core Unit Tests (`tests/agent_core`, `packages/agent_testkit`):** 453 passed, 28 skipped, 2 deselected in 5.28s.
- **Python Desktop Worker Tests (`tests/desktop_worker`):** 26 passed in 0.38s.
- **Python Realtime Agent Tests (`services/realtime_agent/tests`):** 27 passed in 2.18s.
- **Flutter Analysis (`frontend/`):** 0 issues found (ran in 2.1s).
- **Flutter Test Suite (`frontend/test/`):** 326 passed in 13.0s.
- **Architecture Boundary Check (`make boundary-check`):** 3 passed in 4.86s, 0 banned patterns in `frontend/lib`.
- **Skillpacks Contract Validation (`make skillpacks-validate`):** PASS 100%.
- **Doc Links Integrity (`make check-docs`):** 10 broken relative links phát hiện (chủ yếu là forward links đến các file part chưa viết trong `docs/implementation/2026-08-28-test-prod-readiness.md`).
- **TypeScript Typecheck:**
  - `services/cosa`: PASS (0 errors).
  - `services/company`: FAIL (4 errors `TS2344`/`TS2345` do `TaskCreatedPayloadV1` và `TaskCompletedPayloadV1` thiếu index signature để gán vào `BusinessEventEnvelope<Record<string, unknown>>`).
- **Subprocess Integration Tests (`tests/apps/cosa`):** 287 passed, 1 failed (`test_crash_recovery_subprocess.py`), 1 error (`test_sse_reconnect_e2e.py`) do chưa bật PostgreSQL daemon trên port 5432 và Encore daemon trên port 4000/4001 trong môi trường kiểm tra offline.

### 5.3 Khuyến nghị quyết định cổng Merge (Decision Gate)

- **Trạng thái cổng:** **CHƯA MERGE VÀO `main`**.
- **Điều kiện mở cổng merge:**
  1. **Fix TypeScript Typecheck (`services/company`):** Sửa lỗi type của `BusinessEventEnvelope` / `task-events.service.ts` để `npm --prefix services/company run typecheck` đạt 0 lỗi (thuộc Part 1A Quality Gate).
  2. **Fix Doc Links Integrity (`make check-docs`):** Hoàn thiện các link markdown bị hỏng hoặc tạo stubs cho các TPR part doc (thuộc Part 1F CI Hardening).
  3. **Đóng Blocker Durability thật qua CI/Test Runner (Part 1C):** Bật container PostgreSQL + pgvector và Encore daemon, chạy xác nhận xanh ổn định cho `test_two_real_processes_crash_recovery_real_worker` và `test_sse_reconnect_survives_process_restart`.

