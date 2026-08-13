# Tenant Isolation Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add database-backed, cross-tenant regression tests for the highest-risk COSA OS resources.

**Architecture:** One integration fixture persists two separate workspace/user/brain graphs using `SessionLocal`; each case calls the existing domain handler/guard with workspace-B membership and workspace-A identifiers. The fixture always rolls back, so the CI test database stays clean.

**Tech Stack:** pytest, SQLAlchemy, FastAPI HTTPException, PostgreSQL, Alembic.

**Spec:** `docs/superpowers/specs/2026-08-13-tenant-isolation-matrix-design.md`

## Global Constraints

- Run only when `RUN_DB_INTEGRATION=1`.
- Use Snowflake IDs and never add SQLite state.
- Foreign resources must remain indistinguishable from non-existent resources.

---

### Task 1: Build integration fixture and failing matrix tests

**Files:**
- Create: `backend/app/tests/test_tenant_isolation_matrix.py`

- [ ] Seed workspace A and B, one active user/member each, brains, a task, a project, a chat session, and a realtime session; use a rollback-only fixture.
- [ ] Add one failing test per matrix row asserting `HTTPException.status_code == 404` and no persisted mutation.
- [ ] Run: `RUN_DB_INTEGRATION=1 DATABASE_URL=$TEST_DATABASE_URL PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_tenant_isolation_matrix.py -q`

### Task 2: Repair only guards proven unsafe

**Files:**
- Modify only router/service files implicated by a failing matrix test.

- [ ] Make the smallest workspace-and-brain-scoped query change.
- [ ] Re-run the individual matrix case, then the full matrix.

### Task 3: Integrate and verify

**Files:**
- Modify: `docs/superpowers/specs/2026-08-13-tenant-isolation-matrix-design.md`
- Modify: `docs/superpowers/plans/2026-08-13-tenant-isolation-matrix.md`

- [ ] Run `make backend-integration-test TEST_DATABASE_URL=$TEST_DATABASE_URL`.
- [ ] Run `make boundary-check` and the full local backend unit suite.
