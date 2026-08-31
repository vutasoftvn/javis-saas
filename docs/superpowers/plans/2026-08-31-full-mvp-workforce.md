# Full MVP Workforce Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Workforce show and manage only actual Agent Platform assignments, specifications, runs, approvals, schedules and observations, while feeding immutable real signals into Workspace Runtime.

**Architecture:** `packages/agent/workforce` remains a pure catalog/composition policy layer. A new Agent database assignment repository records when a workspace actually configures a functional AgentSpec; it does not create an automatic default fleet. FastAPI exposes a typed `/agent/workforce/*` read/write surface using authenticated workspace identity. Run/approval status comes from the existing durable repositories; a transactional outbox publishes only persisted Agent transitions to the Company Runtime projection.

**Tech Stack:** Python/FastAPI/Pydantic, SQLAlchemy/asyncpg/PostgreSQL, existing Agent spec/run/approval registries, Flutter/Dart/GetX, pytest and Flutter test.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- Complete the Foundation plan before enabling a Workforce capability; consume generated `MvpEndpoint` metadata and `ApiResult` only.
- The functional catalog is versioned system reference data, not evidence that a workspace has an assigned/running agent. A roster lists persisted assignments only.
- Title/persona does not grant capability. Every assignment pins `spec_id`, `spec_version` and `definition_hash`; a capability change requires a new published spec/assignment record and the existing approval policy.
- Agent Platform uses `get_authenticated_identity` and `require_workspace_operator` for changes. It never trusts a browser workspace/principal/role payload.
- Health derives from a real run/heartbeat observation. No observation is `not_observed`, not `healthy`.
- Runtime signals originate only after a durable run/approval transition and are delivered through an outbox. A failed delivery remains pending/visible; it cannot fabricate a delivered signal.
- Migration number `022_workforce_assignments_and_runtime_outbox` is reserved for this plan; do not edit earlier Agent migrations.

---

## File map

| File | Responsibility |
|---|---|
| `packages/agent/migrations/022_workforce_assignments_and_runtime_outbox.sql` | Assignment and runtime-signal outbox tables/indexes/constraints |
| `packages/agent/migrations/022_workforce_assignments_and_runtime_outbox.down.sql` | Safe rollback of new Agent tables only |
| `packages/agent/workforce/repository.py` | Workspace-scoped assignment/outbox persistence |
| `packages/agent/workforce/models.py` | Assignment, roster, health and signal typed records |
| `packages/agent/workforce/catalog.py` | Reused system-owned functional specs; no automatic assignment path |
| `apps/cosa/composition/agent_plane.py` | Wires `WorkforceRepository` with real Agent DB session factory |
| `apps/cosa/api/workforce_schemas.py` | Pydantic request/response payloads |
| `apps/cosa/api/workforce_routes.py` | `/agent/workforce/*` API routes |
| `apps/cosa/api/app.py` | Registers workforce router |
| `apps/cosa/events/runtime_signal.py` | Signed Company signal client and durable outbox delivery |
| `apps/cosa/api/routes.py` | Enqueues approval/cancel runtime signals after durable writes |
| `apps/cosa/worker/handlers.py` | Enqueues terminal run runtime signals |
| `apps/cosa/worker/main.py` | Retries pending runtime-signal outbox items |
| `tests/agent/workforce/test_repository.py` | Real Agent Postgres assignment/outbox tests |
| `tests/apps/cosa/test_workforce_routes.py` | FastAPI route/auth/provenance tests |
| `tests/apps/cosa/test_runtime_signal_delivery.py` | Outbox retry/signing/Company delivery tests |
| `frontend/lib/modules/agents/services/workforce_service.dart` | Typed Workforce client |
| `frontend/lib/modules/agents/models/workforce_models.dart` | Assignment/agent/run/approval/health DTOs |
| `frontend/lib/modules/agents/controllers/agents_controller.dart` | Result-aware Workforce state |
| `frontend/lib/modules/agents/services/agents_service.dart` | Compatibility delegate with legacy fallback removed |
| `frontend/lib/modules/agents/services/agent_platform_service.dart` | Compatibility delegate with fake/default roster removed |
| `frontend/lib/modules/agents/views/*.dart` | Honest roster, health, approval and run UI states |
| `frontend/test/workforce_service_test.dart` | Typed failure/empty/provenance client tests |
| `frontend/test/workforce_views_test.dart` | Roster/health/approval widget-state tests |

## Task 1: Persist actual workspace workforce assignments and signal outbox

**Files:**

- Create: `packages/agent/migrations/022_workforce_assignments_and_runtime_outbox.sql`
- Create: `packages/agent/migrations/022_workforce_assignments_and_runtime_outbox.down.sql`
- Create: `packages/agent/workforce/models.py`
- Create: `packages/agent/workforce/repository.py`
- Modify: `packages/agent/workforce/__init__.py`
- Test: `tests/agent/workforce/test_repository.py`
- Test: `tests/agent/scripts/test_migrate.py`

**Interfaces:**

- Produces `WorkforceAssignmentRecord`, `WorkforceRepository.create_assignment`, `list_assignments`, `retire_assignment`, `list_cost_observations`, `enqueue_runtime_signal`, `claim_pending_signals`, and `mark_signal_delivered`.
- Subsequent routes and worker code use these methods; they never create a roster entry from catalog data alone.

- [ ] **Step 1: Write database-backed assignment/outbox tests.**

  ```python
  @pytest.mark.integration
  async def test_assignment_is_scoped_and_pins_a_published_spec(agent_db) -> None:
      repo = WorkforceRepository(agent_db)
      assignment = await repo.create_assignment(
          workspace_id="1001", functional_key="campaign_planner",
          spec_id="functional.campaign_planner", spec_version="1.0.0",
          definition_hash="sha256:published", configured_by="user:1",
      )
      assert [row.assignment_id for row in await repo.list_assignments("1001")] == [assignment.assignment_id]
      assert await repo.list_assignments("2002") == []

  @pytest.mark.integration
  async def test_signal_retry_does_not_create_two_outbox_rows(agent_db) -> None:
      repo = WorkforceRepository(agent_db)
      await repo.enqueue_runtime_signal(workspace_id="1001", source_kind="agent_run", source_id="run_7", sequence=3, state="FAILED", observed_at=NOW)
      await repo.enqueue_runtime_signal(workspace_id="1001", source_kind="agent_run", source_id="run_7", sequence=3, state="FAILED", observed_at=NOW)
      assert len(await repo.claim_pending_signals(limit=10)) == 1
  ```

- [ ] **Step 2: Run the focused tests and confirm migration/repository failure.**

  Run: `PYTHONPATH=$(pwd) AGENT_MIGRATION_TEST_DATABASE_URL="$AGENT_MIGRATION_TEST_DATABASE_URL" python3 -m pytest tests/agent/workforce/test_repository.py tests/agent/scripts/test_migrate.py -q`

  Expected: FAIL until migration 022 and repository are present; explicit database-unavailable SKIP is acceptable only for integration-marked cases.

- [ ] **Step 3: Add the two durable tables and typed repository.**

  Create these database invariants:

  ```sql
  CREATE TABLE agent.workforce_assignments (
    assignment_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    functional_key TEXT NOT NULL,
    spec_id TEXT NOT NULL,
    spec_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    reports_to_assignment_id UUID NULL,
    configured_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at TIMESTAMPTZ NULL,
    UNIQUE (workspace_id, functional_key, spec_id, spec_version, definition_hash)
  );
  CREATE TABLE agent.runtime_signal_outbox (
    outbox_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    sequence BIGINT NOT NULL,
    state TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    state_delivery TEXT NOT NULL CHECK (state_delivery IN ('PENDING','DELIVERED','FAILED')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ NULL,
    UNIQUE (workspace_id, source_kind, source_id, sequence)
  );
  CREATE TABLE agent.run_cost_observations (
    observation_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    input_tokens BIGINT NULL CHECK (input_tokens >= 0),
    output_tokens BIGINT NULL CHECK (output_tokens >= 0),
    cost_amount NUMERIC NULL CHECK (cost_amount >= 0),
    currency TEXT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (workspace_id, run_id, provider_key, model_key, observed_at)
  );
  ```

  Add indexes `(workspace_id, status)`, `(workspace_id, reports_to_assignment_id)`, `(state_delivery, next_attempt_at)`, and `(workspace_id, observed_at DESC)`. `create_assignment` must resolve the current published spec from `SpecRegistryRepository` before inserting, and reject a missing/mismatched hash. No method calls `build_functional_spec` to write a row automatically. The run worker writes a cost observation only from an actual provider usage receipt; absent receipt remains unmeasured and no row is created.

- [ ] **Step 4: Implement down migration and migrate/rollback rehearsal.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) AGENT_MIGRATION_DATABASE_URL="$AGENT_MIGRATION_DATABASE_URL" python3 -m packages.agent.scripts.migrate
  PYTHONPATH=$(pwd) AGENT_MIGRATION_DATABASE_URL="$AGENT_MIGRATION_DATABASE_URL" python3 -m packages.agent.scripts.migrate --down 1
  PYTHONPATH=$(pwd) AGENT_MIGRATION_DATABASE_URL="$AGENT_MIGRATION_DATABASE_URL" python3 -m packages.agent.scripts.migrate
  ```

  Expected: all three commands succeed on an isolated database and no unrelated Agent table changes.

- [ ] **Step 5: Run focused tests and commit persistence.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/agent/workforce/test_repository.py -q`

  ```bash
  git add packages/agent/migrations/022_workforce_assignments_and_runtime_outbox.* packages/agent/workforce tests/agent/workforce tests/agent/scripts/test_migrate.py
  git commit -m "feat: persist workspace workforce assignments"
  ```

## Task 2: Expose authenticated Workforce routes from Agent Platform

**Files:**

- Create: `apps/cosa/api/workforce_schemas.py`
- Create: `apps/cosa/api/workforce_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_workforce_routes.py`
- Test: `tests/apps/cosa/test_tenant_isolation.py`

**Interfaces:**

- Produces `GET /agent/workforce/assignments`, `GET /agent/workforce/composition`, `GET /agent/workforce/org-chart`, `POST /agent/workforce/assignments`, `POST /agent/workforce/assignments/:id/retire`, `GET /agent/workforce/runs`, `GET /agent/workforce/runs/:runId`, `GET /agent/workforce/runs/:runId/events`, `GET /agent/workforce/runs/:runId/artifacts`, `GET|POST /agent/workforce/schedules`, `POST /agent/workforce/schedules/:scheduleId/run-now`, `GET /agent/workforce/approvals`, `POST /agent/workforce/approvals/:approvalId/decision`, `GET /agent/workforce/capabilities`, `GET /agent/workforce/cost-observations`, and `GET /agent/workforce/health`.
- All list routes return `MvpSuccess` with Agent `data_state`/source metadata; write routes return the persisted assignment or a typed FastAPI error.

- [ ] **Step 1: Write route/auth tests before routes.**

  ```python
  async def test_empty_assignment_roster_is_honest(client, workspace_identity) -> None:
      response = await client.get("/agent/workforce/assignments", headers=workspace_identity.headers)
      assert response.status_code == 200
      assert response.json()["meta"]["data_state"] == "empty"
      assert response.json()["data"] == []

  async def test_other_workspace_cannot_retire_assignment(client, workspace_a, workspace_b, assignment_a) -> None:
      response = await client.post(f"/agent/workforce/assignments/{assignment_a.assignment_id}/retire", headers=workspace_b.headers)
      assert response.status_code == 404
  ```

- [ ] **Step 2: Run the test and verify it fails before router registration.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_workforce_routes.py -q`

  Expected: FAIL with missing `/agent/workforce/*` routes.

- [ ] **Step 3: Implement schemas/routes with server-derived context.**

  Use `identity: AuthenticatedIdentity = Depends(get_authenticated_identity)` on every route and `require_workspace_operator(identity)` for create/retire. The create request accepts only `functional_key`; the route resolves the current published spec/hash server-side. `composition` may list all catalog entries but each result must include `assigned: false` when no durable assignment exists and eligibility reasons from actual policy/readiness inputs. It must not call this a running agent.

  `runs`, event streams, artifacts, schedules and approvals adapt the existing workspace-scoped repositories/routes; they do not rebuild a second ledger. `org-chart` derives only from persisted assignments plus their declared reporting link, and is a genuine empty tree before an assignment exists. `capabilities` lists pinned spec capability refs and current policy outcome, never grants power from a persona/title. `cost-observations` reads persisted run telemetry/budget records with source/timestamp; no telemetry is `NOT_MEASURED`, not a zero-cost run. `health` returns `{assignment_id, status: "healthy"|"degraded"|"failed"|"not_observed", observed_at, source_ref}` from an actual last observation. Do not invent an observed timestamp. Return `not_observed` when the assignment has no run/heartbeat.

- [ ] **Step 4: Wire a real `WorkforceRepository` into the production plane.**

  Add `workforce_repository` to `CosaAgentPlane`, construct it only with the real Agent database session factory in `build_cosa_agent_plane`, and include it in `_PLANE_CORE_DEPENDENCIES`. Test injection may provide an in-memory repository only inside `tests/**`; production startup must fail if the durable dependency is absent.

- [ ] **Step 5: Run focused API/tenancy tests.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_workforce_routes.py tests/apps/cosa/test_tenant_isolation.py tests/apps/cosa/test_app_lifecycle.py -q
  ```

  Expected: PASS; no default roster and no cross-workspace record disclosure.

- [ ] **Step 6: Commit Workforce API.**

  ```bash
  git add apps/cosa/api/workforce_schemas.py apps/cosa/api/workforce_routes.py apps/cosa/api/app.py apps/cosa/composition/agent_plane.py tests/apps/cosa/test_workforce_routes.py tests/apps/cosa/test_tenant_isolation.py
  git commit -m "feat: add authenticated workforce api"
  ```

## Task 3: Publish persisted Agent transitions to Workspace Runtime

**Files:**

- Create: `apps/cosa/events/runtime_signal.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/config/service_identity.py`
- Test: `tests/apps/cosa/test_runtime_signal_delivery.py`

**Interfaces:**

- Consumes `WorkforceRepository.enqueue_runtime_signal` and sends the exact signed payload required by `agent-runtime-signal.handler.ts` from the Strategy/Runtime plan.
- Produces retryable delivery state only after the original run/approval record is durable.

- [ ] **Step 1: Write outbox ordering/retry tests.**

  ```python
  async def test_failed_company_delivery_stays_pending_without_fake_runtime_success(repo, publisher) -> None:
      await repo.enqueue_runtime_signal(workspace_id="1001", source_kind="approval", source_id="approval_1", sequence=9, state="PENDING", observed_at=NOW)
      await publisher.deliver_due(limit=1)
      assert (await repo.claim_pending_signals(limit=1))[0].state_delivery == "PENDING"

  async def test_delivery_marks_row_only_after_company_2xx(repo, publisher, company_server) -> None:
      await repo.enqueue_runtime_signal(workspace_id="1001", source_kind="agent_run", source_id="run_1", sequence=2, state="FAILED", observed_at=NOW)
      await publisher.deliver_due(limit=1)
      assert await repo.is_signal_delivered("1001", "agent_run", "run_1", 2)
  ```

- [ ] **Step 2: Run it and verify it fails before publisher implementation.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_runtime_signal_delivery.py -q`

  Expected: FAIL because `AgentRuntimeSignalPublisher` does not exist.

- [ ] **Step 3: Implement durable signal production and delivery.**

  Create `AgentRuntimeSignalPublisher` using the configured Company service URL and service token, with staging/production validation through `validate_service_identity`. The API decision route enqueues only after `submit_decision` returns durable state; worker terminal paths enqueue only after the run repository commits its final status. A worker loop claims due outbox rows, posts the signed payload, marks `DELIVERED` only after Company 2xx, and otherwise increments attempt/backoff without erasing the row. The delivery client may be a fake only in the Python unit test; real integration uses the Company service.

- [ ] **Step 4: Run focused worker and route tests.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_runtime_signal_delivery.py tests/apps/cosa/test_routes.py tests/apps/cosa/worker/test_handlers.py -q
  ```

  Expected: PASS; a transient Company outage is recorded as pending/unavailable rather than reported as a resolved Runtime item.

- [ ] **Step 5: Commit signal delivery.**

  ```bash
  git add apps/cosa/events/runtime_signal.py apps/cosa/api/routes.py apps/cosa/worker apps/cosa/config/service_identity.py tests/apps/cosa/test_runtime_signal_delivery.py
  git commit -m "feat: publish durable agent runtime signals"
  ```

## Task 4: Replace Workforce Flutter legacy/fallback clients and UI

**Files:**

- Create: `frontend/lib/modules/agents/services/workforce_service.dart`
- Create: `frontend/lib/modules/agents/models/workforce_models.dart`
- Modify: `frontend/lib/modules/agents/services/agents_service.dart`
- Modify: `frontend/lib/modules/agents/services/agent_platform_service.dart`
- Modify: `frontend/lib/modules/agents/controllers/agents_controller.dart`
- Modify: `frontend/lib/modules/agents/views/agents_view.dart`
- Modify: `frontend/lib/modules/agents/views/widgets/agents_directory_tab.dart`
- Modify: `frontend/lib/modules/agents/views/widgets/agent_org_chart_widget.dart`
- Modify: `frontend/lib/modules/agents/views/widgets/agents_runs_history_tab.dart`
- Modify: `frontend/lib/modules/agents/views/widgets/agent_activity_timeline_widget.dart`
- Test: `frontend/test/workforce_service_test.dart`
- Test: `frontend/test/workforce_views_test.dart`

**Interfaces:**

- Consumes `MvpEndpoint.workforce*`, `MvpRequestClient` and typed Agent envelopes.
- Produces `ApiResult<List<WorkforceAssignment>>`, `ApiResult<List<RunSummary>>`, `ApiResult<List<Approval>>` and `ApiResult<List<WorkforceHealth>>` for controller/view rendering.

- [ ] **Step 1: Write failing Flutter tests for roster truth states.**

  ```dart
  testWidgets('unavailable workforce does not show the legacy default agent cards', (tester) async {
    await tester.pumpWidget(AgentsView.withService(FailingWorkforceService.unavailable()));
    expect(find.text('Không thể tải lực lượng agent'), findsOneWidget);
    expect(find.byType(AgentCard), findsNothing);
  });

  testWidgets('not observed is not rendered as healthy', (tester) async {
    await tester.pumpWidget(AgentsView.withService(RecordedWorkforceService.notObserved()));
    expect(find.text('Chưa có quan sát chạy/heartbeat'), findsOneWidget);
    expect(find.text('Healthy'), findsNothing);
  });
  ```

- [ ] **Step 2: Run the tests and verify the existing fallback behavior fails them.**

  Run: `cd frontend && flutter test test/workforce_service_test.dart test/workforce_views_test.dart`

  Expected: FAIL while `agents_service.dart` falls back from `/workforce/*` to `/agents/*` and while either agent service returns default/empty success on failure.

- [ ] **Step 3: Implement typed client and remove all Workforce fallbacks.**

  `WorkforceService` calls only generated `/agent/workforce/*` endpoint IDs and existing `/agent/runs/*`/`/agent/approvals/*` IDs declared in the manifest. Delete calls to `/workforce/*`, `/agents/*`, `fallbackResp`, default agent arrays and `return []`/`return null` error suppression from enabled paths. The controller retains failure objects and passes them to views.

- [ ] **Step 4: Render real composition versus assignment honestly.**

  Directory uses persisted assignments. Composition displays catalog eligibility as "có thể cấu hình" with its `assigned` value and reasons, never as active staff. Runs/approvals link to their real run/approval IDs. Health cards show `observed_at`, source link and `not_observed`/`unavailable` separately.

- [ ] **Step 5: Run focused Flutter verification and enable the manifest entries.**

  Run:

  ```bash
  cd frontend && flutter test test/workforce_service_test.dart test/workforce_views_test.dart
  cd frontend && flutter analyze
  node ../scripts/gen-mvp-contracts.mjs
  ```

  Expected: PASS. Flip only verified Workforce capability IDs to `enabled: true` and update their acceptance-ledger rows.

- [ ] **Step 6: Commit the Flutter cutover.**

  ```bash
  git add frontend/lib/modules/agents frontend/test/workforce_service_test.dart frontend/test/workforce_views_test.dart shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "feat: wire truthful workforce ui"
  ```

## Task 5: Prove real Workforce-to-Runtime flow

**Files:**

- Create: `tests/e2e/test_mvp_workforce_runtime_http.py`
- Modify: `tests/e2e/conftest.py`
- Modify: `docs/architecture/generated/route-inventory.allowlist.json`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Consumes actual Agent DB, FastAPI service, Company service and authenticated workspaces.
- Produces `VERIFIED` evidence for Workforce APIs and Agent-to-Company runtime projection.

- [ ] **Step 1: Write the full real-service scenario.**

  ```python
  def test_assignment_run_approval_signal_is_real_and_workspace_scoped(real_mvp_stack, workspace_a, workspace_b):
      assignment = real_mvp_stack.agent.create_assignment(workspace_a, functional_key="campaign_planner")
      assert real_mvp_stack.agent.list_assignments(workspace_a)["data"][0]["assignment_id"] == assignment["assignment_id"]
      approval = real_mvp_stack.agent.create_pending_approval(workspace_a, assignment)
      real_mvp_stack.agent.decide_approval(workspace_a, approval, approved=False)
      real_mvp_stack.worker.deliver_runtime_signals()
      assert real_mvp_stack.company.runtime_blockers(workspace_a)["meta"]["sources"]
      assert real_mvp_stack.agent.get_assignment(workspace_b, assignment["assignment_id"]).status_code in {403, 404}
  ```

- [ ] **Step 2: Run it against real services.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_workforce_runtime_http.py -q`

  Expected: PASS with actual service/database processes; explicit environment SKIP is permitted but never a mock substitute.

- [ ] **Step 3: Assert delayed delivery stays visible.**

  Stop only the test Company endpoint after an Agent durable transition, deliver once, and assert the outbox remains pending plus Workspace Runtime source status is unavailable/stale. Restore Company and assert exactly one projected signal appears after retry.

- [ ] **Step 4: Regenerate inventory and run relevant gates.**

  Run:

  ```bash
  make mvp-surface-check
  make contract-freeze-check
  PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_workforce_runtime_http.py -q
  ```

- [ ] **Step 5: Remove Workforce ghosts and commit evidence.**

  ```bash
  git add tests/e2e docs/architecture/generated docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "test: verify workforce runtime mvp flow"
  ```

## Completion gate

Run:

```bash
PYTHONPATH=$(pwd) python3 -m pytest tests/agent/workforce tests/apps/cosa/test_workforce_routes.py tests/apps/cosa/test_runtime_signal_delivery.py -q
cd frontend && flutter test test/workforce_service_test.dart test/workforce_views_test.dart
make mvp-surface-check
git diff --check
```

The slice is incomplete if an agent exists only in the static catalog, health is inferred without a persisted observation, a Company mirror owns Agent data, or a delivery error makes Workspace Runtime look complete.
