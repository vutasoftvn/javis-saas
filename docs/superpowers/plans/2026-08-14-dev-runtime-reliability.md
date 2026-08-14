# Dev Runtime Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a fresh Docker Compose development runtime migrate before serving, work from Flutter Web, and accurately report schema readiness.

**Architecture:** Compose supplies a one-shot migration gate. FastAPI owns CORS and migration readiness; Compose retains provider secrets in the worker and sends only configured flags to the API.

**Tech Stack:** Docker Compose, FastAPI/Starlette, Alembic, pytest, Flutter/Dart.

**Spec:** `docs/superpowers/specs/2026-08-14-dev-runtime-reliability-design.md`

## Global Constraints

- No `javis/` or `backend/server/` runtime dependency.
- Flutter communicates only through `/api/v1`.
- Provider secrets never reach `brain-api` or Flutter.
- Preserve unrelated user changes.

---

### Task 1: Add CORS contract

**Files:**

- Create: `backend/app/core/cors.py`
- Modify: `backend/app/main.py`, `backend/app/tests/test_health.py`, `.env.example`

**Interfaces:** `parse_allowed_origins(raw: str | None) -> list[str]` reads comma-separated `CORS_ALLOWED_ORIGINS`.

- [ ] Write a failing `TestClient(app).options()` test that asserts an origin in `CORS_ALLOWED_ORIGINS` gets HTTP 200 and `access-control-allow-origin`, then a test that an unconfigured origin does not get that header.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_health.py -q`; observe the current 405 preflight failure.
- [ ] Implement the parser and install Starlette `CORSMiddleware` in `app.main`, using local origins by default only in development; list the variable in `.env.example`.
- [ ] Re-run the focused test until green.
- [ ] Commit only Task 1 files as `feat: configure development CORS`.

### Task 2: Gate runtime boot on migrations and correct OpenRouter wiring

**Files:**

- Create: `backend/app/tests/test_compose_contract.py`
- Modify: `docker-compose.yml`, `backend/app/tests/test_model_registry.py`

**Interfaces:** service `migrate` runs `alembic upgrade head`; API and worker depend on `migrate: service_completed_successfully`.

- [ ] Write a failing YAML-based test that asserts the `migrate` service and both dependencies exist; assert API has `PROVIDER_CONFIGURED_OPENROUTER=${OPENROUTER_API_KEY:+1}`, worker has `OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}`, and API has no direct key.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_compose_contract.py -q`; observe failure against current Compose source.
- [ ] Add `migrate`, based on the API image and Postgres health, then add successful-completion dependencies. Remove the literal API configured flag and pass the key only to the worker.
- [ ] Re-run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_compose_contract.py backend/app/tests/test_model_registry.py -q` until green.
- [ ] Commit only Task 2 files as `fix: migrate schema before runtime startup`.

### Task 3: Add Alembic-aware readiness

**Files:**

- Create: `backend/app/core/migration_health.py`
- Modify: `backend/app/main.py`, `backend/app/tests/test_health.py`

**Interfaces:** `get_migration_health(engine) -> tuple[bool, str]`; `/ready.checks.migrations` is `ok` or stable error code.

- [ ] Write a failing test that stubs `get_migration_health` to `(False, "behind")` and expects `/ready` to return HTTP 503 plus `checks.migrations == "behind"`; add the healthy case expecting `ok`.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_health.py -q`; observe the absent migration check.
- [ ] Compare `alembic_version` through the existing engine to Alembic `ScriptDirectory` head. Do not invoke Alembic migrations in the API process.
- [ ] Re-run the focused health test until green.
- [ ] Commit only Task 3 files as `feat: report schema migration readiness`.

### Task 4: Update runbook and remove analyzer diagnostics

**Files:**

- Modify: `DEPLOYMENT.md`, `Makefile`, `frontend/lib/modules/mission_control/controllers/mission_control_controller.dart`, `frontend/lib/modules/mission_control/views/mission_control_view.dart`, `backend/app/tests/test_compose_contract.py`

**Interfaces:** `make dev` starts Compose and polls `/ready` with bounded retries.

- [ ] Write a failing text-level test that requires `DEPLOYMENT.md` to document `docker compose up --build -d migrate`, `CORS_ALLOWED_ORIGINS`, and no longer claim `Base.metadata.create_all(bind=engine)` executes at startup.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_compose_contract.py -q`; observe failure.
- [ ] Replace stale runbook text; implement a bounded, non-destructive `make dev`; replace every analyzer-reported `withOpacity(x)` with `withValues(alpha: x)` and remove only the reported unnecessary `toList()`.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_compose_contract.py -q && cd frontend && flutter analyze`; expect zero analyzer diagnostics.
- [ ] Commit only Task 4 files as `docs: document reliable development startup`.

### Task 5: Verify the completed runtime

**Files:** none unless verification reveals a defect.

- [ ] Run `make backend-test frontend-test frontend-analyze boundary-check`; all commands must return 0.
- [ ] Run `docker compose up --build -d --force-recreate && docker compose ps`; expect successful `migrate` and running API/worker/dependencies.
- [ ] Run a `/ready` curl and an OPTIONS preflight from `http://localhost:3000`; expect migration `ok` and allowed-origin response.
- [ ] Run `git status --short`; stage and commit only files belonging to this plan, retaining all pre-existing user changes.
