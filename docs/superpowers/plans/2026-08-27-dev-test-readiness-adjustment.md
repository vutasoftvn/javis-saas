# Dev/Test Readiness Adjustment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa COSA về trạng thái có thể chạy development và kiểm thử một cách lặp lại được, fail-closed và không tạo kết quả “xanh giả”.

**Architecture:** Development chuẩn chạy PostgreSQL, MinIO và LiveKit trong Docker; Company Encore, COSA Control Plane Encore, FastAPI và worker chạy trên host để dùng các URL loopback nhất quán. Production giữ triển khai tách rời nhưng bắt buộc khai báo URL, token service và migration theo thứ tự trước khi bật process.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy/asyncpg, TypeScript strict, Encore, Drizzle, PostgreSQL 16, Docker Compose, Flutter, pytest, Vitest và GitHub Actions.

**Spec:** `CLAUDE.md` cùng audit tĩnh ngày 2026-08-27 trong repository hiện tại. Tài liệu này tự chứa các quyết định và acceptance criteria cần để thực thi, không phụ thuộc vào tài liệu lịch sử đã bị di chuyển hoặc loại khỏi working tree.

## Global Constraints

- Giữ bốn vùng kiến trúc trong `CLAUDE.md`: business truth ở `services/*`; `packages/agent_core` không import `services/*` hoặc `apps/*`.
- Mọi API đọc/ghi conversation, run, approval và SSE phải truy vấn với `company_id + workspace_id`; không chỉ kiểm tra sau một truy vấn theo ID.
- Không thêm fallback production cho database URL, service URL, token hoặc model key; thiếu cấu hình phải fail-fast.
- Không đưa secret thật vào source, Compose, `.env.example`, log hay artifact CI.
- Migration là immutable, có checksum và phải chạy trước process tiêu thụ schema.
- Test PR không được phụ thuộc API model có phí; live-provider test là một gate riêng có secret và được kích hoạt có chủ đích.
- Mọi comment mới giải thích lý do phải viết bằng tiếng Việt theo `CLAUDE.md`.

---

## File map

| File | Trách nhiệm sau điều chỉnh |
|---|---|
| `services/cosa/storage/control-plane-schema.ts` | Khai báo chính xác kiểu mảng cho JSONB connector scopes/actions. |
| `services/cosa/services/token.service.ts` | Kiểu hóa TTL token worker để TypeScript strict pass. |
| `services/cosa/handlers/workspace-connector.handler.ts` | Trả DTO connector có kiểu dữ liệu đã xác nhận. |
| `packages/agent_core/runs/repository.py` | Bổ sung read/list approval và run có tenant scope ở tầng repository. |
| `packages/agent_core/capabilities/approval_service.py` | Chuyển tiếp filter company/workspace xuống repository. |
| `apps/cosa/api/routes.py` | Chỉ dùng scoped repository methods cho resource tenant-bound. |
| `Makefile` | Tách infrastructure, migration, dev stack, test tier và deploy gate. |
| `docker-compose.yml`, `services/docker-compose.yml` | Khai báo topology/container environment rõ ràng; không dựa vào localhost sai ngữ cảnh. |
| `.env.example`, `services/.env.example` | Ghi rõ contract biến môi trường cho host development và process production. |
| `scripts/check-dev-preflight.sh` | Kiểm tra môi trường, schema, token, URL và health trước khi chạy development. |
| `services/cosa/scripts/migrate.mjs` | Bắt buộc control-plane database URL thay vì dùng credential fallback trong source. |
| `.github/workflows/quality.yml` | Chia gate deterministic và live integration; cài Python đúng cho boundary job. |
| `tests/apps/cosa/test_tenant_isolation.py` | Chứng minh scoped reads và approval list không rò tenant khi workspace ID trùng. |
| `services/cosa/tests/workspace-connector.test.ts` | Bảo vệ DTO scopes/actions sau khi khai báo JSONB typed. |
| `frontend/lib/modules/chat/views/session_view_widget.dart` | Xóa lint analyzer hiện hữu. |

---

### Task 1: Khôi phục static quality gates của Control Plane

**Files:**

- Modify: `services/cosa/storage/control-plane-schema.ts:178,197`
- Modify: `services/cosa/services/token.service.ts:1,58-71`
- Modify: `services/cosa/handlers/workspace-connector.handler.ts:112-151`
- Modify: `services/cosa/package.json`
- Modify: `services/cosa/tests/workspace-connector.test.ts`
- Modify: `frontend/lib/modules/chat/views/session_view_widget.dart:100`

**Interfaces:**

- Produces `ConnectorAuthorizationResponse.grantedScopes: string[]` and `SessionConnectorGrantResponse.allowedActions: string[]` without a type assertion at the HTTP handler boundary.
- Produces a `typecheck` package script that executes `tsc --noEmit` under the strict project configuration.
- Produces a Flutter analyzer result with zero diagnostics.

- [ ] **Step 1: Add the two failing connector response assertions**

Extend `services/cosa/tests/workspace-connector.test.ts` with the existing install → authorize → grant flow. Assert the exact response array values:

```ts
expect(authorization.grantedScopes).toEqual(["read", "metadata"]);
expect(grant.allowedActions).toEqual(["sandbox.read"]);
```

- [ ] **Step 2: Verify the current static failure**

Run: `cd services/cosa && npx tsc --noEmit`

Expected: three errors: two `unknown` JSONB response fields and one `expiresIn: string` overload error.

- [ ] **Step 3: Declare typed JSONB columns and typed JWT TTL**

Use Drizzle’s column type at the schema boundary, not a handler-only cast:

```ts
grantedScopes: jsonb("granted_scopes").$type<string[]>().default([]).notNull(),
allowedActions: jsonb("allowed_actions").$type<string[]>().default([]).notNull(),
```

Import `SignOptions` as a type in `token.service.ts` and narrow the parameter:

```ts
export function signWorkerServiceToken(
  workerId: string,
  workspaceId?: string,
  expiresIn: SignOptions["expiresIn"] = "1d",
): string
```

Do not convert unknown values with `as string[]` in a handler; the database schema owns their static type.

- [ ] **Step 4: Expose and run the static gates**

Add this script to `services/cosa/package.json`:

```json
"typecheck": "tsc --noEmit"
```

Replace `separatorBuilder: (_, __)` with `separatorBuilder: (_, _)` in the Flutter widget.

Run:

```bash
(cd services/cosa && npm run typecheck)
(cd services/company && npx tsc --noEmit)
(cd frontend && flutter analyze)
```

Expected: all commands exit `0`.

- [ ] **Step 5: Run focused and full service tests**

Run:

```bash
(cd services/cosa && encore test)
make services-test
```

Expected: connector lifecycle tests preserve array values and both Encore applications pass.

- [ ] **Step 6: Commit**

```bash
git add services/cosa/storage/control-plane-schema.ts services/cosa/services/token.service.ts services/cosa/handlers/workspace-connector.handler.ts services/cosa/package.json services/cosa/tests/workspace-connector.test.ts frontend/lib/modules/chat/views/session_view_widget.dart
git commit -m "fix: restore control-plane static quality gates"
```

### Task 2: Enforce tenant scope in data access, not after lookup

**Files:**

- Modify: `packages/agent_core/runs/repository.py:28-71,102-104,343-365,771-810`
- Modify: `packages/agent_core/capabilities/approval_service.py:158-159`
- Modify: `apps/cosa/api/routes.py:119-136,182-238,295-428,431-445`
- Modify: `tests/apps/cosa/test_tenant_isolation.py`
- Modify: `tests/agent_core/runs/test_repository.py`

**Interfaces:**

- Produces `RunRepository.get_scoped_run(run_id, company_id, workspace_id) -> Optional[RunRecord]`.
- Changes `RunRepository.list_pending_approvals` and `DurableApprovalService.list_pending_approvals` to accept `company_id` and `workspace_id` as named optional parameters.
- Uses `ConversationRepository.get_scoped_conversation` for get, update and message routes.

- [ ] **Step 1: Write database-agnostic failing tests**

Add a repository test that stores two runs with the same workspace ID but different company IDs and verifies that the scoped read returns only the caller’s run. Add an API test that creates pending approvals for both companies and asserts tenant A sees only approval A:

```python
assert [item["approval_id"] for item in response.json()["items"]] == [approval_a.approval_id]
```

- [ ] **Step 2: Verify that the approval-list test fails**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_tenant_isolation.py -q
PYTHONPATH=. .venv/bin/pytest tests/agent_core/runs/test_repository.py -q
```

Expected: the new collision test fails because the current approval query filters only `workspace_id`.

- [ ] **Step 3: Add scoped repository queries**

Implement `get_scoped_run` in both in-memory and Postgres repositories. The Postgres query must contain all predicates in SQL:

```sql
WHERE run_id = :run_id
  AND company_id = :company_id
  AND workspace_id = :workspace_id
```

Change the approval query to join `agent_core.approvals` with `agent_core.runs` and apply the same company/workspace predicates. Preserve the existing unscoped call used by expiry processing by allowing both filters to be absent only for the internal expiry service.

- [ ] **Step 4: Route every tenant-bound lookup through scoped methods**

Replace `get_conversation(conversation_id)` in the get/update/create-message routes with `get_scoped_conversation(identity.company_id, identity.workspace_id, conversation_id)`. Replace `_get_owned_run_or_404` with a scoped repository lookup. Pass both scopes into approval listing.

The user-visible failure remains a generic HTTP 404; the implementation must not fetch another tenant’s row first.

- [ ] **Step 5: Run tenancy and regression suites**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_tenant_isolation.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_vertical_slice_2_write_approval.py -q
PYTHONPATH=. .venv/bin/pytest tests/agent_core/runs/test_repository.py -q
```

Expected: cross-tenant reads, writes, cancellation, SSE and approval listing all return no other tenant’s data.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/runs/repository.py packages/agent_core/capabilities/approval_service.py apps/cosa/api/routes.py tests/apps/cosa/test_tenant_isolation.py tests/agent_core/runs/test_repository.py
git commit -m "fix: scope tenant-bound run and approval queries"
```

### Task 3: Define one executable development topology and configuration contract

**Files:**

- Create: `scripts/check-dev-preflight.sh`
- Create: `scripts/mint-worker-service-token.mjs`
- Modify: `Makefile:3-49,87-112`
- Modify: `.env.example`
- Modify: `services/.env.example`
- Modify: `docker-compose.yml:7-109,141-205`
- Modify: `services/docker-compose.yml:51-80`
- Modify: `README.md`

**Interfaces:**

- Produces `make dev-infra`, `make dev-migrate`, `make dev-preflight`, `make dev-stack` and `make dev-status`.
- Produces a required host development environment contract: `AGENT_CORE_DATABASE_URL`, `COSA_DATABASE_URL`, `COMPANY_DATABASE_URL`, `COSA_CONTROL_PLANE_URL`, `COMPANY_SERVICE_URL`, `PLATFORM_JWT_SECRET`, `WORKER_SERVICE_JWT_SECRET`, `COSA_WORKER_SERVICE_TOKEN`, and `DEEPSEEK_API_KEY` for real model runs.
- Produces a worker token with `aud="control_plane"`, `role="worker_service"`, issuer `cosa_control_plane`, and a finite expiry.

- [ ] **Step 1: Add a failing preflight shell test matrix**

Create a small shell test under `tests/scripts/test_check_dev_preflight.sh` that invokes the preflight script with each required variable absent and expects non-zero exit. Invoke it with all variables present but a non-listening service URL and expect non-zero exit.

```bash
env -u COSA_WORKER_SERVICE_TOKEN scripts/check-dev-preflight.sh
test "$?" -ne 0
```

- [ ] **Step 2: Create `check-dev-preflight.sh`**

The script must:

1. Require the eight environment variables above, except allow a dedicated deterministic-test mode to omit `DEEPSEEK_API_KEY`.
2. Validate `docker compose config -q` for both Compose files.
3. Verify HTTP readiness of Company and COSA Control Plane using explicit health endpoints, and `/healthz` for FastAPI.
4. Verify `COSA_WORKER_SERVICE_TOKEN` locally by decoding claims only for audience, role and expiry; never print the token.
5. Exit non-zero on the first failed contract and name only the missing variable or unreachable service.

- [ ] **Step 3: Create the short-lived worker-token helper**

Implement `scripts/mint-worker-service-token.mjs` using the `jsonwebtoken` dependency already used by `services/cosa`. Read `WORKER_SERVICE_JWT_SECRET`, reject missing or weak secrets outside development, sign a token for a caller-provided worker ID, and emit only the compact JWT to stdout so it can be assigned by the caller.

- [ ] **Step 4: Make host development the canonical local topology**

Update `Makefile` so:

```make
dev-infra: ## Start only Postgres, MinIO and LiveKit containers
dev-migrate: ## Run Agent Core, COSA and Company migrations in order
dev-preflight: ## Validate config, migrations and dependency health
dev-stack: dev-infra dev-migrate dev-preflight ## Launch Company, COSA, API and worker with a signal-cleanup trap
```

`dev-stack` must wait for actual `/healthz` endpoints and return non-zero on timeout. It must never treat a timeout as successful. Remove the current `curl /` loop because neither Encore application defines that root route.

- [ ] **Step 5: Correct container-to-host assumptions**

Document host URLs separately from container URLs. Do not let a container rely on `localhost:4000` or `127.0.0.1:4001` to reach a host process. For Compose profiles that run `cosa-api` or `cosa-worker`, require explicit endpoint variables and inject all four runtime requirements:

```yaml
DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:?required}
COSA_CONTROL_PLANE_URL: ${COSA_CONTROL_PLANE_URL:?required}
COMPANY_SERVICE_URL: ${COMPANY_SERVICE_URL:?required}
COSA_WORKER_SERVICE_TOKEN: ${COSA_WORKER_SERVICE_TOKEN:?required}
```

Use a named service on a shared Docker network when the dependency is containerized; otherwise use the Docker Desktop host gateway deliberately and document it.

- [ ] **Step 6: Verify preflight behavior**

Run:

```bash
bash tests/scripts/test_check_dev_preflight.sh
make dev-infra
make dev-migrate
make dev-preflight
```

Expected: a missing contract stops immediately; a valid configured stack reports each dependency by name; no success message appears when any endpoint is down.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-dev-preflight.sh scripts/mint-worker-service-token.mjs tests/scripts/test_check_dev_preflight.sh Makefile .env.example services/.env.example docker-compose.yml services/docker-compose.yml README.md
git commit -m "build: make local runtime configuration explicit"
```

### Task 4: Make bootstrap, migrations and deployment ordered and repeatable

**Files:**

- Modify: `docker-compose.yml:7-24`
- Modify: `services/cosa/scripts/migrate.mjs:26-30`
- Modify: `Makefile:51-103`
- Modify: `docs/operations/migrations.md`
- Modify: `docs/operations/rollback_pre_cutover.md`
- Create: `tests/db_baseline_candidate/test_dev_bootstrap_contract.py`

**Interfaces:**

- Produces `make db-bootstrap`, `make migrate-all` and `make deploy-preflight`.
- `migrate-all` executes Agent Core → COSA Control Plane → Company schema migration before dependent processes are started.
- `services/cosa/scripts/migrate.mjs` requires `COSA_DATABASE_URL` or `CONTROL_PLANE_DATABASE_URL` and never selects a committed credential/host fallback.

- [ ] **Step 1: Write the bootstrap/migration contract test**

The test must assert that root Compose mounts `deploy/postgres/init` read-only at `/docker-entrypoint-initdb.d`, the COSA migration script has no database URL literal fallback, and the `deploy` recipe invokes preflight, migrations and application deployment in that exact order.

```python
assert "/docker-entrypoint-initdb.d:ro" in compose_text
assert "SecureCentral" not in migration_text
assert deploy_lines == ["$(MAKE) deploy-preflight", "$(MAKE) migrate-all", "$(MAKE) deploy-app"]
```

- [ ] **Step 2: Make new-database bootstrap explicit and safe**

Mount `deploy/postgres/init` in the root Postgres service. Add `db-bootstrap` that refuses to initialize an existing volume automatically, prints the backup requirement for a non-empty database, and delegates existing-instance role/database setup to a documented idempotent operator command.

- [ ] **Step 3: Remove hidden database fallback and add migration targets**

Replace the fallback in `services/cosa/scripts/migrate.mjs` with a clear error:

```ts
if (!DATABASE_URL) {
  throw new Error("COSA_DATABASE_URL or CONTROL_PLANE_DATABASE_URL is required");
}
```

Add `migrate-all` that runs the three migration commands with explicit DSNs. Do not infer `postgres` as a host when the migration executes on the host; the environment file must provide host-reachable URLs.

- [ ] **Step 4: Reorder deploy and add a deployment preflight**

Make the deploy recipe explicitly sequential, including when a caller passes `-j`:

```make
deploy:
	$(MAKE) deploy-preflight
	$(MAKE) migrate-all
	$(MAKE) deploy-app
```

`deploy-preflight` verifies backup policy, URL reachability, migration checksum state, required secrets and independently deployed Company/Control Plane health. It must stop before restarting any app if a prerequisite fails.

- [ ] **Step 5: Verify against a fresh disposable database**

Run the bootstrap contract test, create an empty disposable Postgres volume, apply `make migrate-all` twice, and confirm the second execution reports no new migration. Then run the Agent Core and control-plane repository integration tests against that database.

Expected: roles/databases exist, schema migrations are idempotent, checksums remain unchanged and no app process starts before schema readiness.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml services/cosa/scripts/migrate.mjs Makefile docs/operations/migrations.md docs/operations/rollback_pre_cutover.md tests/db_baseline_candidate/test_dev_bootstrap_contract.py
git commit -m "build: gate deployment on bootstrap and migrations"
```

### Task 5: Make CI deterministic, comprehensive and representative

**Files:**

- Modify: `.github/workflows/quality.yml`
- Modify: `Makefile:1-49`
- Modify: `pytest.ini`
- Modify: `tests/apps/cosa/worker/test_crash_recovery_subprocess.py`
- Modify: `tests/apps/cosa/test_sse_reconnect_e2e.py`
- Create: `tests/desktop_worker/test_ci_contract.py`

**Interfaces:**

- Produces `make python-test-unit`, `make python-test-integration`, `make desktop-worker-test`, `make realtime-agent-test` and `make verify-local`.
- Produces CI jobs named `quality-unit`, `quality-integration` and `quality-live-provider` with distinct secret and trigger rules.
- Unit and standard integration tests use a deterministic fake model; live-provider conformance is the only job permitted to use `DEEPSEEK_API_KEY`.

- [ ] **Step 1: Add CI contract tests**

Create a test that reads `.github/workflows/quality.yml` and asserts the boundary job contains `actions/setup-python`, installs pytest, and does not call a hard-coded repository `.venv`. Assert the standard PR job invokes `pytest -m "not live_provider"`.

- [ ] **Step 2: Make Make targets portable**

Use configurable variables rather than `.venv/bin/pytest` directly:

```make
PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
```

Retain local override support (`PYTHON=.venv/bin/python`) and make all test targets use `$(PYTEST)`.

- [ ] **Step 3: Separate test categories**

Register `live_provider` in `pytest.ini`. Mark tests requiring outbound model traffic with it. Preserve cross-process crash recovery and SSE restart as integration tests, but make their model execution deterministic through a test-only injected model factory guarded by `APP_ENV=test`; production startup must reject that flag.

- [ ] **Step 4: Update GitHub Actions**

1. Add Python setup and `pip install pytest` to the boundary job.
2. Use `npm ci` where package locks exist.
3. Run `npm run typecheck` for both Encore applications.
4. Add desktop-worker and realtime-agent targets to the standard quality matrix.
5. Run live-provider tests only on protected branches, scheduled execution or manual dispatch with the secret present.
6. Upload JUnit/XML results for every test-bearing job.

- [ ] **Step 5: Verify test selection**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest -m "not live_provider" --collect-only -q
PYTHONPATH=. .venv/bin/pytest -m live_provider --collect-only -q
make boundary-check
make desktop-worker-test
```

Expected: the two collections are disjoint; ordinary test runs make no outbound model request; boundary and desktop-worker gates execute without relying on a checked-in virtual environment.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/quality.yml Makefile pytest.ini tests/apps/cosa/worker/test_crash_recovery_subprocess.py tests/apps/cosa/test_sse_reconnect_e2e.py tests/desktop_worker/test_ci_contract.py
git commit -m "ci: separate deterministic and live-provider quality gates"
```

### Task 6: Run the staged validation gate and document operational handoff

**Files:**

- Modify: `README.md`
- Modify: `docs/COSA_RUNBOOK.md`
- Modify: `docs/operations/migrations.md`
- Modify: `docs/implementation/production-runtime-closure.md`

**Interfaces:**

- Produces one documented go/no-go sequence that is identical for a developer machine and CI, except that live-provider tests are explicit.
- Produces health endpoints for both Encore applications if they do not already exist, each checking database connectivity without returning secrets.

- [ ] **Step 1: Add failing health/readiness tests for both Encore applications**

Create one test per Encore app which calls an unauthenticated `/healthz` endpoint and asserts HTTP 200 plus a body with `status: "ok"` only after a database `SELECT 1` succeeds.

- [ ] **Step 2: Implement minimal health endpoints**

Add a small handler in `services/company` and `services/cosa` that performs a bounded database connectivity check. Keep the response limited to app name, status and version; never return DSNs, configured host names, migrations or secrets.

- [ ] **Step 3: Execute the full deterministic gate**

Run, in this order:

```bash
make dev-infra
make dev-migrate
make dev-preflight
make boundary-check
make python-test-unit
make python-test-integration
make services-test
make desktop-worker-test
make realtime-agent-test
make frontend-test
make frontend-analyze
```

Expected: every command exits `0`; report the command, elapsed time and test count in the implementation-closure document.

- [ ] **Step 4: Execute controlled process-restart tests**

With a disposable Postgres instance and `APP_ENV=test`, run the SSE reconnect and two-process worker crash-recovery tests. Kill the worker/API process as the tests require; do not run this gate against a developer’s shared database.

Expected: scheduler visibility timeout reclaims a task, stale fencing token cannot complete it, and `Last-Event-ID` resumes without duplicates after FastAPI restart.

- [ ] **Step 5: Execute live-provider conformance only with authorized credentials**

Run the `live_provider` marker in the protected environment. Record model/provider name, test count, failures and sanitized correlation IDs. Do not store API keys, bearer tokens or model prompts containing customer data.

- [ ] **Step 6: Update the runbook and commit**

Document prerequisites, explicit topology, migration order, rollback point, test tiers, health endpoints and the condition that blocks deploy. Commit:

```bash
git add README.md docs/COSA_RUNBOOK.md docs/operations/migrations.md docs/implementation/production-runtime-closure.md services/company services/cosa
git commit -m "docs: document deterministic development and test gates"
```

## Plan self-review

- **Coverage:** static compilation, Flutter lint, tenant isolation, environment contract, networking topology, bootstrap, migration ordering, deployment gate, deterministic CI, process-restart verification and live-provider separation each map to a task.
- **Consistency:** all local runtime URLs are host-reachable and all container runtime URLs are explicit; no task relies on a hidden localhost fallback or a default production credential.
- **Scope:** the plan changes only paths that control test/dev readiness and its direct security prerequisites; it does not redesign the agent architecture, database baseline or runtime choice.
- **Ambiguity resolved:** development uses host processes plus Docker infrastructure; Compose application profiles remain available only with all required external URLs and tokens supplied explicitly.

## Execution order and acceptance criteria

Execute Tasks 1 → 2 → 3 → 4 → 5 → 6. Do not start the full development test gate before Tasks 1–4 pass. The repository is ready for developer testing only when all of the following are true:

1. `services/company` and `services/cosa` type checks pass; Flutter analyzer has zero diagnostics.
2. `make dev-preflight` fails closed for invalid configuration and passes against the configured stack.
3. Fresh schema bootstrap and a second migration execution are both successful.
4. Tenant-collision tests prove that no conversation, run, approval or event can cross a company/workspace scope.
5. CI standard jobs run deterministically without model-provider secrets, and live-provider tests are isolated.
6. Cross-process recovery tests pass against disposable PostgreSQL and the runbook contains the verified commands and rollback path.
