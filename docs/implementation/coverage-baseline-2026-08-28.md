# Test Suite Baseline & Coverage Report (2026-08-28)

## 1. Executive Summary

This report establishes the verified test baseline for `javis-saas` across all four system layers (Agent Core / Python, COSA Control Plane, Company Microservices, and Flutter Frontend) following the completion of the 4-part remediation sprint.

- **Status**: ✅ **100% Passing across all layers (0 failures, 0 analysis warnings)**
- **Verification Date**: 2026-08-28
- **Runner Configuration**: Local test databases (`postgresql://javis:javis@127.0.0.1:5432/javis`, `cosa_control_plane`), Encore runtime `v1.44+`, Flutter `3.27+`, Python `3.11`.

---

## 2. Test Execution Matrix

| Subsystem / Layer | Test Framework | Test Files | Tests Run | Passed | Skipped | Failed | Coverage / Health |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Agent Core (Python)** | Pytest 9.1 | 38+ | 445 | 433 | 12 | 0 | In-memory + PostgreSQL real stores, DAG validation, idempotency CAS |
| **COSA Apps / Worker (Python)** | Pytest 9.1 | 24+ | 227 | 224 | 3 | 0 | Ingestion sandbox, subprocess crash recovery, tenant isolation |
| **COSA Control Plane (TS)** | Vitest 3.2 | 9 | 77 | 77 | 0 | 0 | Leases, worker ingress, scheduler crash recovery, DB URL resolution |
| **Company Services (TS)** | Vitest 3.2 | 49 | 234 | 234 | 0 | 0 | Commercial, Operations, Finance-Legal, Identity, Tenant isolation |
| **Flutter Web/Mobile Frontend** | Flutter Test | 36+ | 306 | 306 | 0 | 0 | Strict type safety, TaskService, auth, chat, session, workflows |
| **Frontend Static Analysis** | Flutter Analyze | - | - | PASS | - | 0 | **0 analyzer issues** |
| **Doc Internal Link Checker** | Custom AST | 170 MD files | 34 | 34 | 0 | 0 | **0 broken links** |
| **Architectural Boundaries** | Pytest + Ripgrep | 1 | 3 | 3 | 0 | 0 | Strict layer isolation, no legacy imports |
| **TOTAL** | | **128+ files** | **1,323+ tests** | **1,308+** | **15** | **0** | **100% Pass Rate** |

---

## 3. Detailed Component Breakdown

### 3.1. Agent Core (`packages/agent_core`, `tests/agent_core`)
- **Workflow Spec Invariants**:
  - Empty workflow specifications (`steps=[]`) strictly rejected at Pydantic validator layer (`packages/agent_core/workflows/schema.py`).
  - Specs composed solely of compensation target steps without forward execution steps rejected with descriptive `ValueError`.
  - Workflow engine runtime fail-safe (`packages/agent_core/workflows/engine.py`) guards against empty forward step executions.
- **Memory & Storage**:
  - Multi-tenant `workspace_id` scoping validated against real PostgreSQL instances (`tests/agent_core/memory/providers/test_postgres_store.py`).
  - Source provenance and run ID tracking preserved across lifecycle transitions.

### 3.2. COSA Control Plane & Apps (`services/cosa`, `apps/cosa`)
- **Worker Crash Recovery & Sweeper Fencing**:
  - Subprocess crash recovery verified end-to-end (`tests/apps/cosa/worker/test_crash_recovery_subprocess.py`).
  - Durable claim tokens prevent split-brain double executions upon worker recovery.
- **Fail-Closed DB Configuration**:
  - Removed all hardcoded development credentials (`DEV_COSA_DB_URL`).
  - Dynamic resolution via `resolveCosaDatabaseUrl()` throws descriptive errors naming missing environment variables (`tests/db-url-resolution.test.ts`).

### 3.3. Company Microservices (`services/company`)
- **Tenant Isolation & Query Scoping (Part 1 Remediation)**:
  - 7 core services updated to enforce `where(and(eq(table.workspaceId, ctx.workspaceId), eq(table.id, id)))`:
    - Commercial: Customer, Contact, Account, Sales Lead, Sales Opportunity.
    - Finance & Legal: Financial Transaction, Legal Obligation.
  - Dedicated cross-tenant isolation test suites:
    - `commercial/tests/tenant-isolation.test.ts` (5 tests)
    - `finance-legal/tests/tenant-isolation.test.ts` (2 tests)
- **Task Contract Parity (Part 3 Remediation)**:
  - Backend `task.handler.ts` (`listTasks`) reads tenant context via `Header<"X-Workspace-Id">`.
  - Full parity contract tests: `operations/tests/task-contract.test.ts` (4 tests).

### 3.4. Flutter Frontend (`frontend/`)
- **Task Module Remediation**:
  - `TaskService` relies strictly on `ApiClient` `X-Workspace-Id` header (removed query parameter duplication and `'1'` fallback).
  - Explicit typed exceptions for 401/403 (`AuthenticationException`), 404 (`NotFoundException`), and network errors.
  - Added `getTask(id)` API implementation matching backend `GET /operations/tasks/:id`.
  - UI controller optimistically updates task states with error handling and state rollback.

---

## 4. Verification Commands

To reproduce the complete verification suite locally:

```bash
# 1. Verify all fast local checks, unit tests, integration tests, boundary checks, and doc links:
make verify-local

# 2. Verify all TypeScript microservices (Company + COSA):
make services-test

# 3. Verify complete project suite (Python, TS, Flutter, Link Checker, Analyzer):
make verify
```
