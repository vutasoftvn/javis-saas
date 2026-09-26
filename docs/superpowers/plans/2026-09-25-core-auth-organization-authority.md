# Core Auth and Organization Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Core membership authority, internal worker authentication, Organization UI contracts and identity-profile ownership safe, durable and truthful.

**Architecture:** Core remains the source of truth. Company accepts only verified local projections that can be revoked by versioned Core-origin events; COSA coordinates projection and invitation reconciliation. A shared Company verifier removes per-handler credential fallbacks, while Flutter moves to a small server-authorized Organization API.

**Tech Stack:** TypeScript/Encore, Drizzle/PostgreSQL, Python/FastAPI worker clients, Flutter/Dart, transactional outbox/inbox, Vitest, pytest and Flutter integration tests.

**Spec:** `docs/superpowers/specs/2026-09-25-core-auth-organization-authority-design.md`

## Global Constraints

- Core is the final authority for identity, active organization membership, role and action; no caller-supplied scope or role can override it.
- Keep Core opaque OIDC access tokens, Company local-session JWTs and COSA delegations cryptographically and semantically separate.
- All schema changes are expand-only and backward compatible; no destructive cleanup in this workstream.
- Do not preserve a static worker token/key fallback outside explicit test fixtures.
- A revocation may never be converted into local/offline write access; reconciliation only moves a projection forward by membership version.
- Do not create an AI workforce member from a client-supplied prompt/spec/capability or arbitrary principal identifier.
- Preserve local-first data residency: no business payload is copied to Core merely to implement revocation.
- Work directly on `main`; preserve unrelated user changes; do not commit or push unless requested.

## Review Focus

- Missing `WORKER_SERVICE_JWT_SECRET` in staging/production rejects every internal worker request before any business lookup; Task 1.
- A valid worker token for workspace A cannot read or mutate authority/callback state in workspace B; Task 2.
- An out-of-order old `membershipVersion` event cannot reactivate a revoked local membership; Task 3.
- A revoked user with an unexpired local JWT cannot make a Company mutation or renew offline authority; Task 4.
- Flutter receives 401/403/404/422 from Organization API and shows an error rather than replacing data with `null`; Task 6.

## File structure and dependency graph

```text
Task 1 shared worker verifier + runtime configuration
  └─> Task 2 migrate all internal callback/authority/event handlers

Task 3 Core membership event + COSA/Company versioned projection
  └─> Task 4 local-session revocation and reconciliation E2E

Task 5 Company Organization API and workforce authorization
  └─> Task 6 Flutter Organization client/view contract

Task 7 Core-owned profile mutation + COSA preference split
Task 8 invitation grant saga/reconciliation
  └─> Task 9 cross-plane release proof and rollout
```

| Area | Existing files | Planned new files |
|---|---|---|
| Worker auth | `services/company/operations/handlers/*internal*.ts`, `services/company/events/services/agent-runtime-signal.service.ts`, `apps/cosa/*/*client.py` | `services/company/shared/auth/worker-service-auth.ts`, `services/company/shared/auth/worker-service-auth.test.ts` |
| Membership propagation | `backend/core/organization/outbox/*`, `services/cosa/services/core-projection.service.ts`, `services/company/identity/services/sync.service.ts` | Company membership-event consumer/reconciliation service and tests |
| Organization API | `services/company/identity/services/workforce.service.ts`, `frontend/lib/modules/organization/*` | Company Organization handler/service/DTO tests; Flutter API/error models |
| Profile | `services/cosa/services/auth.service.ts`, `frontend/lib/modules/auth/services/auth_service.dart` | Core-profile adapter tests, COSA preference handler tests |
| Invitation recovery | `services/cosa/services/workspace-invitation.service.ts` | invitation reconciliation job/tests |

### Task 1: Centralize and fail-close worker-service authentication

**Files:**
- Create: `services/company/shared/auth/worker-service-auth.ts`
- Create: `services/company/shared/auth/worker-service-auth.test.ts`
- Modify: `services/company/shared/env.ts`
- Modify: `deploy/central_vps/docker-compose.prod.yaml`
- Modify: `scripts/check-dev-preflight.sh`

**Consumes:** `WORKER_SERVICE_JWT_SECRET`, current environment classifier and JWT library.

**Produces:** `requireWorkerServiceAuth(headers): WorkerServiceClaims` with no implicit defaults.

- [ ] **Step 1: Write failing unit tests for environment and claim validation.**

  Add tests for: missing secret in production; static `dev-worker-service-token`; wrong `iss`; wrong `aud`; expired token; and valid short-lived token. The production-missing-secret assertion is:

  ```ts
  await expect(() => requireWorkerServiceAuth({ authorization: "Bearer anything" }))
    .rejects.toMatchObject({ code: "internal" });
  ```

- [ ] **Step 2: Run the focused test red.**

  Run: `cd services/company && npx vitest run shared/auth/worker-service-auth.test.ts`

  Expected: FAIL because the shared verifier does not exist and existing handlers accept static defaults.

- [ ] **Step 3: Implement a single verifier.**

  Define `WorkerServiceClaims` exactly as the spec and use `jwt.verify(token, requiredSecret, { audience: "company-internal", issuer: "apps-cosa" })`. In non-development/test, reject absent or `<32`-character secret. In test, inject a test secret through a factory; never retain `"dev-worker-service-token"` in production code.

- [ ] **Step 4: Make deploy/preflight contracts match the verifier.**

  Require `WORKER_SERVICE_JWT_SECRET` and document issuer/audience. Do not add `COSA_WORKER_SERVICE_TOKEN` as an alternate raw bearer bypass.

- [ ] **Step 5: Run focused green checks.**

  Run: `cd services/company && npx vitest run shared/auth/worker-service-auth.test.ts && npm run typecheck`

  Expected: PASS; production configuration cannot silently fall back.

### Task 2: Apply worker authentication and bind callbacks to durable authority

**Files:**
- Modify: `services/company/operations/handlers/founder-asset-authoring.handler.ts`
- Modify: `services/company/operations/handlers/executive-deliberation-internal.handler.ts`
- Modify: `services/company/operations/handlers/project-startup-team.handler.ts`
- Modify: `services/company/operations/handlers/founder-asset-deployment.handler.ts`
- Modify: `services/company/operations/services/automation-outcome.service.ts`
- Modify: `services/company/events/services/agent-runtime-signal.service.ts`
- Modify: matching `services/company/**/tests/*worker*` and handler tests
- Modify: `apps/cosa/company/executive_board_client.py`, `apps/cosa/company/project_team_client.py`, `apps/cosa/events/*.py`

**Consumes:** `requireWorkerServiceAuth` from Task 1.

**Produces:** All internal routes reject unauthenticated/default tokens and bind claims to expected workspace/run/worker records.

- [ ] **Step 1: Write negative handler tests before migration.**

  For every listed endpoint, call the exported handler with `serviceToken: "dev-worker-service-token"` under production config and assert `unauthenticated` or `internal`. Add cross-workspace authority test:

  ```ts
  await expect(getProjectDeploymentAuthorityApi({
    serviceToken: tokenFor("worker-a"), workspaceId: workspaceB,
    projectId: projectB, workspaceAgentId: agentB,
  })).rejects.toMatchObject({ code: "permission_denied" });
  ```

- [ ] **Step 2: Run the focused tests red.**

  Run: `cd services/company && npx vitest run operations/tests/founder-asset-deployment.handler.test.ts operations/tests/project-startup-team.handler.test.ts operations/tests/automation-outcome.service.test.ts events/tests/agent-runtime-signal.test.ts`

  Expected: FAIL on default-token acceptance.

- [ ] **Step 3: Replace every local verifier with the shared verifier.**

  Remove duplicated `DEV_WORKER_JWT_SECRET`, raw token equality and local `jwt.verify` helpers. Pass verified `sub` into domain service and require it to equal the durable worker/lease owner where that record exists; do not use `userId: "0"` as authority.

- [ ] **Step 4: Update apps/cosa clients to mint a short-lived signed JWT.**

  Configure issuer `apps-cosa`, audience `company-internal`, role `worker_service`, immutable worker `sub`, `jti` and expiry. Client construction fails outside test if signing config is missing.

- [ ] **Step 5: Run focused green tests.**

  Run: `cd services/company && npx vitest run operations/tests/founder-asset-deployment.handler.test.ts operations/tests/project-startup-team.handler.test.ts operations/tests/automation-outcome.service.test.ts events/tests/agent-runtime-signal.test.ts && npm run typecheck`

  Expected: PASS; no source under `services/company` accepts `dev-worker-service-token`.

### Task 3: Propagate Core membership state as a versioned projection

**Files:**
- Modify: `backend/core/organization/outbox/outbox-relay.service.ts`
- Modify: `backend/core/foundation/contracts/organization-events.ts`
- Modify: `services/cosa/services/core-projection.service.ts`
- Modify: `services/company/identity/services/sync.service.ts`
- Modify: Company identity schema/migration files for `membershipState`, `sourceMembershipVersion`, `revokedAt`
- Create: Company membership-event consumer/service and focused tests

**Consumes:** Core `organization.membership.changed.v1` durable event.

**Produces:** `applyMembershipProjection(event)` applies only newer membership versions and tombstones revoked membership.

- [ ] **Step 1: Write failing event-order tests.**

  Define fixtures for version 3 active, version 4 revoked, then replay version 3. Assert active → revoked → revoked; assert no local role is restored by stale input.

- [ ] **Step 2: Run the focused tests red.**

  Run the Core organization event tests and new COSA/Company projection tests. Expected: FAIL because Company currently only upserts active list results.

- [ ] **Step 3: Add expand-only schema and contract.**

  Store `membership_state` (`active|revoked`), nullable `revoked_at`, and `source_membership_version`. Add a unique event id/inbox record. Core event includes stable IDs and version only; it contains no access token, email or business payload.

- [ ] **Step 4: Implement idempotent forward-only apply.**

  In one transaction, ignore event version `<= sourceMembershipVersion`; otherwise upsert active state or tombstone revoked state. Audit the state transition with correlation/event ID. Never delete history during this task.

- [ ] **Step 5: Run focused green and migration gates.**

  Run relevant Core/COSA/Company tests plus `git diff --check` and the repository migration compatibility check. Expected: duplicate/out-of-order delivery is deterministic.

### Task 4: Enforce revocation in Company authorization and reconcile gaps

**Files:**
- Modify: `services/company/identity/services/tenant-context.service.ts`
- Modify: `services/company/identity/services/token.service.ts`
- Modify: `services/company/identity/handlers/auth.handler.ts`
- Create: `services/company/identity/services/membership-reconciliation.service.ts`
- Modify: `services/company/identity/tests/tenant-context.test.ts`, `session-renew.test.ts`, add process E2E

**Consumes:** tombstone/version data from Task 3.

**Produces:** revoked memberships fail every mutation and cannot extend local authority without fresh active confirmation.

- [ ] **Step 1: Write failing revoked-session tests.**

  Create a valid local JWT, tombstone its workspace membership, then call a representative write endpoint and session renew. Assert `permission_denied` for write and no new session authority for the revoked workspace.

- [ ] **Step 2: Run red tests.**

  Run: `cd services/company && npx vitest run identity/tests/tenant-context.test.ts identity/tests/session-renew.test.ts`

  Expected: FAIL because current lookup does not filter membership state.

- [ ] **Step 3: Enforce active membership and session epoch.**

  Require `membershipState === "active"` in `resolveTenantContext`. Bind JWT to a session epoch; revocation increments the organization epoch. Renewal verifies active membership and does not increase offline read validity without a fresh authoritative observation.

- [ ] **Step 4: Implement bounded reconciliation.**

  Reconcile only locally active memberships with missing/aged source observation, request authoritative status through COSA/Core, and apply only newer versions. Network errors leave status unchanged but do not authorize a mutation that needs confirmation.

- [ ] **Step 5: Prove cross-plane behavior.**

  Add a disposable PostgreSQL/process E2E: grant membership, sync Company, issue local session, revoke in Core, relay event, assert Company write fails, replay old event and assert it stays denied. Record infrastructure absence as `UNVERIFIED_ENVIRONMENT`, not a pass.

### Task 5: Build the server-authoritative Organization and AI workforce API

**Files:**
- Create: `services/company/operations/handlers/organization-overview.handler.ts`
- Create: `services/company/operations/services/organization-overview.service.ts`
- Create: `services/company/operations/handlers/ai-workforce.handler.ts`
- Modify: `services/company/identity/services/workforce.service.ts`
- Modify: `services/company/identity/services/permissions.service.ts` and permission catalog
- Create: focused handler/service tests

**Consumes:** `requireWorkspaceAccess`, active membership state, a workspace-agent ownership resolver.

**Produces:** typed overview/workforce APIs and `createAiWorkforceMember(ctx, input)`.

- [ ] **Step 1: Write red contract/authorization tests.**

  Assert a member can read overview but cannot create AI workforce; a founder can create using an in-workspace deployable agent; a foreign agent id, a `systemPrompt`, or mismatched path/header organization returns 403/400.

- [ ] **Step 2: Run focused tests red.**

  Run the new Company handler/service tests. Expected: FAIL because the contract and role gate do not exist.

- [ ] **Step 3: Define DTOs and explicit permission.**

  Implement `OrganizationOverviewResponse`, `WorkforceListResponse`, and `CreateAiWorkforceRequest` exactly as in the spec. Add `organization.workforce.manage`; founder/co-founder owns it initially. The handler requires path/header equality and `requireWorkspaceAccess` before query.

- [ ] **Step 4: Restrict workforce persistence.**

  Make public generic workforce creation unavailable for client-controlled AI specs. Resolve `workspaceAgentId` server-side, validate organization ownership/deployability, store the canonical reference and idempotency key, then return durable member ID.

- [ ] **Step 5: Run green tests and Company typecheck.**

  Run: `cd services/company && npx vitest run operations/tests/organization-overview.handler.test.ts operations/tests/ai-workforce.handler.test.ts identity/tests/workforce.test.ts && npm run typecheck`

  Expected: PASS; no member can create arbitrary AI workforce.

### Task 6: Replace obsolete Flutter Organization calls with typed contract calls

**Files:**
- Modify: `frontend/lib/modules/organization/services/organization_service.dart`
- Modify: `frontend/lib/modules/organization/controllers/organization_controller.dart`
- Modify: `frontend/lib/modules/organization/views/organization_view.dart`
- Create: `frontend/lib/modules/organization/models/organization_api_models.dart`
- Modify/Create: `frontend/test/organization_service_test.dart`, controller and widget tests

**Consumes:** Task 5 endpoint DTOs.

**Produces:** typed API client states and truthful error UX.

- [ ] **Step 1: Write failing Flutter service tests.**

  Assert requests target `/operations/organizations/{id}/overview` and `/ai-workforce`, use camelCase `workspaceAgentId`/`roleTitle`, and map 401/403/404/422 to explicit error states.

- [ ] **Step 2: Run red Flutter tests.**

  Run: `cd frontend && flutter test test/organization_service_test.dart test/modules/organization`

  Expected: FAIL because current service targets nonexistent `/org/*` and returns `null` for every failure.

- [ ] **Step 3: Implement models and result states.**

  Replace nullable map responses with sealed success/error result types. Retain existing successful view data while a refresh fails; render login/permission/not-found/validation/unavailable messages distinctly. Do not show a success toast unless returned member ID is non-empty.

- [ ] **Step 4: Remove unsupported UI input.**

  Replace `departmentId` and `systemPrompt` input with a server-listed workspace agent selector. The UI never transmits raw prompts/specs/capabilities.

- [ ] **Step 5: Run focused green tests and analysis.**

  Run: `cd frontend && flutter test test/organization_service_test.dart test/modules/organization && flutter analyze`

  Expected: PASS; offline/error state is visible and no `/org/` call remains.

### Task 7: Move Core-owned profile mutations out of COSA

**Files:**
- Modify: `services/cosa/services/auth.service.ts`
- Modify: `services/cosa/handlers/auth.handler.ts`
- Modify: `frontend/lib/modules/auth/services/auth_service.dart`
- Modify: `frontend/lib/modules/auth/services/core_auth_client.dart`
- Modify: Core authenticated profile handler/service and tests
- Modify: COSA auth/profile tests and Flutter auth tests

**Consumes:** Core authenticated profile API and COSA user projection.

**Produces:** Core contact/profile update client plus COSA-only preference route.

- [ ] **Step 1: Write red ownership tests.**

  Assert a phone update from Flutter calls Core and a COSA profile update cannot mutate `cosa.users.phone`. Assert locale update still persists only in COSA preference storage.

- [ ] **Step 2: Run focused red tests.**

  Run Core profile tests, COSA `auth-profile-locale` tests and Flutter auth tests. Expected: FAIL because COSA currently writes contact/profile fields.

- [ ] **Step 3: Split the endpoint contracts.**

  Core receives phone/display name/avatar mutations and applies its verification policy. COSA route accepts only `preferredLocale`, `headline`, `bio`; reject `phone`, `email`, `display_name`, `full_name`, `avatar_url` with `invalid_argument`.

- [ ] **Step 4: Refresh read projection after Core mutation.**

  Return Core's canonical response; then trigger/read a projection refresh. A projection refresh failure is an explicit degraded state, never a false success for Core mutation.

- [ ] **Step 5: Run focused green checks.**

  Run relevant Core/COSA/Flutter focused suites and static API contract check. Expected: contact data has one writer.

### Task 8: Make invitation Core-grant projection recoverable

**Files:**
- Modify: `services/cosa/services/workspace-invitation.service.ts`
- Modify: COSA schema/migration/outbox files
- Create: `services/cosa/services/invitation-membership-reconciliation.service.ts`
- Modify: `services/cosa/tests/invitation-core-grant.test.ts` and invitation tests

**Consumes:** Core idempotent membership grant and versioned membership query/event from Task 3.

**Produces:** durable invitation grant state machine and reconciliation job.

- [ ] **Step 1: Write red ambiguous-outcome tests.**

  Simulate Core grant success followed by COSA transaction/projection failure. Assert invitation remains recoverable, retry creates no duplicate Core/local membership, and audit state transitions are `requested → core_granted → projected`.

- [ ] **Step 2: Run red tests.**

  Run: `cd services/cosa && npx vitest run tests/invitation-core-grant.test.ts tests/workspace-invitation.test.ts`

  Expected: FAIL because Core HTTP call occurs inside the local transaction without durable saga state.

- [ ] **Step 3: Persist grant intent before external call.**

  Insert a unique invitation-grant operation/outbox record keyed by invitation/user. Worker calls Core idempotently, stores Core version/result, then commits local projection and accepted invitation in a separate local transaction.

- [ ] **Step 4: Implement reconciliation.**

  For nonterminal operations, query Core only for the recorded organization/user, reconcile authoritative state, and do not infer success from transport timeout. Store sanitized audit metadata only.

- [ ] **Step 5: Run green tests and typecheck.**

  Run: `cd services/cosa && npx vitest run tests/invitation-core-grant.test.ts tests/workspace-invitation.test.ts && npm run typecheck`

  Expected: PASS; duplicate retries are idempotent and ambiguity is visible/recoverable.

### Task 9: Cross-plane evidence, rollout and removal gates

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Modify: relevant generated contract/check scripts only through their canonical generator
- Create: cross-plane E2E scenario for worker auth, membership revoke and Organization workflow
- Modify: deployment runbook/preflight documentation

**Consumes:** Tasks 1–8.

**Produces:** release gate evidence proving behavior, not only mocked unit tests.

- [ ] **Step 1: Add process E2E scenarios.**

  Cover: missing worker secret cannot start safe production configuration; forged/default credential rejected; Core revoke propagates and blocks Company write; stale event cannot reactivate; founder creates AI workforce with valid agent; member is denied; Flutter receives a usable error response.

- [ ] **Step 2: Run disposable PostgreSQL/process E2E.**

  Run the repository cross-plane smoke target with isolated databases. Expected: all scenarios pass. If the environment cannot start required PostgreSQL/processes, save exact blocker as `UNVERIFIED_ENVIRONMENT`.

- [ ] **Step 3: Run focused static and client gates.**

  Run Company/COSA typechecks, relevant Vitest suites, Flutter tests/analyze, contract generation in `--check` mode, auth allowlist and `git diff --check`.

- [ ] **Step 4: Stage rollout.**

  Deploy schema/event consumers in observe mode; measure Core-vs-projection membership versions and unresolved invitation operations. Enable write denial after zero unexplained drift for the agreed soak window, rotate worker secrets, then release Flutter contract.

- [ ] **Step 5: Verify removal conditions.**

  Only remove obsolete `/org/*` client paths and old COSA contact writes after E2E and staging evidence pass. Never restore raw worker token fallback as rollback.

## Plan self-review

- Spec coverage: Tasks 1–2 cover internal credentials; 3–4 cover revocation/projection; 5–6 cover Organization contract; 7 covers profile ownership; 8 covers invitation saga; 9 covers rollout evidence.
- Placeholder scan: no deferred design placeholders; every task identifies concrete files, interface and observable test behavior.
- Type consistency: `WorkerServiceClaims`, `membershipVersion`, `membershipState`, `workspaceAgentId` and `CreateAiWorkforceRequest` are used consistently across tasks.
- Review focus coverage: each of the five stated cases is asserted in its owning task.

## Trạng thái thực thi (2026-09-26)

| Task | Trạng thái | Ghi chú |
|---|---|---|
| 1–3 | DONE | Verifier JWT worker dùng chung, callback bind authority, consumer event membership forward-only (PR core-auth). |
| 4 | DONE (có giới hạn) | Session epoch: cột `core.workspace_memberships.session_not_before` (migration identity 006); tenant context, `/identity/me`, renew từ chối session có `auth_time` không sau mốc thu hồi. Đối soát: `/identity/me` trả `membershipObservedAt`/`membershipObservationStale`; Flutter chạy lại `/identity/sync-from-platform` bằng token Core khi quá tuổi (giãn cách 5 phút, lỗi giữ nguyên trạng thái). |
| 5–8 | DONE | Organization API + Flutter typed, preference COSA, saga invitation (PR core-auth). |
| 9 | CHƯA LÀM | Rollout/soak và điều kiện gỡ đường cũ. |

**Giới hạn đã biết của Task 4:** Company không có credential dịch vụ để tự hỏi Core
trạng thái membership, và bản chiếu `cosa.organization_memberships` không có
version/trạng thái thu hồi. Vì vậy đối soát chạy khi client có token Core của người
dùng; job nền phía server cần Core mở API dịch vụ đọc membership (ngoài repo này)
và một quyết định về credential mới (ADR-COSA-DELEGATION-002). Producer event
`organization.membership.changed.v1` nằm ở `backend/core`, cũng ngoài repo.

**Chưa kiểm chứng:** `encore test` và E2E process thật
(`tests/e2e/test_membership_session_epoch_http.py`): môi trường thực thi không tải
được Encore CLI (proxy chặn `encore.dev`) → `UNVERIFIED_ENVIRONMENT`. Đã chạy:
`tsc --noEmit`, migration compat, schema fingerprint trên Postgres 16 thật, gate
boundary/handler/suppression/route-auth/contract-freeze, Flutter test + analyze.
