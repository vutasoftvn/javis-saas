# Workspace-Canonical M2 Cutover Execution Plan

> **Goal:** Execute the full transition from legacy `Company` aggregate to canonical `Workspace` tenancy across database schemas, backend services, agent policy snapshots, and Flutter client views.

---

## Wave 1: Schema Migration & Database Clean-up

### Task 1: Migrate Agent Policy Table to Workspace Boundary
- Migrate `control_plane.company_agent_policy` to `control_plane.workspace_agent_policy` with `workspace_id` primary/foreign key.
- Update Drizzle models in `services/cosa/models/db.ts` and `services/cosa/storage/schema.ts`.
- Verify: `cd services/cosa && pnpm vitest run tests/agent-policy.test.ts`

### Task 2: Drop Legacy Companies Schema Tables
- Apply migration to drop unused legacy `control_plane.companies`, `control_plane.company_memberships`, `control_plane.licenses`.
- Ensure `control_plane.platform_workspaces` and `control_plane.workspace_memberships` serve all tenant relationships.

---

## Wave 2: COSA Backend & Auth Service Cutover

### Task 3: Pivot Platform Registration & Auth to Workspace Exclusively
- In `services/cosa/services/auth.service.ts`:
  - Update `RegisterParams`: remove `company_name`, `join_company_id`; require `workspace_name` or `join_workspace_id`.
  - Update `TokenResponse`: return `workspace_id`, remove `company_id`.
- Update `services/cosa/services/agent-policy.service.ts` to query `workspace_agent_policy`.
- Verify: `cd services/cosa && pnpm vitest run tests/auth.test.ts tests/agent-policy.test.ts`

### Task 4: Deprecate Legacy Company Handlers
- Mark `/platform/auth/companies/*` in `services/cosa/handlers/company.handler.ts` as `410 Gone` or redirect to `/platform/workspaces/*`.
- Verify: `cd services/cosa && pnpm vitest run tests/company-handler.test.ts`

---

## Wave 3: Client (Flutter) & Shared Models Cutover

### Task 5: Update Flutter Auth Controller & Registration Flow
- In `frontend/lib/modules/auth/controllers/auth_controller.dart` & `register_view.dart`:
  - Replace company creation/joining fields with workspace creation/joining fields (`workspaceName`, `joinWorkspaceId`).
  - Update `auth_service.dart` API payloads.
- Verify: `cd frontend && flutter test test/modules/auth/auth_flow_test.dart`

### Task 6: Replace Company Scope Switcher with Workspace Scope Switcher
- Refactor `frontend/lib/shared/widgets/company_scope_switcher.dart` to `workspace_scope_switcher.dart`.
- Update navigation shell, drawer, and app bar headers.
- Verify: `cd frontend && flutter test && flutter analyze`

---

## Wave 4: Final Deprecation & Verification Gates

### Task 7: End-to-End Tenancy Verification & Gate Run
- Run full repository validation:
  - `make lint`
  - `make typecheck-py`
  - `make boundary-check`
  - `make contract-freeze-check`
  - `make check-docs`
  - `cd services/cosa && pnpm typecheck && pnpm test`
  - `cd services/company && pnpm typecheck && pnpm test`
  - `cd frontend && flutter test && flutter analyze`
