# COSA OS Development Master Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current COSA OS development stack into a coherent, repeatable and tenant-safe platform before expanding product capability or preparing a staging release.

**Architecture:** The work is ordered by dependency: first establish a reproducible runtime and one background-worker owner; then replace UUID runtime storage with Snowflake and secure the retained Zalo QR connector; then harden test/quality gates; finally complete the core Strategy → Tasks → Chat product loop. This plan is a development remediation plan; production secrets, managed infrastructure, and production data migration are deliberately deferred.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL/pgvector, MinIO, Docker Compose, Flutter/GetX, pytest, Flutter test.

## Global Constraints

- `backend/app` is the only backend runtime for Flutter, through `/api/v1`.
- `javis/` and `backend/server/` are behavior references only; no production dependency, import, proxy, or client call.
- Every workspace/brain resource is server-side tenant-scoped; client IDs are never trusted by themselves.
- New and migrated runtime IDs use 64-bit Snowflake `BIGINT`; all API IDs are serialized as decimal strings.
- Zalo personal QR remains a development connector and is scoped to workspace/user ownership.
- Postgres is schema-managed only through Alembic after the Snowflake dev cutover.
- Background work runs only in `agent-worker`.

---

## Phase 0: Confirm the development baseline

**Purpose:** Establish one authoritative description of what is currently supported before changing runtime behavior.

### Task 1: Create a current-state and ADR index

**Files:**
- Create: `docs/architecture/CURRENT_STATE.md`
- Modify: `docs/architecture/IMPLEMENTATION_ROADMAP.md`
- Modify: `docs/architecture/JAVIS_MIGRATION_PLAN.md`

- [ ] Write `CURRENT_STATE.md` with these fixed sections: runtime diagram, active Compose services, source-of-truth API boundary, supported dev capabilities, experimental capabilities, current test commands, and superseded documents/decisions.
- [ ] Record that Zalo personal QR is supported for development, but only through `backend/app` and only as a tenant-scoped connector.
- [ ] Mark contradictory historical statements in the two existing roadmaps as historical context, not current implementation instructions.
- [ ] Add the command below to `CURRENT_STATE.md` and verify it has no runtime legacy references:

```bash
rg -n --glob '!build/**' '(:8888|backend/server|javis/)' frontend/lib
```

- [ ] Commit:

```bash
git add docs/architecture
git commit -m "docs: establish current COSA OS development state"
```

### Task 2: Make runtime ownership explicit

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/worker_main.py`
- Modify: `docker-compose.yml`
- Test: `backend/app/tests/test_health.py`

- [ ] Write a failing test asserting the FastAPI startup path does not call `channel_worker_loop`.
- [ ] Remove `asyncio.create_task(channel_worker_loop())` from `backend/app/main.py`.
- [ ] Keep chat, channel, scheduler, dispatcher, chunking, and Zalo QR loops owned by `agent-worker` only.
- [ ] Run:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_health.py -q
docker compose config
```

- [ ] Commit:

```bash
git add backend/app/main.py backend/app/worker_main.py docker-compose.yml backend/app/tests/test_health.py
git commit -m "fix: centralize background work in agent worker"
```

## Phase 1: Snowflake and Zalo QR tenancy cutover

**Purpose:** Replace UUID storage and make retained Zalo QR functionality durable and workspace-safe.

### Task 3: Execute the dedicated Snowflake/Zalo plan

**Plan:** [2026-08-11-zalo-workspace-tenancy-and-snowflake-cutover.md](2026-08-11-zalo-workspace-tenancy-and-snowflake-cutover.md)

- [ ] Confirm the local Postgres volume contains no data that must be retained.
- [ ] Execute Tasks 1–7 of the dedicated plan in order.
- [ ] Do not begin any feature work that creates a new model until the static scan is clean:

```bash
rg -n 'uuid\.UUID|PG_UUID|postgresql\.UUID|sa\.UUID|uuid\.uuid4' backend/app backend/alembic/versions
```

- [ ] Verify the completed QR contract with two users in different workspaces: owner can read/cancel; non-member receives 404 for both operations.

## Phase 2: Make schema migrations repeatable

**Purpose:** Remove development schema drift so a fresh database produces exactly the schema represented by Alembic.

### Task 4: Retire runtime DDL after baseline migration

**Files:**
- Modify: `backend/app/main.py`
- Modify: `DEPLOYMENT.md`
- Test: `backend/app/tests/test_health.py`

- [ ] Write a failing startup test that imports the app and asserts no `Base.metadata.create_all` call occurs.
- [ ] Remove `Base.metadata.create_all(bind=engine)` and all literal `ALTER TABLE` statements from `on_startup`.
- [ ] Preserve only dependency readiness behavior: MinIO bucket readiness and health checks.
- [ ] Update deployment instructions so the only schema command is:

```bash
docker compose exec brain-api alembic upgrade head
```

- [ ] Verify a new dev volume works:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec brain-api alembic upgrade head
curl --fail http://127.0.0.1:8000/ready
```

- [ ] Commit:

```bash
git add backend/app/main.py backend/app/tests/test_health.py DEPLOYMENT.md
git commit -m "fix: make alembic the schema authority"
```

### Task 5: Add a migration smoke test

**Files:**
- Create: `backend/app/tests/test_migration_smoke.py`
- Modify: `DEPLOYMENT.md`

- [ ] Add a test or CI script that creates a clean test database, runs `alembic upgrade head`, and confirms key tables `users`, `workspaces`, `brains`, `chat_sessions`, `tasks`, `mcp_connections`, and `zalo_qr_sessions` exist with `BIGINT` primary keys.
- [ ] Add the documented test command:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_migration_smoke.py -q
```

- [ ] Commit:

```bash
git add backend/app/tests/test_migration_smoke.py DEPLOYMENT.md
git commit -m "test: verify clean database migrations"
```

## Phase 3: Tenant contract and test reliability

**Purpose:** Turn the repeated cross-tenant bug class into a reusable test gate and eliminate test dependence on a developer's host database or platform hardware.

### Task 6: Build tenant-scoped integration fixtures

**Files:**
- Replace: `backend/app/tests/conftest.py`
- Create: `backend/app/tests/fixtures/tenancy.py`
- Modify: resource-specific tests under `backend/app/tests/`

- [ ] Create fixtures for an isolated Postgres test database, workspace A/B, member A/B, brain A/B, authenticated headers, and a factory that returns Snowflake-backed entities.
- [ ] Make every database-using test accept the database fixture rather than reading the developer `DATABASE_URL` implicitly.
- [ ] Convert `test_zalo_mcp.py` into a fully isolated API test with an overridden `get_db`; it must never open a TCP connection to `localhost:5432`.
- [ ] Add this representative contract test to each resource family: vault, chat, tasks, workflows, strategy, marketing, integrations, outcomes, devices, organization:

```python
def test_resource_from_other_workspace_returns_not_found(client, member_b_headers, resource_a, workspace_b):
    response = client.get(resource_a.url(workspace_id=workspace_b.id), headers=member_b_headers)
    assert response.status_code == 404
```

- [ ] Run:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/app/tests -q
```

- [ ] Commit:

```bash
git add backend/app/tests
git commit -m "test: isolate tenant integration contracts"
```

### Task 7: Decouple frontend controllers from platform services

**Files:**
- Modify: `frontend/lib/core/services/voice_service.dart`
- Modify: `frontend/lib/modules/chat/controllers/chat_controller.dart`
- Modify: `frontend/test/chat_service_test.dart`

- [ ] Add `IVoiceService` constructor injection to `ChatController`; do not instantiate `AudioRecorder` during controller construction.
- [ ] In production binding, pass `VoiceService()` from the chat binding; in tests, pass a fake that returns fixed values and never touches method channels.
- [ ] Add the regression test:

```dart
test('sending first chat message does not initialize the platform recorder', () async {
  final controller = ChatController(chatService: _FakeChatGateway(), voiceService: _FakeVoiceService());
  await controller.sendMessage('Tin nhắn đầu tiên');
  expect(controller.currentSessionId.value, 'session-1');
});
```

- [ ] Run:

```bash
cd frontend && flutter test && flutter analyze
```

- [ ] Commit:

```bash
git add frontend/lib/core/services/voice_service.dart frontend/lib/modules/chat frontend/test/chat_service_test.dart
git commit -m "test: inject voice service into chat controller"
```

## Phase 4: Development delivery gates

**Purpose:** Make a regression visible before it reaches a shared development environment.

### Task 8: Add local quality commands

**Files:**
- Create: `Makefile`
- Modify: `DEPLOYMENT.md`

- [ ] Add these targets:

```make
backend-test:
	PYTHONPATH=backend .venv/bin/pytest backend/app/tests -q

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib
	rg -n 'uuid\.UUID|PG_UUID|postgresql\.UUID|sa\.UUID|uuid\.uuid4' backend/app backend/alembic/versions
```

- [ ] Run each target and correct every non-zero result before committing.
- [ ] Commit:

```bash
git add Makefile DEPLOYMENT.md
git commit -m "build: add local quality gates"
```

### Task 9: Add CI after local gates pass

**Files:**
- Create: `.github/workflows/quality.yml`

- [ ] Configure jobs for backend tests, Flutter tests/analyze, and `make boundary-check`.
- [ ] Cache Python and Flutter dependencies; do not inject provider keys into CI.
- [ ] Publish test output as CI annotations/artifacts, not secrets or runtime DB files.
- [ ] Commit:

```bash
git add .github/workflows/quality.yml
git commit -m "ci: enforce backend frontend and boundary checks"
```

## Phase 5: Product vertical slice

**Purpose:** Make the product's value obvious through one complete user path instead of expanding disconnected modules.

### Task 10: Define the supported core flow contract

**Files:**
- Create: `docs/architecture/CORE_PRODUCT_FLOW.md`
- Modify: `frontend/lib/modules/dashboard/views/dashboard_view.dart`
- Test: backend and Flutter flow tests

- [ ] Define the exact user path: create workspace/brain → enter company context → create or update strategy canvas → compile a twelve-week plan → create/assign a task → ask Chat for context-aware support.
- [ ] For every step, list endpoint, required tenant IDs, success response, user-visible error, and navigation destination.
- [ ] Mark modules outside this path as `experimental` in navigation/UI until they have a complete API, tenancy tests, and useful empty states.
- [ ] Commit:

```bash
git add docs/architecture/CORE_PRODUCT_FLOW.md frontend/lib/modules/dashboard/views/dashboard_view.dart
git commit -m "docs: define COSA OS core product flow"
```

### Task 11: Add end-to-end regression coverage for the core flow

**Files:**
- Create: `backend/app/tests/test_core_product_flow.py`
- Create: `frontend/integration_test/core_product_flow_test.dart`

- [ ] Backend test seeds a Snowflake workspace/brain/user, executes the core APIs in order, and verifies all created rows remain scoped to the same workspace/brain.
- [ ] Flutter integration test uses a fake API service to verify screen transitions and error presentation without calling external AI providers.
- [ ] Run:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_core_product_flow.py -q
cd frontend && flutter test integration_test/core_product_flow_test.dart
```

- [ ] Commit:

```bash
git add backend/app/tests/test_core_product_flow.py frontend/integration_test/core_product_flow_test.dart
git commit -m "test: cover strategy to chat product flow"
```

## Phase 6: Staging-readiness backlog

**Purpose:** Keep production work visible without blocking current development.

### Task 12: Create the release checklist, do not implement it yet

**Files:**
- Create: `docs/architecture/STAGING_READINESS.md`

- [ ] Include required items: production-only secret validation, secret manager, database backup/restore drill, MinIO/S3 recovery test, structured logs with request IDs, error tracking, rate limits, CORS policy for web deployment, worker concurrency/load test, provider budget controls, and dependency vulnerability review.
- [ ] State that personal Zalo connector requires a separate risk decision before exposure outside controlled development.
- [ ] Commit:

```bash
git add docs/architecture/STAGING_READINESS.md
git commit -m "docs: define staging readiness checklist"
```

## Completion criteria

- A clean local Docker volume starts with an Alembic-built Snowflake schema.
- All runtime IDs are Snowflake `BIGINT`; every client-visible ID is a string.
- Zalo QR works from the worker image, is persisted, and cannot be viewed or cancelled cross-workspace.
- `brain-api` owns no background loop or connector process.
- Backend and Flutter tests are isolated and green; static boundary checks are clean.
- The Strategy → Tasks → Chat flow has documented API/UI behavior and regression coverage.
