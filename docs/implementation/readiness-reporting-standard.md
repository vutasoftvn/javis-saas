# Development Readiness & Reporting Standard (2026-08-28)

## 1. Overview & Principles

This standard establishes mandatory development readiness, code quality, and verification gates for the `javis-saas` project across all engineering disciplines.

### Core Invariants:
1. **Single Source of Truth**: All architectural decisions must align with current schemas, ADRs, and implementation docs. Speculative or phantom contracts are strictly forbidden.
2. **Fail-Closed Security & Tenancy**:
   - Every single-record query and mutation must scope by `workspace_id`.
   - Missing configuration or secrets must immediately raise fatal runtime errors rather than falling back to insecure development defaults.
3. **Verified Reproducibility**: No feature or fix is complete without automated regression tests and local verification passing 100%.

---

## 2. Readiness Checklists by Layer

### 2.1. Backend Microservices (`services/company`, `services/cosa`)
- [ ] **Tenant Scoping**: All database queries (`select`, `update`, `delete`) must include `eq(table.workspaceId, ctx.workspaceId)` in their where clauses.
- [ ] **Header-First Context**: Endpoints must extract tenant context via `Header<"X-Workspace-Id">` instead of URL query parameters or request bodies.
- [ ] **Database Connection Security**: DB URL resolvers must strictly throw `Error("Missing required environment variable ...")` without hardcoded fallback credentials.
- [ ] **Container Image Pinning**: All images in Docker Compose and Kubernetes manifests must specify immutable semantic version tags (never `:latest`).
- [ ] **Durable Coordination**: Scheduled tasks, leases, and worker claims must use fencing tokens and atomic CAS operations (`FOR UPDATE SKIP LOCKED`).

### 2.2. Python Core & Agents (`packages/agent_core`, `apps/cosa`)
- [ ] **DAG Invariants**: Workflow specs must undergo schema validation ensuring non-empty step collections and preventing all-compensation DAG configurations.
- [ ] **Layer Boundaries**: `packages/agent_core` must never import from `services/` or `apps/`.
- [ ] **Subprocess Resilience**: Long-running background processes must support graceful SIGTERM and clean recovery from unexpected worker exits.

### 2.3. Flutter Frontend (`frontend/`)
- [ ] **Typed Error Handling**: HTTP client calls must catch status codes (401, 403, 404, 500) and throw structured typed exceptions.
- [ ] **Tenant Header Injection**: All API calls must utilize `ApiClient` which automatically injects `X-Workspace-Id` and Bearer authentication headers.
- [ ] **Optimistic UI Rollback**: Optimistic state updates must be enclosed in `try-catch` blocks that restore previous state upon network or server failures.
- [ ] **Zero Static Analysis Errors**: `flutter analyze` must report 0 issues before merging.

---

## 3. Mandatory CI / Local Verification Gates

Before submitting code reviews or deploying to staging/production, developers must execute and pass the standard verification targets:

```bash
# Gate 1: Fast Local Checks
make verify-local

# Gate 2: Full Integration & Service Verification
make verify
```

### Gate Pass Criteria:
- `boundary-check`: 0 illegal layer cross-dependencies.
- `tenancy-check`: 0 unsecured database queries.
- `check-docs`: 0 broken relative internal markdown links.
- `flutter analyze`: 0 analysis warnings or errors.
- `test suites`: 100% pass rate across Pytest, Vitest, and Flutter test suites.
