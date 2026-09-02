# Design: Dàn E2E cross-plane tự động ("test thật") cho COSA

- **Ngày:** 2026-09-02
- **Trạng thái:** DRAFT — chờ review
- **Phạm vi chi tiết:** P1–P3 (Lớp dùng chung + Tầng 1 smoke + workstream sửa bug)
- **Phác thảo:** P4–P5 (Tầng 2 golden path + DeepSeek thật + Flutter Tier 2) — sẽ có spec/plan riêng

## 1. Bối cảnh & vấn đề

Repo đã có **ý định "test thật" được code hoá rõ**:

- Marker pytest `integration` / `live_provider` / `durability` (`pyproject.toml`).
- `scripts/check_mvp_e2e_purity.py` — chặn mock/skip/xfail/transport giả trong các file MVP E2E bắt buộc.
- Gate `make ai-compliance-production-gate` — boot **một** Encore service (`services/company`) thật qua
  `tests/e2e/conftest.py::real_company_service`, seed qua HTTP thật, không mock.
- CLAUDE.md rule 6 ("test durability phải qua process thật"), rule 11 ("không tuyên bố xong khi chưa test"),
  rule 7 ("trạng thái phải structured, không suy diễn từ text").
- Plan `docs/superpowers/plans/2026-09-01-truthful-mvp-hardening.md` (chạy release gate trên Postgres
  disposable, unique ports, fresh database) + `2026-09-02-frontend-trust-and-ux-hardening.md`
  (milestone M4 "CI has isolated end-to-end evidence").

**Hiện trạng** đạt mức **integration thật per-service**: DB Postgres (pgvector) thật ở mọi job CI có DB,
migration áp thật, một Encore service thật, durability đa tiến trình thật
(`tests/apps/cosa/worker/test_crash_recovery_subprocess.py`).

**Khoảng cách còn lại — tầng cross-plane:**

1. **Không job CI nào** chạy đồng thời `services/company` + `services/cosa` + `apps/cosa` API +
   `cosa-worker` và gọi RPC HTTP chéo thật giữa chúng. `tests/e2e/mvp_stack.py` tự khai là placeholder
   ("This module deliberately does not start processes… Release tests must use the real stack fixture
   when that broader program is implemented"); `MvpStack.migration_versions` hard-code và đã lệch thực tế.
2. `scripts/e2e/run-golden-path.sh` + `docker-compose.yml --profile e2e` (pg + `migrate-all` +
   `services-cosa` + `services-company` + `cosa-api` + `cosa-worker`) + `.env.e2e` **đã tồn tại** nhưng
   **chưa được wire vào bất kỳ job nào** trong `.github/workflows/quality.yml`. `Makefile` khai
   `.PHONY: backend-integration-test` nhưng không có recipe.
3. `COSA_MODEL_PROVIDER=fake` trên toàn bộ đường E2E. DeepSeek thật chỉ chạy job `quality-live-provider`
   trên nhánh `main`/dispatch — không nằm trong golden path.
4. Frontend "Tier 2" (Flutter thật ↔ backend thật) mô tả trong `docs/testing/frontend-integration.md`
   §1 nhưng ghi rõ **"CHƯA được dựng/verify"**. 3 integration test hiện tại chỉ chạy vs `FixtureServer`
   (loopback HTTP tối giản, không chạy business logic thật). Job `frontend-integration` chỉ chạy
   `schedule`/`dispatch`, không chặn PR.
5. **Bug tích hợp đã lộ khi chạy trên Postgres disposable, chưa fix / chưa gán owner**
   (`docs/runbooks/truthful-mvp-release-checklist.md` Task 10):
   - `ingestion_run_id` không persist vào `knowledge.source_versions`;
   - migration `019/020` tạo bảng trong schema `public` → `_grant_application_access` không cấp quyền
     → runtime lỗi `permission denied for table event_inbox`;
   - 2 test còn `INSERT` vào `cosa.companies` (đã bị migration 29 DROP);
   - 5 flutter test flaky khi chạy full-suite (pass khi chạy riêng — rò rỉ global state).

**Kết quả mong muốn:** năng lực E2E cross-plane tự động, dài hạn — tầng **smoke chặn PR** (subprocess,
nhanh, `model=fake`) + tầng **golden path đầy đủ** chạy nightly/release gồm **DeepSeek thật** +
**Flutter Tier 2** — với evidence khớp milestone M4.

## 2. Quyết định thiết kế

**Hướng lai, phân tầng; triển khai theo thứ tự "subprocess trước, Docker sau".**

| Tầng | Cách boot stack | Model | Khi chạy | Chặn PR? |
|---|---|---|---|---|
| **1 — cross-plane smoke** | 4 subprocess (`encore run` ×2 + `apps/cosa` api + worker), **không Docker**, Postgres disposable | `fake` | mọi PR | **Có** |
| **2 — golden path** | `docker-compose --profile e2e` (image production) | `fake` | nightly + `workflow_dispatch` | Không |
| **2-live — golden path + LLM thật** | như tầng 2 | `deepseek` (secret) | nightly + dispatch | Không |
| **3 — Flutter Tier 2** | compose stack + `flutter test integration_test -d macos` | `fake` | nightly + dispatch | Không |

**Lý do subprocess trước Docker:** subprocess stack rẻ + nhanh (không mất phút build Docker Encore),
cho tín hiệu cross-plane thật ngay trên PR; kỷ luật "disposable DB mỗi run, unique ports, fresh
database" (yêu cầu step 4 của `truthful-mvp-hardening.md`) dễ đảm bảo hơn; Encore CLI đã có trong CI.
Docker compose golden path chậm/flaky hơn → để nightly.

**Nguyên tắc bất biến (không được vi phạm ở mọi tầng):**

- Assert trên HTTP status / JSON envelope `{data, meta}` / SSE frame / hàng DB thật — **không** suy
  diễn từ text tự nhiên.
- Guard `E2E_TEST_SEED_ENABLED` fail-closed 2 lớp (như `ai-compliance-e2e-seed.handler.ts`).
- Thiếu `encore` CLI / Postgres không reachable → `pytest.fail(...)` với lý do + cách khắc phục,
  **không** SKIP âm thầm, **không** fallback mock.
- `scripts/check_mvp_e2e_purity.py` mở rộng phủ toàn bộ file mới — cấm `unittest.mock`,
  `Mock/MagicMock/AsyncMock/patch`, `ASGITransport/MockTransport`, `skip/skipif/xfail`,
  `sqlite:///:memory:`, class `Fake*/InMemory*/Stub*`.

## 3. Kiến trúc thư mục

```
tests/e2e/
  seed/                          # LỚP DÙNG CHUNG — seed kit thống nhất (Python, dùng cho mọi tầng)
    __init__.py
    identity.py                  # register_user(), login(), seed_workspace()  → bọc /identity/* + /identity/_e2e/*
    compliance.py                # seed_ai_compliance_baseline()  → bọc /finance-legal/ai-compliance/_e2e/seed
    entitlement.py               # grant_license(), grant_entitlement()  (qua services/cosa venture-workspace)
    agent_spec.py                # seed_minimal_agent_spec()  → publish AgentSpec + skillpack tối thiểu cho dispatch
    handles.py                   # @dataclass SeededWorkspace(workspace_id, owner_token, member_token, ...)
  scenarios/                     # LỚP DÙNG CHUNG — mỗi file 1 hàm run(stack, seeded) -> None
    auth_tenant_isolation.py     # S1
    dispatch_worker_result.py    # S2
    capability_governance.py     # S3
    outbox_relay.py              # S4
    sse_reconnect.py             # S5  (Tầng 2)
    knowledge_ingest_retrieval.py# S6  (Tầng 2)
    policy_snapshot_tenant.py    # S7  (Tầng 2)
    multi_agent_coordination.py  # S8  (Tầng 2)
  stack/
    disposable_postgres.py       # cluster tạm: 3 DB (agent/cosa/workspace) + 6 role, DB name có suffix run_id, migrate-all, teardown DROP
    subprocess_stack.py          # TẦNG 1: boot 4 process, chờ /healthz, env cross-wiring, try/finally teardown
    compose_stack.py             # TẦNG 2: wrap `docker compose --profile e2e up --wait` hoặc E2E_BASE_URL_* ngoài
    _process.py                  # helper chung: pick_free_port, popen_with_capture, wait_until_ready (rút từ conftest.py)
  conftest.py                    # + fixture real_cosa_stack (session scope) trả MvpStack; giữ real_company_service cũ
  mvp_stack.py                   # GỠ placeholder: MvpStack.from_subprocess() / .from_compose(); bỏ migration_versions hard-code
  test_cross_plane_smoke.py      # TẦNG 1: gọi S1–S4, model=fake, blocking PR
  test_golden_path.py            # TẦNG 2: gọi S1–S8, nightly
  test_golden_path_live.py       # TẦNG 2-live: subset S2/S3/S8 với model=deepseek, @pytest.mark.live_provider
```

## 4. P1 — Lớp dùng chung

### 4.1 `tests/e2e/stack/disposable_postgres.py`

- `@dataclass DisposableCluster(agent_url, cosa_url, workspace_url, agent_migrator_url, cosa_migrator_url, workspace_migrator_url)`.
- `create_disposable_cluster(run_id: str) -> DisposableCluster`:
  - Kết nối Postgres admin (`PGHOST/PGPORT/PGUSER/PGPASSWORD` như CI, mặc định `127.0.0.1:5432` `postgres`).
  - `CREATE DATABASE agent_<run_id>` / `cosa_<run_id>` / `workspace_<run_id>` (`run_id` = 8 hex ngẫu nhiên).
  - Chạy `deploy/postgres/init/01-create-app-roles.sql` (idempotent) — tạo 6 role
    `{agent,cosa,workspace}_{app,migrator}` nếu chưa có; `GRANT` trên 3 DB mới.
  - Trả URL `postgresql://<svc>_app:<pwd>@host:port/<svc>_<run_id>?sslmode=disable`.
- `apply_migrations(cluster)`: gọi tuần tự đúng thứ tự `make migrate-all`:
  `python -m packages.agent.scripts.migrate` (env `AGENT_MIGRATOR_DATABASE_URL`) →
  `node scripts/migrate.mjs` trong `services/cosa` (env `COSA_MIGRATOR_DATABASE_URL`) →
  `node scripts/migrate.mjs` trong `services/company` (env `WORKSPACE_MIGRATOR_DATABASE_URL`).
  Fail → `pytest.fail` kèm stdout/stderr.
- `drop_disposable_cluster(cluster)`: `DROP DATABASE … WITH (FORCE)` cả 3, log nếu lỗi (không raise trong teardown).
- Fixture `disposable_cluster` (session scope) — `create → apply_migrations → yield → drop` trong try/finally.
- `E2E_PG_STRATEGY`: `database` (mặc định — tạo DB mới trong cluster sẵn) hoặc `container` (Postgres
  service container riêng — chỉ dùng ở job compose).

### 4.2 `tests/e2e/seed/*`

Gom logic seed đang rải trong `tests/e2e/test_ai_compliance_company_http.py` + các endpoint `_e2e`
(`/identity/_e2e/session`, `/identity/_e2e/seed`, `/finance-legal/ai-compliance/_e2e/seed`).

- `identity.register_user(company_base_url, email=None) -> {user_id, email, password}` — `POST /identity/register`
  thật (luồng công khai), hoặc `_e2e/seed` khi cần bulk.
- `identity.login(company_base_url, email, password) -> access_token` — `POST /identity/login` (cosa phát JWT).
- `identity.seed_workspace(cosa_base_url, owner_token, name) -> {workspace_id}` — qua
  `venture-workspace.handler.ts` (provision workspace + license + entitlement).
- `entitlement.grant_entitlement(cosa_base_url, workspace_id, capability_prefix)` — bật capability cho S3.
- `agent_spec.seed_minimal_agent_spec(...)` — publish 1 AgentSpec + skillpack tối thiểu đủ để
  `control-plane` dispatch (dựa `apps/cosa/agents/seed.py`).
- `compliance.seed_ai_compliance_baseline(company_base_url)` — giữ nguyên hành vi test hiện có.
- Tất cả **idempotent**; trả `SeededWorkspace` handle.

### 4.3 `tests/e2e/mvp_stack.py` (sửa)

- `MvpStack` giữ `company / platform / agent: ServiceClient` + thêm `worker_health_url: str`.
- Thêm `@classmethod from_subprocess(cls, handles)` / `from_compose(cls, base_urls)`.
- **Xoá** `migration_versions` hard-code → thay bằng `assert_migrations_current()` gọi `migrate … --check` runtime.
- `uses_mock_transport` giữ `False` cứng; thêm assertion trong quality gate.

### 4.4 DoD P1

`PYTHONPATH=. pytest tests/e2e/seed -q` (với `disposable_cluster` + `real_cosa_stack`) tạo cluster tạm,
migrate-all, seed 1 workspace, teardown sạch — không rớt DB thừa, không treo cổng. `ruff` + `mypy` xanh.

## 5. P2 — Tầng 1: subprocess stack + S1–S4 + job CI

### 5.1 `tests/e2e/stack/subprocess_stack.py`

- `@dataclass StackHandles(company_url, cosa_url, apps_cosa_url, worker_health_url, procs: list)`.
- `boot_subprocess_stack(cluster) -> StackHandles`, thứ tự phụ thuộc:
  1. `encore run --port=<p1>` trong `services/company` — env `WORKSPACE_DATABASE_URL=cluster.workspace_url`,
     `E2E_TEST_SEED_ENABLED=1`, `COSA_URL=http://127.0.0.1:<p2>` (cho `identity/services/platform.client.ts`),
     JWT secret dev từ `.env.e2e`.
  2. `encore run --port=<p2>` trong `services/cosa` — env `COSA_DATABASE_URL=cluster.cosa_url`,
     `COMPANY_SERVICE_URL=http://127.0.0.1:<p1>`, JWT secret dev, `SNOWFLAKE_*` dev.
  3. `python -m apps.cosa.api.main` (cổng `<p3>`) — env `AGENT_DATABASE_URL=cluster.agent_url`,
     `COSA_DATABASE_URL=cluster.cosa_url`, `COMPANY_SERVICE_URL=http://127.0.0.1:<p1>`,
     `COSA_CONTROL_PLANE_URL=http://127.0.0.1:<p2>`, `COSA_MODEL_PROVIDER=fake`,
     `DEEPSEEK_API_KEY=fake-deepseek-key-for-e2e`,
     `COSA_WORKER_SERVICE_TOKEN=<mint>` (`node scripts/mint-worker-service-token.mjs` 1 lần).
  4. `python -m apps.cosa.worker.main` — env như (3) + `WORKER_ID=e2e-<run_id>`, health `<p4>`.
  - Mỗi bước: `wait_until_ready(f"{url}/healthz", proc)` (chấp nhận 200/503 như `conftest.py` hiện tại),
    timeout 60s; process chết sớm → raise kèm output đã capture.
- Teardown (`try/finally`, đảo thứ tự): `terminate` → `wait(15)` → `kill`; drain + in stdout nếu
  `returncode` bất thường (mẫu `conftest.py`).
- Fixture `real_cosa_stack` (session scope): `disposable_cluster → boot_subprocess_stack →
  MvpStack.from_subprocess(handles) → yield → teardown`. Nhánh `E2E_BASE_URL_*` (trỏ stack ngoài, bỏ boot)
  giống `real_company_service`.

### 5.2 Scenario — assert cụ thể

**S1 `auth_tenant_isolation.py`**
- `register_user` → `login` → `seed_workspace` A và B (cùng owner) + thêm member user M vào A.
- `GET /operations/tasks` token M + `X-Workspace-Id: A` → 200 `{data:[...], meta}`.
- Tạo 1 task ở A → lấy `task_id`.
- `GET /operations/tasks/<task_id>` token M + `X-Workspace-Id: B` → **404** (không leak).
- `GET /operations/tasks` không `Authorization` → **401**; token M + workspace C (không thuộc) → **403**.

**S2 `dispatch_worker_result.py`**
- Seed AgentSpec tối thiểu. `POST` tạo mission/task ở cosa (`control-plane.handler.ts` →
  `control-plane-mission.service.ts`) → nhận `run_id`.
- Poll trạng thái run tới `status == "completed"` (timeout 90s) — worker thật claim qua
  `FOR UPDATE SKIP LOCKED`, kernel `ManualToolLoopKernel` + `FakeSDKModel`.
- Company nhận signal `POST /events/internal/agent-runtime-signal`. Gửi lại **cùng identity**
  `(workspace_id, source_kind, source_id, sequence)` → `count_runtime_source_signals(...)` (đã có trong
  `conftest.py`) assert **== 1** (idempotent, unique constraint migration 33).
- Assert `run_events` / `run_tool_calls` có hàng thật trong DB `agent_<run_id>`.

**S3 `capability_governance.py`**
- `grant_entitlement(workspace, "operations")`. Từ `apps/cosa` gọi endpoint kích hoạt capability
  `operations_read` → `CapabilityGateway` chạy pipeline thật, `CompanyServiceClient` HTTP thật tới
  `services/company` (KHÔNG `StubCompanyServiceClient`).
- Assert response có dữ liệu từ company thật + audit event ghi vào bảng governance (`count > 0`).
- Case HIGH-risk: capability phân loại HIGH/CRITICAL → kết quả `REQUIRE_APPROVAL`, `approval` bind đúng
  `run_id + tool_call_id + checkpoint_ref` (đọc hàng `run_approvals`), **không** lookup theo tên action.

**S4 `outbox_relay.py`**
- Mutation company sinh domain event (vd tạo OKR) → assert hàng trong bảng outbox (`events` schema)
  trong cùng transaction.
- Cron `outbox-relay` (`services/company/events/outbox-relay.cron.ts`) đẩy sang cosa → assert cosa nhận,
  gửi lại cùng event id → không tạo bản ghi trùng.

### 5.3 CI + Makefile

- `Makefile`: target `e2e-cross-plane-smoke` →
  `PYTHONPATH=. $(PYTEST) tests/e2e/test_cross_plane_smoke.py -q --junitxml=test-results/e2e-smoke.xml`.
  Thêm vào `verify-local` (sau `e2e-test`).
- `.github/workflows/quality.yml`: job `e2e-cross-plane-smoke` (mọi push/PR, **blocking**):
  - `services: postgres: pgvector/pgvector:pg16`.
  - checkout → setup Python/Node → install Encore CLI (`curl -L https://encore.dev/install.sh | bash`)
    → install deps → `scripts/bootstrap-postgres-cluster.sh` → `make e2e-cross-plane-smoke` → upload junit.
  - `timeout-minutes: 20`.
- `scripts/check_mvp_e2e_purity.py`: thêm `tests/e2e/test_cross_plane_smoke.py` + quét
  `tests/e2e/{scenarios,stack,seed}/*.py`.
- Quality gate: assertion `mvp_stack.uses_mock_transport is False`.

### 5.4 DoD P2

`make e2e-cross-plane-smoke` local (Postgres + Encore CLI) chạy S1–S4 xanh. PR nháp → job xanh trên
Actions. `make mvp-e2e-purity-check` xanh. Test tiêu cực: inject `unittest.mock` vào 1 scenario →
purity-check **fail**. `make verify-local` xanh.

## 6. P3 — Workstream sửa bug làm-xanh-gate (song song P2, TDD: test đỏ trước)

| ID | Bug | Vị trí điều tra | Cách sửa | Evidence |
|---|---|---|---|---|
| B1 | `ingestion_run_id` không persist vào `knowledge.source_versions` | `apps/cosa/knowledge_ingestion/publish.py`, `packages/agent/knowledge/snapshot_repository.py`, migration `packages/agent/migrations/*source_versions*` | Thêm binding/cột còn thiếu hoặc sửa INSERT bỏ sót field; nếu thiếu cột → migration Expand | Test mới `tests/agent/knowledge/` assert `source_versions.ingestion_run_id` != null sau publish |
| B2 | Migration `019/020` tạo bảng ở schema `public` → `permission denied for table event_inbox` | `packages/agent/migrations/019_*`, `020_*`; `_grant_application_access` trong init SQL / migrate runner | Migration Expand mới: `ALTER TABLE public.event_inbox SET SCHEMA <đúng>` **hoặc** `GRANT` bổ sung cho `*_app` role; comment `-- migration-compat:` + evidence file `docs/runbooks/evidence/` nếu chạm destructive | `make migration-compat-check` + `make schema-fingerprint-check` xanh; runtime hết `permission denied` |
| B3 | 2 test `INSERT cosa.companies` (đã DROP migration 29) | `rg -n "cosa\.companies\|INTO companies" services tests` | Chuyển sang workspace-only seed (qua `venture-workspace` provision) | 2 test đó xanh trên disposable DB |
| B4 | 5 flutter test flaky khi full-suite | `cd frontend && flutter test --concurrency=1` vs `flutter test`; khoanh 5 file | Reset global state trong `setUp/tearDown` (`Get.reset()`, `SecureStorageService.configureForTest`) hoặc cô lập qua `flutter_test_config.dart` | `flutter test` full-suite xanh **3 lần liên tiếp** |

**DoD P3:** mỗi bug đỏ→xanh; `make migration-compat-check` + `make schema-fingerprint-check` +
`make tenancy-check` không hồi quy; `flutter test` full-suite ổn định.

## 7. P4 — Tầng 2 golden path (phác thảo, phase kế, DoD riêng)

- `tests/e2e/stack/compose_stack.py`: `boot_compose_stack()` = `docker compose --profile e2e up -d
  --build --wait` + đọc port compose (4000/4001/8001/8090) + teardown `down -v`; hoặc `E2E_BASE_URL_*`
  khi trỏ staging. Về bản chất bọc `scripts/e2e/run-golden-path.sh` cho pytest.
- `tests/e2e/test_golden_path.py`: gọi S1–S8. Scenario mới:
  - **S5 SSE reconnect/replay** — mở SSE, ngắt, reconnect kèm `Last-Event-ID` → không mất/không trùng event.
  - **S6 knowledge ingest → retrieval + citation** — upload bytes → verify MIME/size/SHA-256 →
    structured states → retrieval trả chunk + citation; workspace B không đọc data workspace A
    (khớp DoD Vault M3 trong `truthful-mvp-hardening.md`).
  - **S7 policy snapshot tenant filter** — snapshot chỉ chứa dữ liệu tenant hiện tại.
  - **S8 multi-agent coordination** — supervisor → delegate → synthesis qua `coordination/` thật.
- `.github/workflows/quality.yml`: job `e2e-golden-path` (`on: schedule` + `workflow_dispatch`), chạy
  `bash scripts/e2e/run-golden-path.sh`, upload junit + log request-id. **Không** chặn PR.
- Cập nhật `docs/testing/frontend-integration.md` + `docs/runbooks/truthful-mvp-release-checklist.md`
  đánh dấu "Encore HTTP E2E đầy đủ" đã có đường chạy.

**DoD P4:** job `e2e-golden-path` xanh trên nightly ≥3 lần liên tiếp; evidence junit lưu artifact.

### 7.1 P4-live — Tầng 2 + DeepSeek thật

- `tests/e2e/test_golden_path_live.py`: subset S2/S3/S8 với `COSA_MODEL_PROVIDER=deepseek`,
  `@pytest.mark.live_provider`, assert **kết cấu** kết quả (structured state, tool-call hợp lệ, audit),
  **không** assert nội dung văn bản model.
- Job `e2e-golden-path-live` (`schedule`/`dispatch` only, `secrets.DEEPSEEK_API_KEY`), `retries: 1`,
  tách khỏi `e2e-golden-path` để flakiness LLM không kéo phần còn lại.
- **DoD:** job xanh ≥2/3 lần nightly; chi phí token ghi nhận trong summary.

## 8. P5 — Tầng 3 Flutter Tier 2 (phác thảo)

- `frontend/integration_test/support/real_stack_config.dart` — đọc `--dart-define` base URL
  4000/4001/8001; giữ `FakeSecretStore` (không chạm Keychain).
- 3 test hiện có (`session_workspace_flow`, `remote_access_flow`, `approvals_truthfulness`) refactor chạy
  được **cả 2 chế độ**: `--dart-define=E2E_MODE=fixture` (PR nhanh) / `=real` (nightly vs compose).
- 2 test mới cần backend thật:
  - `workspace_switch_real_data_test.dart` — switch A→B với dữ liệu 2 tenant thật; assert wire không còn
    `X-Workspace-Id` của A (dùng `ApiRecorder`).
  - `remote_access_configured_mode_test.dart` — REMOTE_ACCESS/OFFLINE với `modeSource` **thật**.
    **Phụ thuộc (blocker):** cần adapter `services/cosa` trả canonical runtime config để
    `modeSource != 'inferred'` — hiện `cosa` luôn trả `inferred`. Nếu adapter chưa có, test này ở trạng
    thái "pending — chờ adapter", **KHÔNG** dùng mock để giả `configured`.
- Xử lý "chạy cả thư mục `integration_test` 1 lệnh rớt từ file thứ 2" (macOS driver): giữ vòng lặp shell
  per-file trong job CI + ghi rõ trong `docs/testing/frontend-integration.md`.
- Job `frontend-integration` mở rộng: matrix `mode=[fixture, real]`; `real` chỉ nightly.

**DoD P5:** job `frontend-integration` (mode=real) xanh nightly ≥3 lần; `docs/testing/frontend-integration.md`
đánh dấu Tier 2 "đã dựng + có evidence".

## 9. Phụ thuộc & rủi ro

- **`modeSource` adapter (`services/cosa`)** — blocker cho 1 test P5; không nằm trong P1–P3. Nếu muốn
  test đường `configured` thật, cần task riêng thêm adapter đọc canonical config.
- **Thời gian CI job `e2e-cross-plane-smoke`** — boot 4 process + migrate-all mỗi PR. Ngân sách ~20p;
  nếu vượt, cân nhắc cache Encore build hoặc giảm số scenario blocking xuống S1+S2.
- **Encore CLI version drift** — `vitest.config.ts` dò `encore-runtime.node` theo path Homebrew
  `1.58.2`; job mới phải cài qua `encore.dev/install.sh` như các job `services` hiện tại.
- **Docker-in-CI cho P4** — build image Encore chậm; đó là lý do P4 chỉ nightly.
- **Flaky LLM (P4-live)** — tách job riêng + `retries: 1`; assert kết cấu, không assert văn bản.

## 10. Deliverable

1. Spec này — commit vào `docs/superpowers/specs/`.
2. Sau khi review & duyệt → gọi skill `superpowers:writing-plans` sinh implementation plan chi tiết cho
   **P1–P3** (P4–P5 để plan riêng ở phase sau).
