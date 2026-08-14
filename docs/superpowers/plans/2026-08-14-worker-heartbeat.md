# Worker Heartbeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/ready` and admin diagnostics detect a stale or missing agent worker.

**Architecture:** A Snowflake-backed global heartbeat row is written by `worker_main` every five seconds. A read-only health service evaluates its age for both FastAPI readiness and tenant-authorized diagnostics.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, asyncio, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-14-worker-heartbeat-design.md`

## Global Constraints

- Migration `v13_030_worker_heartbeat` must have `down_revision = v13_029_chat_session_purpose`.
- Runtime-global heartbeat records contain no workspace, brain, provider secret, or user data.
- Use Snowflake IDs and serialize identifiers as strings in any JSON response.
- Do not change legacy runtime boundaries or add client-side persistent state.

---

### Task 1: Persist and evaluate runtime heartbeat freshness

**Files:**

- Modify: `backend/app/modules/platform/models.py`, `backend/app/db/base.py`
- Create: `backend/app/core/worker_health.py`
- Create: `backend/alembic/versions/v13_030_worker_heartbeat.py`
- Create: `backend/app/tests/test_worker_health.py`

**Interfaces:** `record_worker_heartbeat(db, component: str) -> None`; `get_worker_health(engine, max_age_seconds: int = 15) -> tuple[bool, str]`.

- [ ] Write failing tests for missing, fresh, stale, and database-error health outcomes, asserting stable statuses `missing`, `ok`, `stale`, and `error`.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_worker_health.py -q`; observe failure because the module does not exist.
- [ ] Add `RuntimeHeartbeat` with Snowflake ID, unique `component`, `last_seen_at`, and updated timestamp; import it in `app.db.base`. Implement upsert and age comparison without migrations or writes in the health function.
- [ ] Add migration `v13_030_worker_heartbeat.py` creating the model's table and unique component constraint.
- [ ] Re-run the focused test until green, then run `alembic -c backend/alembic.ini check` against a dedicated migrated integration database.
- [ ] Commit Task 1 files as `feat: persist agent worker heartbeat`.

### Task 2: Write heartbeat from worker and consume it from readiness

**Files:**

- Modify: `backend/app/worker_main.py`, `backend/app/main.py`, `backend/app/tests/test_health.py`

**Interfaces:** worker emits component `agent-worker` immediately and every five seconds; `/ready.checks.worker` is `ok`, `missing`, `stale`, or `error`.

- [ ] Write failing `/ready` tests for fresh `(True, "ok")` and stale `(False, "stale")` worker health; assert stale makes response HTTP 503.
- [ ] Run `PYTHONPATH=$PWD/backend $PWD/.venv/bin/pytest backend/app/tests/test_health.py -q`; observe the missing worker check.
- [ ] Add an async worker heartbeat loop that calls `record_worker_heartbeat`, commits its own short-lived session, logs exceptions, and continues after failures. Start it alongside existing worker loops. Add worker health to readiness without changing `/live`.
- [ ] Re-run health tests and a source-level worker startup test until green.
- [ ] Commit Task 2 files as `feat: require fresh worker heartbeat for readiness`.

### Task 3: Surface the same state in authorized diagnostics and verify runtime

**Files:**

- Modify: `backend/app/modules/platform/router.py`, `backend/app/tests/test_platform_audit_events.py` or a focused diagnostics test, `DEPLOYMENT.md`

- [ ] Write a failing diagnostics test that stubs worker health stale and expects `workers: degraded` while preserving workspace authorization and existing response fields.
- [ ] Run its focused pytest command; observe diagnostics still derives worker health only from chunking failures.
- [ ] Replace that derived worker signal with `get_worker_health`; document the 15-second readiness window and troubleshooting command in `DEPLOYMENT.md`.
- [ ] Run `make backend-test frontend-analyze boundary-check`.
- [ ] Recreate Compose, wait for migrate exit code 0, verify `/ready` includes `worker: ok`, then stop `agent-worker` and verify `/ready` eventually returns HTTP 503 with `worker: stale`.
- [ ] Commit Task 3 files as `feat: expose worker liveness in diagnostics`.
