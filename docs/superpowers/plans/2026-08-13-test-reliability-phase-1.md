# Test Reliability Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make backend and realtime test execution deterministic and visible in CI without changing COSA OS runtime behaviour.

**Architecture:** CI uses a dedicated `javis_test` Postgres service and validates Alembic metadata before backend integration tests. Unit tests explicitly bypass persisted workspace-secret discovery when exercising environment fallback. The realtime sidecar is tested in an independent Python environment.

**Tech Stack:** GitHub Actions, pytest, pytest-asyncio, Alembic, PostgreSQL 16, Flutter.

**Spec:** `docs/superpowers/specs/2026-08-13-test-reliability-phase-1-design.md`

## Global Constraints

- Keep `frontend/` communicating only with versioned `/api/v1` endpoints.
- Do not add a legacy runtime dependency.
- Do not modify or reset the developer database automatically.
- Keep the realtime sidecar dependency environment separate from `backend/requirements.txt`.
- Do not add SQLite state.

---

### Task 1: Make model-registry fallback deterministic

**Files:**
- Modify: `backend/app/tests/test_model_registry.py`

**Interfaces:**
- Consumes: `app.modules.chat.model_registry._resolve_defaults() -> tuple[str, str]`.
- Produces: a regression test that cannot read local `WorkspaceSecret` data.

- [ ] **Step 1: Write the failing regression test**

```python
def test_unknown_env_defaults_ignore_workspace_secrets(monkeypatch):
    _forget_every_provider_key(monkeypatch)
    monkeypatch.setattr("app.db.session.SessionLocal", _unexpected_database_access)
    monkeypatch.setenv("CHAT_DEFAULT_PROVIDER", "openrouter")
    monkeypatch.setenv("CHAT_DEFAULT_MODEL", "unknown")
    assert _resolve_defaults() == ("deepseek", "deepseek-chat")
```

- [ ] **Step 2: Run the regression test and verify it fails against the current test helper**

Run: `PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_model_registry.py::test_unknown_env_defaults_ignore_workspace_secrets -q`

Expected: FAIL because the test/helper does not yet prevent dynamic secret lookup.

- [ ] **Step 3: Add the smallest test-only isolation helper**

```python
def _disable_workspace_secret_lookup(monkeypatch):
    monkeypatch.setattr("app.modules.chat.model_registry._workspace_secret_configured", lambda *_: False)
```

Use this helper from tests asserting fallback behaviour and preserve production provider lookup.

- [ ] **Step 4: Run model registry tests**

Run: `PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_model_registry.py -q`

Expected: PASS.

### Task 2: Isolate database integration in CI and validate migrations

**Files:**
- Modify: `.github/workflows/quality.yml`
- Modify: `services/realtime_agent/requirements.txt`
- Modify: `Makefile`

**Interfaces:**
- Consumes: `DATABASE_URL` understood by Alembic and `RUN_DB_INTEGRATION=1` understood by integration tests.
- Produces: CI database URL `postgresql://javis:javis@127.0.0.1:5432/javis_test` and JUnit report files under `test-results/`.

- [ ] **Step 1: Write the CI assertions as workflow commands**

```yaml
- run: PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
- run: PYTHONPATH=backend alembic -c backend/alembic.ini check
- run: PYTHONPATH=backend RUN_DB_INTEGRATION=1 pytest backend/app/tests -q --junitxml=test-results/backend.xml
```

- [ ] **Step 2: Verify the local database is intentionally not used by the new Make target**

Run: `TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_test make migration-check`

Expected: the target reads `TEST_DATABASE_URL`, not an implicit development URL.

- [ ] **Step 3: Implement workflow and Makefile changes**

Set the CI service database to `javis_test`, route every migration/test command through the explicit URL, add `alembic check`, and upload the backend JUnit file with `if: always()`.

- [ ] **Step 4: Verify syntax and migration command**

Run: `TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_test make migration-check`

Expected: Alembic reports no new operations when the test database has been migrated.

### Task 3: Add realtime CI and test reports

**Files:**
- Modify: `.github/workflows/quality.yml`

**Interfaces:**
- Consumes: `services/realtime_agent/requirements.txt`.
- Produces: standalone `realtime-agent` CI job and JUnit reports for all test jobs.

- [ ] **Step 1: Add a failing workflow-level expectation**

```yaml
realtime-agent:
  steps:
    - run: pip install -r services/realtime_agent/requirements.txt 'pytest>=8.0.0'
    - run: pytest tests -q --junitxml=../test-results/realtime-agent.xml
      working-directory: services/realtime_agent
```

- [ ] **Step 2: Implement report uploads**

Upload `test-results/` from backend, frontend, and realtime jobs with `actions/upload-artifact@v4` and `if: always()`.

- [ ] **Step 3: Declare direct backend import dependencies**

Add `pgvector`, `asyncpg`, `passlib[bcrypt]`, and the backend-compatible `bcrypt` pin to the realtime runtime requirements. These modules are imported by the backend tool bridge and must exist in a clean realtime environment.

- [ ] **Step 4: Run realtime tests with its own environment**

Run: `services/realtime_agent/.venv/bin/python -m pytest services/realtime_agent/tests -q`

Expected: PASS.

### Task 4: Verify the complete phase

**Files:**
- Modify: `docs/superpowers/specs/2026-08-13-test-reliability-phase-1-design.md`
- Modify: `docs/superpowers/plans/2026-08-13-test-reliability-phase-1.md`

- [ ] **Step 1: Run all affected tests and checks**

Run: `make boundary-check`

Run: `PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_model_registry.py -q`

Run: `services/realtime_agent/.venv/bin/python -m pytest services/realtime_agent/tests -q`

Run: `cd frontend && flutter test && flutter analyze`

- [ ] **Step 2: Record actual outcomes in the handoff**

State test counts, any environment-only blockers, and the fact that no developer database was reset.
