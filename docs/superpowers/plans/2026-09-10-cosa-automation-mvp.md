# COSA Automation MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a governed, curated Automation MVP: a workspace can configure and invoke approved blueprints, inspect a pinned execution, resolve an exact approval, and recover safely from duplicate delivery, worker failure, or cancellation.

**Architecture:** `services/company` owns definitions, revisions, invocations and user-visible outcome projection; `services/cosa` owns opaque dispatch, schedule delivery and fenced worker claims; `packages/agent` and `apps/cosa` own the immutable execution manifest, run/checkpoint/tool-call lifecycle and Capability Gateway; Flutter renders a manifest-gated Automation Library, Needs You and Run Inspector. Cross-plane messages carry opaque IDs and hashes only. The Agent Platform never writes the Company database directly.

**Tech Stack:** PostgreSQL, Encore/TypeScript and Drizzle, Python/asyncpg/Pydantic, Flutter/GetX, Node test/Vitest, pytest, Flutter test, disposable three-plane PostgreSQL/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md`

## Global Constraints

- Work directly on `main`; do not create a Git worktree.
- Preserve unrelated working-tree changes. Recheck `git status --short` before every task and stage only listed files.
- Add only expand-only `002_cosa_automation_mvp` migrations after `001_founder_trial_mvp_baseline`; include compatible rollback proof where the plane supports down migrations.
- Company is business authority. No Python/Agent code may import a Company database URL, schema, ORM, or issue Company SQL.
- All identifiers at HTTP and Flutter boundaries, including Snowflake IDs, remain strings.
- Every public route has handler authorization, tenant-scoped service access, an enabled `shared/contracts/mvp-surface.json` entry, generated-client refresh, backend negative tests and Flutter typed-client coverage.
- Define no generic workflow DSL, YAML/DAG editor, user-supplied code, arbitrary HTTP connector, dynamic plugin, MCP auto-discovery, commercial delivery, finance posting or legal-regime change.
- Queue/event/scheduler payloads contain IDs, version/hash, trigger identity and correlation ID only; never raw Company records, prompts, credentials, connector grants, approval evidence or business documents.
- A capability effect is allowed only through the existing Capability Gateway with a stable idempotency key. Retrying non-idempotent effects is forbidden.
- Approval is valid only for the exact `(run_id, tool_call_id, checkpoint_ref, manifest_hash)` and is authorized server-side.
- Cancellation is a durable compare-and-set transition. A stale lease holder or task claimant cannot write terminal success after cancellation/reclaim.
- All new visible Flutter strings include `vi-VN` and `en-US`; forbidden, unavailable, local-offline, pending approval, empty, failed and completed are separate states.

---

## Dependency order

~~~text
Task 1 contract + storage
        |
Task 2 definitions --------- Task 3 invocations/outbox
                                      |
                               Task 4 Control dispatch
                                      |
                            Task 5 Agent manifest/runtime
                                      |
                     Task 6 lifecycle/approval/outcome projection
                              |                       |
                   Task 7 Flutter Library      Task 8 Inspector/Needs You
                              \                       /
                               Task 9 rollout policy
                                      |
                             Task 10 process E2E/release
~~~

### Task 1: Freeze the Automation contract and add durable, isolated persistence

**Files:**

- Modify: `shared/contracts/mvp-surface.json`
- Regenerate: `services/company/shared/contracts/mvp-surface.generated.ts`
- Regenerate: `frontend/lib/core/network/mvp_endpoints.g.dart`
- Create: `shared/contracts/automation-envelope.v1.json`
- Create: `services/company/operations/migrations/002_cosa_automation_mvp.up.sql`
- Create: `services/company/operations/migrations/002_cosa_automation_mvp.down.sql`
- Create: `services/cosa/migrations/002_cosa_automation_mvp.up.sql`
- Create: `services/cosa/migrations/002_cosa_automation_mvp.down.sql`
- Create: `packages/agent/migrations/002_cosa_automation_mvp.sql`
- Create: `packages/agent/migrations/002_cosa_automation_mvp.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Modify: `packages/agent/runs/models.py`
- Create: `tests/contracts/test_automation_contract.py`
- Create: `tests/migrations/test_automation_migrations.py`

**Interfaces:**

- `AutomationDispatchEnvelopeV1` has exactly `schema_version`, `invocation_id`, `workspace_id`, `automation_key`, `revision`, `revision_hash`, `trigger_kind`, `trigger_identity`, `correlation_id`, `requested_at`; JSON schema rejects unknown keys.
- Required enabled capabilities: `automation.definition.list`, `automation.definition.get`, `automation.definition.configure`, `automation.definition.publish`, `automation.definition.suspend`, `automation.invocation.create`, `automation.invocation.get`, `automation.invocation.cancel`, `automation.run.inspector.read`, `automation.approval.decide`, `automation.needs_you.list`.
- Company owns `automation_definitions`, `automation_revisions`, `automation_invocations`, `automation_invocation_events`; every table has a tenant-leading index. Unique invocation identity is `(workspace_id, revision_id, idempotency_key)`.
- Agent owns `agent.automation_run_manifests(run_id, manifest_hash, manifest_json, created_at)`; Control owns `control_plane.automation_dispatches(invocation_id, task_id, claim_token, state, timestamps)`. Both store opaque references only.

- [ ] **Step 1: Write failing contract and migration tests**

Create `test_automation_contract.py`. Assert the exact capabilities are enabled, paths are unique, every listed backend/Flutter/E2E test file exists, and the envelope rejects `input_payload`, `prompt`, `credential`, or any unknown field.

Create `test_automation_migrations.py`. Apply each 002 migration over the corresponding 001 baseline on disposable databases. Assert tables, unique constraints and tenant-leading indexes. Assert no Company foreign key crosses a database boundary and Agent migration source has neither a Company connection setting nor Company table reference.

- [ ] **Step 2: Prove the tests are red**

Run:

~~~bash
.venv/bin/python -m pytest tests/contracts/test_automation_contract.py tests/migrations/test_automation_migrations.py -q
~~~

Expected: FAIL because the Automation surface, envelope and migrations do not exist.

- [ ] **Step 3: Implement the canonical surface and expand-only schemas**

Create the strict JSON schema; use strings for IDs and RFC 3339 for timestamps. Add Drizzle table exports that exactly match migration columns. Company foreign keys stay local to definition/revision tables. Agent manifest hash is immutable and `run_id` references existing `agent.runs`. Control's unique `invocation_id` records only dispatch fencing data.

Add only described capabilities to `mvp-surface.json`, with concrete source/test evidence. Run `make mvp-contracts-gen`; never hand-edit generated files.

- [ ] **Step 4: Verify and commit**

Run:

~~~bash
.venv/bin/python -m pytest tests/contracts/test_automation_contract.py tests/migrations/test_automation_migrations.py -q
make mvp-contracts-check mvp-surface-check migration-compat-check
git diff --check
~~~

Expected: PASS.

~~~bash
git add shared/contracts/automation-envelope.v1.json shared/contracts/mvp-surface.json \
  services/company/shared/contracts/mvp-surface.generated.ts frontend/lib/core/network/mvp_endpoints.g.dart \
  services/company/operations/migrations/002_cosa_automation_mvp.up.sql services/company/operations/migrations/002_cosa_automation_mvp.down.sql \
  services/cosa/migrations/002_cosa_automation_mvp.up.sql services/cosa/migrations/002_cosa_automation_mvp.down.sql \
  packages/agent/migrations/002_cosa_automation_mvp.sql packages/agent/migrations/002_cosa_automation_mvp.down.sql \
  services/company/shared/db/schema/operations.ts \
  services/cosa/storage/control-plane-schema.ts packages/agent/runs/models.py \
  tests/contracts/test_automation_contract.py tests/migrations/test_automation_migrations.py
git commit -m "feat(automation): add durable cross-plane contract"
~~~

### Task 2: Implement Company-owned definitions, immutable revisions and lifecycle authorization

**Files:**

- Create: `services/company/operations/services/automation-definition.service.ts`
- Create: `services/company/operations/handlers/automation-definition.handler.ts`
- Modify: `services/company/operations/api.ts`
- Create: `services/company/operations/tests/automation-definition.service.test.ts`
- Create: `services/company/operations/tests/automation-definition.handler.test.ts`

**Interfaces:**

- `listAutomationDefinitions(ctx)`, `getAutomationDefinition(ctx, id)`, `configureAutomationDefinition(ctx, id, command)`, `publishAutomationRevision(ctx, id, revision)`, `suspendAutomationDefinition(ctx, id)`.
- `AutomationRevisionInput` contains typed configuration, trigger, declared capability IDs, evidence policy, autonomy mode, approval requirement and pinned `agentSpecId`/skills; it has no free-form prompt, executable source, secret or connector grant.
- Lifecycle: `DRAFT -> PUBLISHED -> SUSPENDED -> RETIRED`. Publishing atomically changes the definition's current revision; published revisions are immutable.

- [ ] **Step 1: Write failing service and handler tests**

Seed two workspaces. Prove workspace B cannot list/read/configure/publish/suspend A. Prove duplicate automation key in one workspace fails while the same key in another succeeds. Prove a published revision is byte-identical after a later draft.

Reject unknown capabilities, unregistered blueprint key, execution autonomy without exact approval, non-system AgentSpec, prompt/source/connector fields and arbitrary URL. Handler tests must prove `requireWorkspaceAccess` and role/capability authorization execute before service calls.

- [ ] **Step 2: Prove the tests are red**

~~~bash
cd services/company && npx vitest run operations/tests/automation-definition.service.test.ts operations/tests/automation-definition.handler.test.ts
~~~

Expected: FAIL because definition services/routes do not exist.

- [ ] **Step 3: Implement fail-closed definition management**

Use Company tenant context and transactions only. Canonicalize typed JSON before producing `revision_hash`; validate it against a static curated-blueprint registry. Persist key/version, never executable content. Use `generateSnowflake()` internally and serialize IDs as strings.

Expose only contract routes. `publish` validates complete configuration, deterministic graph and capability policy in the transaction that changes state. `suspend` blocks future invocations but preserves history. Return the existing `mvpList`/`mvpItem` envelope with source references.

- [ ] **Step 4: Verify and commit**

~~~bash
cd services/company && npx vitest run operations/tests/automation-definition.service.test.ts operations/tests/automation-definition.handler.test.ts
cd ../.. && make frontend-api-contract-check
git diff --check
git add services/company/operations/api.ts services/company/operations/services/automation-definition.service.ts \
  services/company/operations/handlers/automation-definition.handler.ts \
  services/company/operations/tests/automation-definition.service.test.ts \
  services/company/operations/tests/automation-definition.handler.test.ts
git commit -m "feat(automation): govern immutable definition revisions"
~~~

Expected: PASS before commit.

### Task 3: Create idempotent invocations and an outbox-only Company-to-Agent handoff

**Files:**

- Create: `services/company/operations/services/automation-invocation.service.ts`
- Create: `services/company/operations/handlers/automation-invocation.handler.ts`
- Modify: `services/company/events/outbox-relay.service.ts`
- Modify: `services/company/operations/api.ts`
- Create: `services/company/operations/tests/automation-invocation.service.test.ts`
- Create: `services/company/events/tests/automation-outbox-relay.test.ts`

**Interfaces:**

- `createAutomationInvocation(ctx, definitionId, command)`, `getAutomationInvocation(ctx, invocationId)`, `cancelAutomationInvocation(ctx, invocationId, expectedVersion)`.
- Manual identity is workspace/revision/client request ID; scheduled identity is workspace/schedule/scheduled instant; event identity is workspace/trigger/event ID.
- `automation.invocation.requested.v1` exactly validates against `AutomationDispatchEnvelopeV1`.

- [ ] **Step 1: Write failing idempotency, cancellation and relay tests**

Test concurrent manual duplicate requests, repeated schedule ticks and duplicate event delivery; each yields one invocation/outbox event. Same idempotency key with a changed fingerprint rejects. Suspended definition or stale revision creates no event.

Test cancellation before dispatch becomes `CANCELLED`; cancellation after a known Agent reference sends one opaque cancel request. A foreign tenant gets no invocation detail. Relay tests verify signed emitted JSON matches the strict envelope and contains no input, prompt, secret, authorization, grant or document field.

- [ ] **Step 2: Prove the tests are red**

~~~bash
cd services/company && npx vitest run operations/tests/automation-invocation.service.test.ts events/tests/automation-outbox-relay.test.ts
~~~

Expected: FAIL because invocation/outbox behavior is absent.

- [ ] **Step 3: Implement transactionally**

In one transaction: lock/read published revision, derive idempotency key, insert `REQUESTED` invocation and append signed outbox event. On uniqueness conflict return only a matching immutable invocation/fingerprint. Never synchronously call Control or Agent.

Use the existing HMAC raw-bytes relay path. Remote retry keeps event ID/envelope. Cancellation uses optimistic version update and emits a reference cancellation event; it never contacts a worker directly.

- [ ] **Step 4: Verify and commit**

~~~bash
cd services/company && npx vitest run operations/tests/automation-invocation.service.test.ts events/tests/automation-outbox-relay.test.ts
cd ../.. && make company-boundary-check
git diff --check
git add services/company/operations/api.ts services/company/operations/services/automation-invocation.service.ts \
  services/company/operations/handlers/automation-invocation.handler.ts services/company/events/outbox-relay.service.ts \
  services/company/operations/tests/automation-invocation.service.test.ts services/company/events/tests/automation-outbox-relay.test.ts
git commit -m "feat(automation): enqueue idempotent invocation dispatch"
~~~

Expected: PASS before commit.

### Task 4: Add Control Plane dispatch, schedule identity and claim fencing

**Files:**

- Modify: `apps/cosa/events/router.py`
- Modify: `apps/cosa/events/event_run_contract.py`
- Modify: `apps/cosa/events/execution_plane_client.py`
- Modify: `services/cosa/services/control-plane-scheduler.service.ts`
- Create: `services/cosa/services/automation-dispatch.service.ts`
- Create: `apps/cosa/events/tests/test_automation_dispatch.py`
- Create: `services/cosa/tests/automation-dispatch.service.test.ts`

**Interfaces:**

- Intake accepts only signed `automation.invocation.requested.v1` and creates `task_type="automation_run"` from opaque envelope fields.
- `scheduleAutomationDispatch(envelope)` is idempotent on `invocation_id`. Scheduled identity is workspace + schedule/definition + scheduled time.
- `claimAutomationDispatch`, `heartbeatAutomationDispatch`, `completeAutomationDispatch` require current claim token; stale completion returns false without terminal mutation.

- [ ] **Step 1: Write failing delivery and fencing tests**

Send valid signed event, duplicate event and unknown-field event. Assert one inbox row/task for duplicates and rejection before scheduling for unsigned/cross-workspace/unknown input.

Create two claims on one expired dispatch. Prove claimant A cannot complete after B reclaims. Prove payload stores none of the forbidden content. Prove a scheduling collision returns original task ID.

- [ ] **Step 2: Prove the tests are red**

~~~bash
.venv/bin/python -m pytest apps/cosa/events/tests/test_automation_dispatch.py -q
cd services/cosa && npx vitest run tests/automation-dispatch.service.test.ts
~~~

Expected: FAIL because Automation dispatch is absent.

- [ ] **Step 3: Implement the narrow adapter**

Validate schema before `inbox.record`; do not route through generic EventTriggerRule policy. Insert/read dispatch by unique invocation ID then call existing scheduler with only allowed fields and target spec `cosa.agents.operations`. Reuse scheduler claim/heartbeat/complete fencing rather than another queue. Quarantine version/hash/state mismatches; no generic profile fallback.

- [ ] **Step 4: Verify and commit**

~~~bash
.venv/bin/python -m pytest apps/cosa/events/tests/test_automation_dispatch.py -q
cd services/cosa && npx vitest run tests/automation-dispatch.service.test.ts
cd ../.. && make lease-integration-test
git diff --check
git add apps/cosa/events/router.py apps/cosa/events/event_run_contract.py apps/cosa/events/execution_plane_client.py \
  services/cosa/services/control-plane-scheduler.service.ts services/cosa/services/automation-dispatch.service.ts \
  apps/cosa/events/tests/test_automation_dispatch.py services/cosa/tests/automation-dispatch.service.test.ts
git commit -m "feat(automation): fence opaque control-plane dispatch"
~~~

Expected: PASS before commit.

### Task 5: Pin Agent execution manifests and run only curated blueprints

**Files:**

- Create: `packages/agent/workflows/automation_manifest.py`
- Create: `packages/agent/workflows/automation_blueprints.py`
- Modify: `packages/agent/runs/repository.py`
- Modify: `packages/agent/runs/models.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Create: `packages/agent/tests/test_automation_manifest.py`
- Create: `apps/cosa/worker/tests/test_automation_run_task.py`

**Interfaces:**

- Immutable `AutomationExecutionManifest`: run/invocation/workspace IDs, key, revision/hash, pinned AgentSpec/skills/model policy, capability allowlist, approval/evidence policy, trigger identity and source refs only.
- `resolve_automation_manifest(envelope, definition_reader)` verifies published hash; `persist_automation_manifest(run_id, manifest)` is insert-once/hash-verifying.
- Exactly four initial functions: `operating.weekly-review`, `operations.task-follow-up`, `commercial.outbound-draft`, `strategy.initiative-health`. Outputs are recommendations/drafts/evidence, never delivery or authoritative mutation.

- [ ] **Step 1: Write failing manifest and blueprint tests**

Reject unknown key, changed hash, unpinned skill, unregistered capability, token/raw document. Same run ID cannot persist different manifest. Worker restart reloads persisted manifest rather than mutable current definition.

For each blueprint assert only declared read/draft/evidence Gateway calls. Commercial returns a draft artifact and never delivery. A `REMOTE_ACCESS` blueprint blocks with `LOCAL_RUNTIME_UNAVAILABLE` with no eligible local node and never cloud-falls back.

- [ ] **Step 2: Prove the tests are red**

~~~bash
.venv/bin/python -m pytest packages/agent/tests/test_automation_manifest.py apps/cosa/worker/tests/test_automation_run_task.py -q
~~~

Expected: FAIL because manifest persistence and `automation_run` handling are absent.

- [ ] **Step 3: Implement immutable allowlisted execution**

Reuse existing RunRecord/checkpoint/lease APIs. Before `RUNNING`, resolve/persist manifest and initialize run with matching `root_definition_hash`. Resume/reclaim loads it by run ID and compares hash.

Register blueprint functions in one explicit mapping. Functions receive manifest, Gateway and checkpoint writer, not generic callable/tool/network/Company repository. Effects use run/tool-call-derived idempotency keys. Persist artifact/evidence references and manifest snapshot, not raw contents.

- [ ] **Step 4: Verify and commit**

~~~bash
.venv/bin/python -m pytest packages/agent/tests/test_automation_manifest.py apps/cosa/worker/tests/test_automation_run_task.py -q
make python-test-unit
git diff --check
git add packages/agent/workflows/automation_manifest.py packages/agent/workflows/automation_blueprints.py \
  packages/agent/runs/repository.py packages/agent/runs/models.py apps/cosa/worker/main.py apps/cosa/worker/handlers.py \
  apps/cosa/composition/agent_plane.py packages/agent/tests/test_automation_manifest.py apps/cosa/worker/tests/test_automation_run_task.py
git commit -m "feat(automation): pin curated agent execution manifests"
~~~

Expected: PASS before commit.

### Task 6: Reconcile lifecycle, exact approvals, cancellation and outcomes without direct cross-plane writes

**Files:**

- Create: `apps/cosa/events/automation_outcome_client.py`
- Modify: `apps/cosa/api/approval_routes.py`
- Modify: `packages/agent/governance/approval_service.py`
- Modify: `packages/agent/runs/recovery.py`
- Create: `services/company/operations/handlers/automation-outcome.handler.ts`
- Create: `services/company/operations/services/automation-outcome.service.ts`
- Create: `packages/agent/tests/test_automation_lifecycle.py`
- Create: `services/company/operations/tests/automation-outcome.service.test.ts`

**Interfaces:**

- Agent sends signed `automation.run.state_changed.v1` and `automation.run.outcome.v1`; Company verifies signature and projects with invocation/version compare-and-set.
- `decideApproval(approvalId, decision, decisionVersion)` revalidates run/tool-call/checkpoint/manifest, reviewer role and current version.
- Terminal state machine forbids `CANCELLED -> COMPLETED`; cancellation propagates `CANCEL_REQUESTED -> CANCELLED` or existing terminal state.

- [ ] **Step 1: Write failing lifecycle race tests**

Create approval then decide it with wrong checkpoint, wrong manifest, foreign workspace reviewer, stale decision version and concurrent reviewers; exactly one valid decision wins.

Expire/reclaim worker lease then send stale completion. Race cancel with completion in both orders. Assert one terminal state, no second effect and matching Company projection. Company handler rejects invalid signature/cross-workspace/missing invocation without metadata leakage.

- [ ] **Step 2: Prove the tests are red**

~~~bash
.venv/bin/python -m pytest packages/agent/tests/test_automation_lifecycle.py -q
cd services/company && npx vitest run operations/tests/automation-outcome.service.test.ts
~~~

Expected: FAIL because Automation outcome reconciliation is absent.

- [ ] **Step 3: Implement durable transitions**

Keep approvals in Agent authority. All decisions/terminal writes are conditional on current state/version/lease token. Denied/expired approval resumes nothing; cancelled run gets no new lease; recovery only reclaims non-terminal work.

Agent client signs compact reference events to Company-owned handler. Company projects only allowed run state to invocation/runtime signals and treats event data as non-authoritative for business mutation. Replays are idempotent; out-of-order events cannot regress terminal state.

- [ ] **Step 4: Verify and commit**

~~~bash
.venv/bin/python -m pytest packages/agent/tests/test_automation_lifecycle.py -q
cd services/company && npx vitest run operations/tests/automation-outcome.service.test.ts
cd ../.. && make lease-integration-test
git diff --check
git add apps/cosa/events/automation_outcome_client.py apps/cosa/api/approval_routes.py \
  packages/agent/governance/approval_service.py packages/agent/runs/recovery.py \
  services/company/operations/handlers/automation-outcome.handler.ts services/company/operations/services/automation-outcome.service.ts \
  packages/agent/tests/test_automation_lifecycle.py services/company/operations/tests/automation-outcome.service.test.ts
git commit -m "feat(automation): reconcile governed run lifecycle"
~~~

Expected: PASS before commit.

### Task 7: Build the manifest-gated Flutter Automation Library and guided configuration

**Files:**

- Create: `frontend/lib/modules/automation/services/automation_service.dart`
- Create: `frontend/lib/modules/automation/models/automation_models.dart`
- Create: `frontend/lib/modules/automation/controllers/automation_library_controller.dart`
- Create: `frontend/lib/modules/automation/views/automation_library_view.dart`
- Create: `frontend/lib/modules/automation/views/automation_configuration_view.dart`
- Modify: `frontend/lib/core/routing/module_routes.dart`
- Modify: `frontend/lib/core/services/workspace_capability_manifest_service.dart`
- Modify: `frontend/assets/lang/vi-VN.json`
- Modify: `frontend/assets/lang/en-US.json`
- Create: `frontend/test/modules/automation/automation_service_test.dart`
- Create: `frontend/test/modules/automation/automation_library_controller_test.dart`
- Create: `frontend/test/modules/automation/automation_configuration_view_test.dart`

**Interfaces:**

- `AutomationService` calls generated endpoints only and parses the standard `mvpItem`/`mvpList` envelope.
- Route `/automation` exists only while `automation.definition.list` is enabled. Disabled capability removes navigation and sends no request.
- Card status is exactly `READY`, `SETUP_REQUIRED`, `SUSPENDED`, `UNAVAILABLE`, or `FORBIDDEN`; configuration renders typed fields only.

- [ ] **Step 1: Write failing client, navigation and localization tests**

Mock enabled, disabled, forbidden and source-unavailable manifest results. Assert disabled module makes no request. Widget tests assert purpose/setup/permissions/evidence/CTA are visible; forbidden differs from unavailable; both locales resolve every new key.

- [ ] **Step 2: Prove the tests are red**

~~~bash
cd frontend && flutter test test/modules/automation/automation_service_test.dart test/modules/automation/automation_library_controller_test.dart test/modules/automation/automation_configuration_view_test.dart
~~~

Expected: FAIL because Automation module is absent.

- [ ] **Step 3: Implement a truthful Library**

Use `WorkspaceCapabilityManifestService` as sole routing authority and add `WorkspaceModule.automation`. Do not resurrect planned/legacy workflow routes or `/workflows/*` client paths. Form values match Company schema; publish/suspend errors come from server authorization, not UI inference.

- [ ] **Step 4: Verify and commit**

~~~bash
cd frontend && flutter test test/modules/automation/automation_service_test.dart test/modules/automation/automation_library_controller_test.dart test/modules/automation/automation_configuration_view_test.dart
cd .. && make frontend-api-contract-check frontend-analyze
git diff --check
git add frontend/lib/modules/automation frontend/lib/core/routing/module_routes.dart \
  frontend/lib/core/services/workspace_capability_manifest_service.dart frontend/assets/lang/vi-VN.json frontend/assets/lang/en-US.json \
  frontend/test/modules/automation
git commit -m "feat(frontend): add governed automation library"
~~~

Expected: PASS before commit.

### Task 8: Build Run Inspector and Needs You from persisted facts

**Files:**

- Modify: `services/company/operations/services/workspace-runtime.service.ts`
- Modify: `services/company/operations/handlers/workspace-runtime.handler.ts`
- Create: `services/company/operations/services/automation-inspector.service.ts`
- Create: `services/company/operations/handlers/automation-inspector.handler.ts`
- Create: `frontend/lib/modules/automation/controllers/automation_run_inspector_controller.dart`
- Create: `frontend/lib/modules/automation/views/automation_run_inspector_view.dart`
- Modify: `frontend/lib/modules/workspace_runtime/views/work_inspector_view.dart`
- Create: `frontend/test/modules/automation/automation_run_inspector_view_test.dart`
- Create: `services/company/operations/tests/automation-inspector.service.test.ts`

**Interfaces:**

- `getAutomationRunInspector(ctx, invocationId)` returns identity, pinned revision/hash, lifecycle, timing/attempts, checkpoint, capability timeline, approvals, evidence refs, failure/retry reason and source health. It does not return raw content/tokens or foreign event.
- Needs You projects `APPROVAL_REQUIRED`, `NEEDS_INPUT`, `BLOCKED`, `LOCAL_RUNTIME_UNAVAILABLE` with stable Automation deep link.
- Inspector is read-only except separately authorized cancellation/approval endpoints.

- [ ] **Step 1: Write failing projection and widget tests**

Seed completed, pending approval, local-offline, retry-failed and foreign workspace runs. Assert five distinct results and redaction. Assert forged runtime signal without matching invocation/run is not a timeline item.

Widget tests render pinned revision/timeline/evidence, approval only while pending, cancellation only while cancellable, and explicit offline vs failure. Tests never fabricate optimistic completion.

- [ ] **Step 2: Prove the tests are red**

~~~bash
cd services/company && npx vitest run operations/tests/automation-inspector.service.test.ts
cd ../../frontend && flutter test test/modules/automation/automation_run_inspector_view_test.dart
~~~

Expected: FAIL because projection/view are absent.

- [ ] **Step 3: Implement projection and inspector**

Build tenant-scoped Company projection from invocations, accepted Agent events and existing `runtimeSourceSignals`. Explicit state mapper handles all declared UI states; unknown/new source state becomes unavailable, never completed. Keep generic Work Inspector for existing sources but remove any claim that a legacy workflow is live Automation.

- [ ] **Step 4: Verify and commit**

~~~bash
cd services/company && npx vitest run operations/tests/automation-inspector.service.test.ts
cd ../../frontend && flutter test test/modules/automation/automation_run_inspector_view_test.dart
cd .. && make frontend-api-contract-check frontend-analyze
git diff --check
git add services/company/operations/services/workspace-runtime.service.ts services/company/operations/handlers/workspace-runtime.handler.ts \
  services/company/operations/services/automation-inspector.service.ts services/company/operations/handlers/automation-inspector.handler.ts \
  services/company/operations/tests/automation-inspector.service.test.ts frontend/lib/modules/automation \
  frontend/lib/modules/workspace_runtime/views/work_inspector_view.dart frontend/test/modules/automation/automation_run_inspector_view_test.dart
git commit -m "feat(automation): expose truthful run inspection"
~~~

Expected: PASS before commit.

### Task 9: Register only safe blueprints and release them behind workspace policy

**Files:**

- Create: `services/company/operations/services/automation-blueprint.service.ts`
- Create: `services/company/operations/tests/automation-blueprint.service.test.ts`
- Modify: `services/cosa/services/surface-policy.ts`
- Create: `services/cosa/tests/automation-surface-policy.test.ts`
- Modify: `.env.example`
- Create: `docs/architecture/automation-mvp.md`

**Interfaces:**

- Initial registry is exactly `operating.weekly-review`, `operations.task-follow-up`, `commercial.outbound-draft`, `strategy.initiative-health` with version, typed schema, triggers, capabilities, evidence, autonomy and runtime requirement.
- Workspace policy can enable only a listed blueprint; it cannot alter its mapping/capabilities/approval/evidence or turn outbound draft into delivery.
- Default rollout is disabled, report/draft-only. Historical inspector remains readable by authorized users.

- [ ] **Step 1: Write failing registry and policy tests**

Assert exact keys; reject arbitrary key and overrides to capability, endpoint URL, execution mode, approval or runtime requirement. Assert commercial declares no delivery capability. Assert disabled policy hides Library CTA while preserving historical inspector access.

- [ ] **Step 2: Prove the tests are red**

~~~bash
cd services/company && npx vitest run operations/tests/automation-blueprint.service.test.ts
cd ../../services/cosa && npx vitest run tests/automation-surface-policy.test.ts
~~~

Expected: FAIL because registry/policy integration is absent.

- [ ] **Step 3: Implement registry and operators' safety guide**

Expose registry metadata read-only to definition configuration. Surface-policy consumes only Company-approved blueprint reference/published state. Environment variables are rollout flags/endpoint config only; document names/safe values, never credentials.

Document rollout: enable one internal workspace, validate report-only run/inspector/approval/cancel/recovery, then expand one blueprint/workspace at a time. Stop/rollback means suspend definition and disable workspace policy; never delete history/migrations.

- [ ] **Step 4: Verify and commit**

~~~bash
cd services/company && npx vitest run operations/tests/automation-blueprint.service.test.ts
cd ../../services/cosa && npx vitest run tests/automation-surface-policy.test.ts
cd ../.. && make mvp-surface-check frontend-boundary-check
git diff --check
git add services/company/operations/services/automation-blueprint.service.ts services/company/operations/tests/automation-blueprint.service.test.ts \
  services/cosa/services/surface-policy.ts services/cosa/tests/automation-surface-policy.test.ts .env.example docs/architecture/automation-mvp.md
git commit -m "feat(automation): gate curated blueprint rollout"
~~~

Expected: PASS before commit.

### Task 10: Prove cross-plane behavior on disposable databases and publish release evidence

**Files:**

- Create: `tests/e2e/test_automation_mvp_cross_plane.py`
- Create: `tests/e2e/test_automation_mvp_tenant_isolation.py`
- Create: `tests/e2e/test_automation_mvp_recovery.py`
- Modify: `Makefile`
- Modify: `docs/architecture/automation-mvp.md`
- Modify: `docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md`

**Interfaces:**

- `make automation-mvp-e2e` provisions only established disposable test databases/processes, applies migrations and runs the three E2E suites. It never targets development/production URLs.
- E2E is real Company outbox -> signed Agent intake -> Control scheduler/lease -> Agent repository/Gateway boundary -> signed Company outcome projection. In-memory repository substitutes are forbidden.

- [ ] **Step 1: Write failing E2E acceptance suites**

Cross-plane: configure/publish weekly review, invoke twice with same identity, observe one invocation/run and pinned manifest, then inspector completion/evidence.

Tenant: workspace B cannot read/configure/invoke/cancel/approve/project A; include unauthorized publish/suspend/approval.

Recovery: stop/restart worker after claim, expire/reclaim lease, submit stale completion, race cancellation/completion, verify terminal/effect/projection. Repeat exact approval race. Include commercial draft and prove no delivery call.

- [ ] **Step 2: Prove the tests are red**

~~~bash
make automation-mvp-e2e
~~~

Expected: FAIL until prior tasks and safe process wiring are integrated.

- [ ] **Step 3: Add guarded orchestration and release evidence**

Make target uses existing test-only bootstrap/reset guards and fails on missing test URLs; it adds no broad deletion. Record command results, migration revisions, redacted endpoint outputs and state assertions in the architecture guide.

Change design status only after this task passes. Release checklist includes contract generation, migrations, tenant negatives, idempotency, lease/reclaim, cancellation race, exact approval, Flutter state coverage, API/boundary gates and real E2E. Do not claim deployment validation without separate approved environment evidence.

- [ ] **Step 4: Verify, review and commit**

~~~bash
make mvp-contracts-check mvp-surface-check frontend-api-contract-check company-boundary-check frontend-boundary-check lease-integration-test
make automation-mvp-e2e
git diff --check
git status --short
~~~

Expected: PASS; status contains only intended changes before staging. Review every Global Constraint, then:

~~~bash
git add tests/e2e/test_automation_mvp_cross_plane.py tests/e2e/test_automation_mvp_tenant_isolation.py \
  tests/e2e/test_automation_mvp_recovery.py Makefile docs/architecture/automation-mvp.md \
  docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md
git commit -m "test(automation): prove governed cross-plane mvp"
~~~

## Release acceptance matrix

| Concern | Required proof |
| --- | --- |
| Tenant boundary | Foreign workspace cannot read, configure, invoke, cancel, approve or project another workspace's Automation. |
| Provenance | Published revision/hash and manifest stay unchanged after later configuration. |
| Exactly-once | Duplicate manual/schedule/event identity yields one Company invocation, Control dispatch and Agent effect claim. |
| Recovery | Reclaimed lease/task fencing rejects stale completion; only registered idempotent effects retry. |
| Governance | Approval is exact and server-authorized; one concurrent decision wins; cancellation cannot regress. |
| UI truth | Library/Inspector distinguish forbidden, unavailable, local offline, pending approval, empty, failure and success. |
| Scope boundary | No custom workflow authoring/raw secret payload/commercial delivery/finance/legal mutation. |
| Production claim | No production-ready claim without separately recorded deployment/environment evidence. |
