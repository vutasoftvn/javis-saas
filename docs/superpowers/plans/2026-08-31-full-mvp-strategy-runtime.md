# Full MVP Strategy and Workspace Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all visible Strategy and Workspace Runtime ghost/fallback calls with Company-owned canvas, execution and source-proven runtime contracts.

**Architecture:** Existing Operations tables remain the source for projects, tasks, dependencies, OKRs, commitments, evidence and lifecycle. This plan adds durable canvases/revisions, completes missing list/read handlers, and builds Workspace Runtime as a read model: direct Company queries plus immutable Agent signal projection and an actor-only snooze overlay. No dashboard row owns or mutates a duplicate task/agent record; action commands call the original owner route.

**Tech Stack:** TypeScript/Encore, Drizzle/PostgreSQL, shared generated MVP contract metadata, Flutter/Dart/GetX, Vitest and Flutter test.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- Complete `2026-08-31-full-mvp-foundation.md` before enabling any capability here.
- Company is the sole writable owner of canvas, revision, task/dependency, OKR and runtime-snooze data. Agent signal rows are immutable projections keyed to a persisted upstream event.
- An AI foundation proposal is a labelled, unaccepted draft based on supplied source references; it is never substituted for a canvas revision or represented as factual workspace data.
- Do not use implicit workspace/project/cycle IDs, default generated themes, arbitrary score `0`, or a failure-to-empty conversion.
- Every handler receives `Authorization` and `X-Workspace-Id`, calls `requireWorkspaceAccess`, and checks referenced IDs in the resolved workspace before read/write.
- New Company migration number is `33`; no existing migration is edited.

---

## File map

| File | Responsibility |
|---|---|
| `services/company/operations/migrations/33_mvp_strategy_canvas_runtime.up.sql` | Canvas/revision tables, immutable runtime-signal projection, actor snoozes, composite indexes/uniqueness |
| `services/company/operations/migrations/33_mvp_strategy_canvas_runtime.down.sql` | Safe rollback of only the new tables/indexes |
| `services/company/shared/db/schema/strategy.ts` | Drizzle canvas/revision definitions |
| `services/company/shared/db/schema/operations.ts` | Runtime signal and snooze definitions |
| `services/company/operations/services/canvas.service.ts` | Workspace-scoped canvas/revision/draft transitions |
| `services/company/operations/services/workspace-runtime.service.ts` | Needs You, blockers, inspector and source-status read model |
| `services/company/operations/services/okr.service.ts` | Authenticated list/read/delete/progress behavior without fake progress defaults |
| `services/company/operations/services/twelve-week-year.service.ts` | Explicit cycle/weekly-plan/commitment validation with no synthetic defaults |
| `services/company/operations/handlers/canvas.handler.ts` | `/operations/strategy/canvases/*` and revision API |
| `services/company/operations/handlers/workspace-runtime.handler.ts` | `/operations/workspace-runtime/*` API |
| `services/company/operations/handlers/okr.handler.ts` | Missing OKR list/delete/progress contract handlers |
| `services/company/operations/handlers/index.ts` | Canonical handler exports |
| `services/company/events/handlers/agent-runtime-signal.handler.ts` | Service-authenticated immutable Agent signal ingest |
| `services/company/events/handlers/index.ts` | Event-handler export |
| `services/company/operations/tests/mvp-canvas-runtime.test.ts` | Real database repository/authorization/projection tests |
| `services/company/operations/tests/mvp-okr-twelve-week.test.ts` | Missing list/auth/no-default-value regression tests |
| `frontend/lib/modules/strategy/services/strategy_mvp_client.dart` | Typed Strategy API client using `MvpRequestClient` |
| `frontend/lib/modules/strategy/models/mvp_strategy_models.dart` | Canvas/revision/OKR/plan DTOs with source metadata |
| `frontend/lib/modules/workspace_runtime/services/workspace_runtime_mvp_client.dart` | Typed runtime client |
| `frontend/lib/modules/workspace_runtime/models/mvp_runtime_models.dart` | Runtime item, source reference, source status and inspector DTOs |
| `frontend/lib/modules/strategy/controllers/*.dart` | Consume explicit `ApiResult` states rather than fallback values |
| `frontend/lib/modules/workspace_runtime/controllers/workspace_runtime_controller.dart` | Separate load state from genuine empty collections |
| `frontend/lib/modules/strategy/views/*.dart` | Render draft/evidence/empty/error states truthfully |
| `frontend/lib/modules/workspace_runtime/views/*.dart` | Render unavailable source and source-linked actions |
| `frontend/test/strategy_mvp_service_test.dart` | Client/model result tests |
| `frontend/test/workspace_runtime_service_test.dart` | Runtime result/error mapping tests |
| `frontend/test/workspace_runtime_views_test.dart` | Empty/unavailable/source-link widget tests |

## Task 1: Add canvas/revision and runtime projection persistence

**Files:**

- Create: `services/company/operations/migrations/33_mvp_strategy_canvas_runtime.up.sql`
- Create: `services/company/operations/migrations/33_mvp_strategy_canvas_runtime.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Modify: `services/company/shared/db/schema/operations.ts`
- Test: `services/company/operations/tests/mvp-canvas-runtime.test.ts`

**Interfaces:**

- Produces `strategy.canvases`, `strategy.canvas_revisions`, `operating.runtime_source_signals`, and `operating.runtime_snoozes`.
- Produces `Canvas`, `CanvasRevision`, `RuntimeSourceSignal`, and `RuntimeSnooze` Drizzle exports.
- Later tasks consume IDs as string JSON values and constrain all source reads by `workspace_id`.

- [ ] **Step 1: Write migration/schema tests before SQL.**

  ```ts
  it("does not let a canvas revision from workspace B attach to canvas A", async () => {
    await expect(insertRevision({ workspaceId: workspaceB, canvasId: canvasA.id })).rejects.toMatchObject({ code: "23503" });
  });

  it("deduplicates the same persisted agent signal sequence", async () => {
    await insertRuntimeSignal({ workspaceId, sourceKind: "agent_run", sourceId: "run_1", sequence: 7 });
    await expect(insertRuntimeSignal({ workspaceId, sourceKind: "agent_run", sourceId: "run_1", sequence: 7 })).rejects.toMatchObject({ code: "23505" });
  });
  ```

- [ ] **Step 2: Run the test and verify it fails because migration 33 is absent.**

  Run: `cd services/company && npx vitest run operations/tests/mvp-canvas-runtime.test.ts`

  Expected: FAIL with missing table/schema export.

- [ ] **Step 3: Add only the required durable tables and constraints.**

  Implement these columns and constraints in migration 33:

  ```sql
  CREATE TABLE strategy.canvases (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT NULL,
    current_revision_id BIGINT NULL,
    created_by_member_id BIGINT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL,
    UNIQUE (id, workspace_id)
  );
  CREATE TABLE strategy.canvas_revisions (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    canvas_id BIGINT NOT NULL,
    parent_revision_id BIGINT NULL,
    content JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('DRAFT','IN_REVIEW','APPROVED','REJECTED')),
    origin TEXT NOT NULL CHECK (origin IN ('USER','MODEL_DRAFT')),
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by_member_id BIGINT NULL,
    reviewed_by_member_id BIGINT NULL,
    review_note TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ NULL,
    UNIQUE (id, workspace_id),
    FOREIGN KEY (canvas_id, workspace_id) REFERENCES strategy.canvases(id, workspace_id)
  );
  ```

  `runtime_source_signals` includes immutable `workspace_id`, `source_kind`, `source_id`, `sequence`, `state`, `observed_at`, `correlation_id`, `payload_hash`, `received_at` and `UNIQUE(workspace_id, source_kind, source_id, sequence)`. `runtime_snoozes` includes `workspace_id`, `actor_member_id`, `source_kind`, `source_id`, `snoozed_until`, `created_at`, `updated_at` and one active unique key per actor/source. Add indexes beginning with `workspace_id` for each runtime list query.

- [ ] **Step 4: Implement a reversible down migration and run migration rehearsal.**

  The down migration removes foreign keys/indexes/new tables only. It must not delete or modify existing Operations/Strategy data.

  Run:

  ```bash
  cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL" node scripts/migrate.mjs
  cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL" node scripts/migrate.mjs --down 1
  cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL" node scripts/migrate.mjs
  ```

  Expected: apply, one-step rollback and reapply all succeed on an isolated disposable database.

- [ ] **Step 5: Re-run the focused database test.**

  Run: `cd services/company && npx vitest run operations/tests/mvp-canvas-runtime.test.ts`

  Expected: PASS for same-workspace writes, cross-workspace rejection and signal deduplication.

- [ ] **Step 6: Commit the durable foundation.**

  ```bash
  git add services/company/operations/migrations/33_mvp_strategy_canvas_runtime.* \
    services/company/shared/db/schema/strategy.ts services/company/shared/db/schema/operations.ts \
    services/company/operations/tests/mvp-canvas-runtime.test.ts
  git commit -m "feat: persist strategy canvases and runtime signals"
  ```

## Task 2: Implement canonical Company APIs for Strategy and Runtime

**Files:**

- Create: `services/company/operations/services/canvas.service.ts`
- Create: `services/company/operations/services/workspace-runtime.service.ts`
- Create: `services/company/operations/handlers/canvas.handler.ts`
- Create: `services/company/operations/handlers/workspace-runtime.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/operations/services/index.ts`
- Modify: `services/company/operations/handlers/okr.handler.ts`
- Modify: `services/company/operations/services/okr.service.ts`
- Modify: `services/company/operations/handlers/twelve-week-year.handler.ts`
- Modify: `services/company/operations/services/twelve-week-year.service.ts`
- Test: `services/company/operations/tests/mvp-canvas-runtime.test.ts`
- Test: `services/company/operations/tests/mvp-okr-twelve-week.test.ts`

**Interfaces:**

- Produces manifest routes `strategy.canvas.*`, `strategy.okr.*`, `strategy.twelve_week.*`, and `workspace_runtime.*` using `MvpSuccess<T>`.
- Produces `getNeedsYou(ctx)`, `getBlockers(ctx)`, `getWorkInspector(ctx, ref)`, `snoozeRuntimeItem(ctx, ref, until)` and source-owner command handlers.
- Later Flutter clients consume typed `data/meta`; no route returns a hand-built empty map on error.

- [ ] **Step 1: Write authorization and no-fabrication API tests.**

  ```ts
  it("returns empty canvases only after an authorized query", async () => {
    const res = await listCanvases({ workspaceId: workspaceA, authorization: tokenA });
    expect(res.meta.dataState).toBe("empty");
    expect(res.meta.sources[0]).toMatchObject({ kind: "company_db", ref: "strategy.canvases" });
  });

  it("does not accept a model draft without source refs", async () => {
    await expect(createRevision(ctx, { canvasId, origin: "MODEL_DRAFT", content: {}, sourceRefs: [] }))
      .rejects.toThrow(/source reference/);
  });

  it("returns forbidden rather than an empty blocker list for another workspace", async () => {
    await expect(listBlockers({ workspaceId: workspaceB, authorization: tokenA })).rejects.toMatchObject({ code: "permission_denied" });
  });
  ```

- [ ] **Step 2: Run the focused tests and confirm they fail before route implementation.**

  Run: `cd services/company && npx vitest run operations/tests/mvp-canvas-runtime.test.ts operations/tests/mvp-okr-twelve-week.test.ts`

  Expected: FAIL for missing service/handler exports and missing canonical list routes.

- [ ] **Step 3: Implement the canonical route set and service behavior.**

  Expose the following methods/routes and use the Foundation envelope helpers:

  ```text
  GET|POST                 /operations/strategy/canvases
  GET|PUT|DELETE           /operations/strategy/canvases/:id
  POST                     /operations/strategy/canvases/:id/revisions
  GET                      /operations/strategy/canvas-revisions/:id
  POST                     /operations/strategy/canvas-revisions/:id/submit-review
  POST                     /operations/strategy/canvas-revisions/:id/approve
  POST                     /operations/strategy/canvas-revisions/:id/reject
  GET                      /operations/okr-cycles
  GET                      /operations/objectives
  DELETE                   /operations/objectives/:id
  GET                      /operations/objectives/:id/progress
  GET                      /operations/workspace-runtime/needs-you
  GET                      /operations/workspace-runtime/blockers
  GET                      /operations/workspace-runtime/items/:sourceKind/:sourceId
  POST                     /operations/workspace-runtime/items/:sourceKind/:sourceId/snooze
  GET                      /operations/workspace-runtime/source-status
  ```

  In the same handler/client cutover, declare and migrate every already-owned visible Strategy bundle rather than leaving a raw legacy call behind: venture profile/lenses; assumptions/interviews/discovery signals/experiments/evidence; initiatives/portfolios/projects; project-stage/gate/pilot/PMF/next-action/decision records; and the existing 12-week cycle/plan/commitment/review routes. Add a missing canonical list/read handler wherever the Flutter view currently invokes a ghost route. Funding catalog/match/watchlist has no invented seed: its handler reads an authorized funding-provider observation with source/freshness metadata, or returns typed `not_connected` when no provider grant exists.

  Canvas revision transitions are `DRAFT -> IN_REVIEW -> APPROVED|REJECTED`; create a fresh revision to amend an approved/rejected one. `MODEL_DRAFT` requires non-empty source refs and stays `DRAFT`; it cannot update `canvases.current_revision_id` until a human approves it. Existing project/assumption/evidence endpoints remain their owners; do not copy them into canvas JSON as a source of truth.

  `getNeedsYou` reads actor-assigned pending decisions/approvals from Company sources and Agent signal projections. `getBlockers` reads unresolved task dependencies plus projected failed/paused Agent source states. `getWorkInspector` reads a declared `(sourceKind, sourceId)` and returns source links/freshness; it rejects arbitrary raw task IDs from another workspace. Snooze writes only `runtime_snoozes`. Resolve actions dispatch to task dependency/approval/decision owners and return their real result.

- [ ] **Step 4: Correct existing OKR and Twelve-Week false defaults.**

  Add explicit authenticated list handlers; pass authorization into `getObjectiveProgressService`; query objective/key results with workspace predicates. On key-result create, require a supplied baseline/current measurement or persist `currentValue: null` and `status: "NOT_MEASURED"`; do not manufacture `0`. Require `theme`, `visionStatement`, actual `projectId`, `cycleId` and `weeklyPlanId` from the UI instead of the current `'1'`, Vietnamese default theme, or week number substituted for an ID.

- [ ] **Step 5: Run the focused Company suite.**

  Run:

  ```bash
  cd services/company && npx vitest run operations/tests/mvp-canvas-runtime.test.ts operations/tests/mvp-okr-twelve-week.test.ts operations/tests/workspace-scoped-links.test.ts operations/tests/task-dependency.test.ts
  ```

  Expected: PASS, including cross-tenant negative cases and no `MODEL_DRAFT` promotion without source references.

- [ ] **Step 6: Commit the canonical Company API.**

  ```bash
  git add services/company/operations/services services/company/operations/handlers \
    services/company/operations/tests/mvp-canvas-runtime.test.ts services/company/operations/tests/mvp-okr-twelve-week.test.ts
  git commit -m "feat: add canonical strategy and runtime contracts"
  ```

## Task 3: Ingest immutable Agent runtime signals

**Files:**

- Create: `services/company/events/handlers/agent-runtime-signal.handler.ts`
- Modify: `services/company/events/handlers/index.ts`
- Modify: `services/company/events/api.ts`
- Modify: `services/company/operations/services/workspace-runtime.service.ts`
- Test: `services/company/events/tests/agent-runtime-signal.test.ts`
- Test: `services/company/operations/tests/mvp-canvas-runtime.test.ts`

**Interfaces:**

- Consumes a signed `agent.runtime-signal.v1` with `{workspaceId, sourceKind, sourceId, sequence, state, observedAt, correlationId, payloadHash}`.
- Produces idempotent `runtime_source_signals` projection rows and source-status metadata; Workforce plan is the only producer.

- [ ] **Step 1: Write failing idempotency/authentication tests.**

  ```ts
  it("rejects an unsigned agent signal before storing it", async () => {
    await expect(ingestAgentRuntimeSignal({ authorization: undefined, ...signal })).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("does not duplicate a retry with the same source sequence", async () => {
    await ingestAgentRuntimeSignal({ authorization: serviceToken, ...signal });
    await ingestAgentRuntimeSignal({ authorization: serviceToken, ...signal });
    expect(await countSignals(signal.workspaceId, signal.sourceId)).toBe(1);
  });
  ```

- [ ] **Step 2: Run and verify failure.**

  Run: `cd services/company && npx vitest run events/tests/agent-runtime-signal.test.ts`

  Expected: FAIL because the internal handler/export is absent.

- [ ] **Step 3: Implement a service-authenticated, projection-only endpoint.**

  Require the existing COSA service identity/worker authentication mechanism; validate every field and reject a missing/invalid workspace ID. Insert with `ON CONFLICT DO NOTHING` against the sequence uniqueness key. The handler has no human-session route, no create/update/delete projection API and no client-supplied title/metric field. The runtime service reports the newest received signal and its `observed_at`; it reports Agent source `unavailable` when the signed producer cannot be reached or no confirmed signal has ever arrived.

- [ ] **Step 4: Run Company event and runtime tests.**

  Run: `cd services/company && npx vitest run events/tests/agent-runtime-signal.test.ts operations/tests/mvp-canvas-runtime.test.ts`

  Expected: PASS for signature rejection, retry deduplication, workspace isolation and source status.

- [ ] **Step 5: Commit the signal consumer.**

  ```bash
  git add services/company/events services/company/operations/services/workspace-runtime.service.ts \
    services/company/events/tests/agent-runtime-signal.test.ts services/company/operations/tests/mvp-canvas-runtime.test.ts
  git commit -m "feat: project agent runtime signals into workspace runtime"
  ```

## Task 4: Migrate Strategy and Runtime Flutter clients and views

**Files:**

- Create: `frontend/lib/modules/strategy/services/strategy_mvp_client.dart`
- Create: `frontend/lib/modules/strategy/models/mvp_strategy_models.dart`
- Create: `frontend/lib/modules/workspace_runtime/services/workspace_runtime_mvp_client.dart`
- Create: `frontend/lib/modules/workspace_runtime/models/mvp_runtime_models.dart`
- Modify: `frontend/lib/modules/strategy/services/canvas_service.dart`
- Modify: `frontend/lib/modules/strategy/services/okr_service.dart`
- Modify: `frontend/lib/modules/strategy/services/twelve_wy_service.dart`
- Modify: `frontend/lib/modules/strategy/controllers/foundation_controller.dart`
- Modify: `frontend/lib/modules/strategy/controllers/strategy_controller.dart`
- Modify: `frontend/lib/modules/strategy/controllers/mixins/okr_state_mixin.dart`
- Modify: `frontend/lib/modules/strategy/controllers/mixins/twelve_wy_state_mixin.dart`
- Modify: `frontend/lib/modules/workspace_runtime/services/workspace_runtime_service.dart`
- Modify: `frontend/lib/modules/workspace_runtime/controllers/workspace_runtime_controller.dart`
- Modify: `frontend/lib/modules/workspace_runtime/views/needs_you_view.dart`
- Modify: `frontend/lib/modules/workspace_runtime/views/blocked_work_view.dart`
- Modify: `frontend/lib/modules/workspace_runtime/views/work_inspector_view.dart`
- Test: `frontend/test/strategy_mvp_service_test.dart`
- Test: `frontend/test/workspace_runtime_service_test.dart`
- Test: `frontend/test/workspace_runtime_views_test.dart`

**Interfaces:**

- Consumes `MvpEndpoint`, `MvpRequestClient` and Company `MvpSuccess` envelopes from Foundation.
- Produces typed `ApiResult` fields/controllers; `List<T>` is rendered only from `ApiSuccess`.

- [ ] **Step 1: Write client tests for empty versus unavailable.**

  ```dart
  test('canvas 503 is unavailable, not an empty canvas collection', () async {
    final result = await service.listCanvases();
    expect(result, isA<ApiFailure<List<StrategyCanvas>>>());
    expect((result as ApiFailure<List<StrategyCanvas>>).failure.code, ApiFailureCode.unavailable);
  });

  test('empty runtime response keeps source status and renders an empty state', () async {
    final result = await runtime.listNeedsYou();
    expect((result as ApiSuccess<List<RuntimeItem>>).meta.dataState, ApiDataState.empty);
  });
  ```

- [ ] **Step 2: Run the focused Flutter tests and verify failure before migration.**

  Run: `cd frontend && flutter test test/strategy_mvp_service_test.dart test/workspace_runtime_service_test.dart test/workspace_runtime_views_test.dart`

  Expected: FAIL because typed MVP clients/models do not exist and current services collapse errors.

- [ ] **Step 3: Implement typed DTO/client mapping.**

  `StrategyMvpClient` uses generated IDs such as `MvpEndpoint.strategyCanvasList`; `WorkspaceRuntimeMvpClient` uses `MvpEndpoint.workspaceRuntimeNeedsYou`. Decode IDs as strings and require all IDs from form fields. Replace each confirmed legacy path in `canvas_service.dart`, `okr_service.dart`, `twelve_wy_service.dart`, and `workspace_runtime_service.dart` with delegation to the typed client. Remove `/strategy/*`, `/company-runtime/*`, `/agents/execution/*`, `?? '1'`, `?? 0`, `return []` on catch, and status-404-to-empty behavior from these enabled clients.

- [ ] **Step 4: Make controllers/views truth-preserving.**

  Introduce a controller field per data group with `ApiResult<T>?`, not just `loading` plus list. Render:

  ```text
  loading       -> progress indicator, no cards
  populated     -> typed records and source metadata
  empty         -> create/import call-to-action with no sample records
  forbidden     -> access explanation, no retry that changes identity
  unavailable   -> last confirmed timestamp (if supplied) plus retry
  not_connected -> connector/setup action only where the source is external
  ```

  The canvas AI action must display a labelled `MODEL_DRAFT`, source refs and required approval; it cannot prefill a current strategy revision as truth.

- [ ] **Step 5: Run focused Flutter verification.**

  Run:

  ```bash
  cd frontend && flutter test test/strategy_mvp_service_test.dart test/workspace_runtime_service_test.dart test/workspace_runtime_views_test.dart
  cd frontend && flutter analyze
  ```

  Expected: PASS. Empty collections appear only when `meta.dataState == empty`; fake cards/default IDs are absent.

- [ ] **Step 6: Enable and commit the migrated manifest entries.**

  Set only the implemented Strategy/Runtime capabilities to `enabled: true`, regenerate contracts/inventory, then commit:

  ```bash
  node scripts/gen-mvp-contracts.mjs
  make route-inventory
  git add frontend/lib/modules/strategy frontend/lib/modules/workspace_runtime frontend/test \
    shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart docs/architecture/generated
  git commit -m "feat: wire truthful strategy and workspace runtime ui"
  ```

## Task 5: Prove Strategy/Runtime integration and remove its legacy allowlist entries

**Files:**

- Create: `tests/e2e/test_mvp_strategy_runtime_http.py`
- Modify: `tests/e2e/conftest.py`
- Modify: `docs/architecture/generated/route-inventory.allowlist.json`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Consumes an actual migrated Company database/service and authenticated workspace fixtures.
- Produces the `strategy.*` and `workspace_runtime.*` `VERIFIED` ledger evidence.

- [ ] **Step 1: Write the real-service scenario with no transport replacement.**

  ```python
  def test_canvas_dependency_and_runtime_are_workspace_scoped(real_company_service, authenticated_workspace_a, authenticated_workspace_b):
      canvas = post_json(real_company_service, authenticated_workspace_a, "/operations/strategy/canvases", {"name": "Validated problem"})
      revision = post_json(real_company_service, authenticated_workspace_a, f"/operations/strategy/canvases/{canvas['data']['id']}/revisions", {"content": {"problem": "user supplied"}, "origin": "USER", "sourceRefs": []})
      assert get_json(real_company_service, authenticated_workspace_a, "/operations/workspace-runtime/blockers")["meta"]["dataState"] in {"populated", "empty"}
      assert get_json(real_company_service, authenticated_workspace_b, f"/operations/strategy/canvases/{canvas['data']['id']}").status_code in {403, 404}
  ```

- [ ] **Step 2: Run it with the existing real Company fixture.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_strategy_runtime_http.py -q`

  Expected: a clear SKIP if Encore/Postgres/auth prerequisites are absent; never a fallback to `MockTransport` or a fake HTTP server.

- [ ] **Step 3: Make the scenario use real authenticated fixtures.**

  Extend `tests/e2e/conftest.py` to provision two real workspaces/members through the product's test environment, capture their actual bearer tokens and headers, and clean their records with the test database lifecycle. Do not add a production-accessible seed endpoint. The test must assert populated, genuine empty, forbidden and unavailable-source outcomes plus idempotent Agent signal retry.

- [ ] **Step 4: Run the E2E test and contract gates.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_strategy_runtime_http.py -q
  make mvp-surface-check
  make contract-freeze-check
  ```

  Expected: PASS, or explicit environmental SKIP for the real-service test only. A skipped run does not permit `VERIFIED` ledger status.

- [ ] **Step 5: Remove only matching legacy entries and commit evidence.**

  Remove the Strategy/Runtime entries from `route-inventory.allowlist.json` only after the raw Flutter calls are gone and generated inventory shows canonical handlers. Update ledger command/SHA/result, then:

  ```bash
  git add tests/e2e docs/architecture/generated/route-inventory.allowlist.json docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "test: verify strategy runtime mvp flow"
  ```

## Completion gate

Run:

```bash
cd services/company && npx vitest run operations/tests/mvp-canvas-runtime.test.ts operations/tests/mvp-okr-twelve-week.test.ts events/tests/agent-runtime-signal.test.ts
cd frontend && flutter test test/strategy_mvp_service_test.dart test/workspace_runtime_service_test.dart test/workspace_runtime_views_test.dart
make mvp-contracts-check
make mvp-surface-check
make contract-freeze-check
git diff --check
```

The slice is not complete while a Strategy/Runtime UI route reads legacy `/strategy`, `/company-runtime` or `/agents/execution` calls, treats 404/503 as empty, requires a fake default ID, or lacks its real-service integration evidence.
