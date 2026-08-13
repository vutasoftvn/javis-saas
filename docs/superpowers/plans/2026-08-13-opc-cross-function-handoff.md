# OPC Cross-Function Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable, tenant-scoped Sales-to-Finance handoffs and create Learning lessons from a resolved handoff.

**Architecture:** A dedicated Handoffs module owns persistence and lifecycle validation. Sales calls it when an opportunity is won; Finance resolves the record; Learning creates a lesson from its audited payload. The table is the source of truth and the existing event broker is notification-only.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, Flutter service layer.

**Spec:** `docs/superpowers/specs/2026-08-13-opc-cross-function-handoff-design.md`

## Global Constraints

- Every resource lookup filters by authenticated `workspace_id`.
- Primary keys use Snowflake IDs and REST JSON serializes IDs as strings.
- Finance remains the only owner of accounting records and transactions.
- New behavior uses tests written before production code.

---

### Task 1: Durable handoff model and migration

**Files:**
- Create: `backend/app/modules/handoffs/models.py`
- Create: `backend/alembic/versions/v13_017_cross_function_handoffs.py`
- Modify: `backend/app/db/base.py`
- Test: `backend/app/tests/test_handoff_service.py`

**Interfaces:**
- Produces: `CrossFunctionHandoff` with `create_sales_finance_handoff(db, opportunity)`.

- [ ] **Step 1: Write failing tests** for idempotent `(workspace_id, idempotency_key)` handoff creation and state transitions.
- [ ] **Step 2: Run** `PYTHONPATH=backend backend/.venv/bin/pytest -q backend/app/tests/test_handoff_service.py` and confirm the missing module failure.
- [ ] **Step 3: Add model, migration and service** with only `pending → accepted → resolved|rejected` transitions.
- [ ] **Step 4: Re-run the focused test** and confirm it passes.
- [ ] **Step 5: Commit** the durable model and service.

### Task 2: Sales and Finance API integration

**Files:**
- Create: `backend/app/modules/handoffs/router.py`
- Modify: `backend/app/modules/sales/domain/opportunities.py`
- Modify: `backend/app/modules/finance/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_handoff_router.py`

**Interfaces:**
- Consumes: `create_sales_finance_handoff(db, opportunity)`.
- Produces: tenant-scoped list/accept/resolve endpoints.

- [ ] **Step 1: Write failing router tests** for workspace rejection, Finance role enforcement and resolution lifecycle.
- [ ] **Step 2: Run** `PYTHONPATH=backend backend/.venv/bin/pytest -q backend/app/tests/test_handoff_router.py` and confirm failure.
- [ ] **Step 3: Add routers and call the service after an opportunity is won** in the same transaction.
- [ ] **Step 4: Re-run focused tests** and confirm pass.
- [ ] **Step 5: Commit** the API integration.

### Task 3: Learning conversion and Week 13 data read

**Files:**
- Modify: `backend/app/modules/learning/router.py`
- Modify: `backend/app/modules/learning/service.py`
- Test: `backend/app/tests/test_learning_handoff.py`

**Interfaces:**
- Consumes: resolved `CrossFunctionHandoff`.
- Produces: `POST /api/v1/learning/from-handoff/{handoff_id}`.

- [ ] **Step 1: Write failing tests** that reject unresolved/cross-tenant handoffs and create one lesson from a resolved handoff.
- [ ] **Step 2: Run** `PYTHONPATH=backend backend/.venv/bin/pytest -q backend/app/tests/test_learning_handoff.py` and confirm failure.
- [ ] **Step 3: Implement minimal scoped lookup and lesson creation** with source handoff metadata.
- [ ] **Step 4: Re-run focused tests** and confirm pass.
- [ ] **Step 5: Commit** the Learning integration.

### Task 4: Regression and operational documentation

**Files:**
- Modify: `DEPLOYMENT.md`
- Test: `backend/app/tests/test_handoff_service.py`, `backend/app/tests/test_handoff_router.py`, `backend/app/tests/test_learning_handoff.py`

- [ ] **Step 1: Add deployment notes** for migration `v13_017_cross_function_handoffs`.
- [ ] **Step 2: Run** the full backend suite and Flutter test/analyze suite.
- [ ] **Step 3: Inspect** `git diff --check` and migration chain.
- [ ] **Step 4: Commit** documentation and any final test-only adjustments.
