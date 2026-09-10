# COSA Startup Core Clean-Slate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Founder Trial baseline with a clean-slate, project-centric COSA Startup Core while retaining companion startup domains, Vault/Knowledge, Skills and governed agents.

**Architecture:** A new test-only three-plane baseline is built from empty databases, with Company as business authority, COSA as identity/policy authority and Agent Platform as a durable governed executor. The shared MVP contract drives all live public routes and Flutter clients. First establish the mandatory Project hierarchy and test it; then add companion-domain context, safe Vault/Knowledge, agents, UI and finally delete legacy framework surfaces and documentation.

**Tech Stack:** PostgreSQL, Encore/TypeScript, Drizzle ORM, Python/asyncpg, OpenAI Agents SDK, Flutter/GetX, Vitest, pytest and Flutter test.

**Spec:** `docs/superpowers/specs/2026-09-10-cosa-startup-core-clean-slate-design.md`

## Global Constraints

- Work directly on `main`; do not create a git worktree.
- This is a clean-slate product replacement: do not import, transform, dual-write, read-fallback or expose legacy business records.
- No reset or deletion runs against a database, volume or file until the exact test-only target and preconditions pass. The final destructive run needs a separate execution preflight.
- Company Services are business truth. Agent Platform never writes Company tables directly.
- Every business read/write filters `workspace_id` in the database query; every project-bound command checks `project_id` belongs to the verified workspace.
- Every live endpoint appears in `shared/contracts/mvp-surface.json`, generated contract files, a backend negative test and a Flutter typed-client test.
- Preserve one-way, single-purpose cross-plane secrets. Scheduler payloads contain IDs/pins only, never raw business/Vault/model payloads.
- Vault source/version/ACL is canonical; approved Knowledge is the retrieval projection. Source files, chunks, embeddings and prompts remain local to the Workspace Runtime Node.
- All visible Flutter copy is present in `vi-VN` and `en-US` catalogs.
- BSC, PESTEL, SWOT, TOWS, Porter, maturity, framework stage-gate scoreboards, Academy, voice/realtime, workflow-builder, automation-library, portfolio/roadmap/funding cockpit and their framework-only documents are removed only after the new replacement path passes its named tests. Workspace and Project lifecycle stages are retained.

---

## Delivery order

```text
1 reset safety and empty-baseline proof
          |
2 schemas + core hierarchy invariants
          |
3 Company operating-loop API + contract
          |
4 Flutter project operating screen
          |
5 companion startup domains and project links
          |
6 Vault/Knowledge safe vertical slice
          |
7 Skills, agent specs and durable project-scoped execution
          |
8 delete framework/product legacy code and routes
          |
9 documentation cutover and clean-baseline release gates
```

### Task 1: Replace the Founder Trial test-reset identity with Startup Core reset safety

**Files:**

- Modify: `scripts/test-db-reset-lib.mjs`
- Modify: `scripts/test-db-reset.mjs`
- Modify: `scripts/provision-founder-trial-test-dbs.sh`
- Modify: `tests/scripts/test_test_db_reset.mjs`
- Modify: `tests/e2e/test_founder_trial_baseline_reset.py`
- Modify: `Makefile`
- Modify: `.env.e2e.example`

**Interfaces:**

- Produces `RESET_CONFIRMATION = "CONFIRM_COSA_STARTUP_CORE_RESET"`.
- Preserves `parseResetTargets(env)`, `assertResetPreconditions(env, targets)`, `resetPlane(target)` and `runTestDatabaseReset(env)` as the only reset API.
- Produces `make test-db-reset`, which can operate only on `javis_agent_test`, `javis_cosa_test` and `javis_workspace_test` while `APP_ENV=test`.

- [ ] **Step 1: Write failing reset-identity tests**

  Change the reset test fixture to require the new confirmation and reject the old one:

  ```js
  const safeEnv = {
    APP_ENV: "test",
    TEST_DATABASE_RESET: "CONFIRM_COSA_STARTUP_CORE_RESET",
    AGENT_TEST_MIGRATOR_DATABASE_URL: "postgresql://agent_migrator:x@127.0.0.1/javis_agent_test",
    COSA_TEST_MIGRATOR_DATABASE_URL: "postgresql://cosa_migrator:x@127.0.0.1/javis_cosa_test",
    WORKSPACE_TEST_MIGRATOR_DATABASE_URL: "postgresql://workspace_migrator:x@127.0.0.1/javis_workspace_test",
  };
  assert.throws(
    () => assertResetPreconditions({ ...safeEnv, TEST_DATABASE_RESET: "CONFIRM_FOUNDER_TRIAL_MVP_RESET" }, parseResetTargets(safeEnv)),
    /CONFIRM_COSA_STARTUP_CORE_RESET/
  );
  ```

- [ ] **Step 2: Run the focused reset test and confirm it fails**

  Run: `node --test tests/scripts/test_test_db_reset.mjs`

  Expected: failure because the old reset confirmation is still accepted or the test fixture still names Founder Trial.

- [ ] **Step 3: Rename only the reset contract and test provisioning label**

  Change `RESET_CONFIRMATION`, comments, Make target invocation and provisioning script name/content to Startup Core. Keep target database names, role allowlist, advisory lock, non-test URL collision guard and migration invocation logic unchanged.

- [ ] **Step 4: Make the reset E2E assert an empty Startup Core ledger**

  Replace `_EXPECTED_LEDGER` with exactly the new `001_cosa_startup_core_baseline` files created in Task 2:

  ```python
  _EXPECTED_LEDGER = {
      ("agent", "001_cosa_startup_core_baseline.sql"),
      ("cosa", "001_cosa_startup_core_baseline.up.sql"),
      ("identity", "001_cosa_startup_core_baseline.up.sql"),
      ("operations", "001_cosa_startup_core_baseline.up.sql"),
      ("commercial", "001_cosa_startup_core_baseline.up.sql"),
      ("finance-legal", "001_cosa_startup_core_baseline.up.sql"),
  }
  ```

- [ ] **Step 5: Run reset unit tests**

  Run: `node --test tests/scripts/test_test_db_reset.mjs`

  Expected: PASS.

- [ ] **Step 6: Commit the reset-contract change**

  ```bash
  git add Makefile .env.e2e.example scripts/test-db-reset-lib.mjs scripts/test-db-reset.mjs scripts/provision-founder-trial-test-dbs.sh tests/scripts/test_test_db_reset.mjs tests/e2e/test_founder_trial_baseline_reset.py
  git commit -m "chore: rename test reset for startup core"
  ```

### Task 2: Create the empty three-plane Startup Core baseline

**Files:**

- Delete: `packages/agent/migrations/001_founder_trial_mvp_baseline.sql` through `005_fix_runtime_signal_outbox_sequence.sql`
- Delete: `services/cosa/migrations/001_founder_trial_mvp_baseline.up.sql` through `005_restore_baseline_gaps.up.sql` and corresponding `.down.sql` files
- Delete: `services/company/{identity,operations,commercial,finance-legal}/migrations/*`
- Create: `packages/agent/migrations/001_cosa_startup_core_baseline.sql`
- Create: `services/cosa/migrations/001_cosa_startup_core_baseline.up.sql`
- Create: `services/company/identity/migrations/001_cosa_startup_core_baseline.up.sql`
- Create: `services/company/operations/migrations/001_cosa_startup_core_baseline.up.sql`
- Create: `services/company/commercial/migrations/001_cosa_startup_core_baseline.up.sql`
- Create: `services/company/finance-legal/migrations/001_cosa_startup_core_baseline.up.sql`
- Modify: `services/company/shared/db/schema/{operations,strategy,commercial,customer-engagement,finance-legal,legal,academy,index}.ts`
- Modify: `packages/agent/migrations/README.md` if present; otherwise create it
- Modify: `tests/e2e/test_founder_trial_baseline_reset.py`
- Create: `tests/db_baseline_candidate/test_startup_core_schema.py`

**Interfaces:**

- Produces exactly six baseline migration ledger entries listed in Task 1.
- Produces Workspace lifecycle (`W0_IDEA` through `W5_SCALE`), Project lifecycle (`P0_DISCOVERY` through `P6_SCALE_GOVERN`) and the canonical Company hierarchy: `Project`, `Objective`, `KeyResult`, `Initiative`, `OperatingCycle`, `Week`, `Commitment`, `Task`.
- Produces only retained Control Plane and Agent substrate tables; no framework, Academy, automation product, realtime or legacy migration table remains.

- [ ] **Step 1: Write a failing schema-introspection test**

  Assert required columns and forbidden tables from a test database:

  ```python
  REQUIRED = {
      "strategy.projects": {"workspace_id"},
      "strategy.okr_objectives": {"workspace_id", "project_id"},
      "strategy.key_results": {"workspace_id", "objective_id"},
      "strategy.initiatives": {"workspace_id", "project_id", "key_result_id"},
      "operating.twelve_week_cycles": {"workspace_id", "project_id", "duration_weeks"},
      "operating.weekly_plans": {"workspace_id", "project_id", "cycle_id", "week_no"},
      "operating.weekly_commitments": {"workspace_id", "project_id", "weekly_plan_id"},
      "operating.tasks": {"workspace_id", "project_id", "weekly_commitment_id"},
  }
  FORBIDDEN_TABLES = {"strategy.pestel_signals", "strategy.swot_items", "strategy.tows_options", "strategy.portfolios", "academy.lesson_attempts"}
  ```

- [ ] **Step 2: Run the baseline schema test and confirm it fails**

  Run: `pytest tests/db_baseline_candidate/test_startup_core_schema.py -q`

  Expected: FAIL because the present schema has nullable/M:N hierarchy links and framework tables.

- [ ] **Step 3: Define Company baseline schema constraints**

  In the Operations baseline migration and Drizzle schema, make ownership direct and non-null. Use composite `(id, workspace_id)` foreign keys or trigger checks wherever a child references a parent so a valid ID from another workspace cannot be linked:

  ```sql
  ALTER TABLE strategy.okr_objectives
    ADD COLUMN project_id bigint NOT NULL,
    ADD CONSTRAINT fk_okr_objective_project_ws
      FOREIGN KEY (project_id, workspace_id)
      REFERENCES strategy.projects (id, workspace_id);

  ALTER TABLE operating.twelve_week_cycles
    ADD CONSTRAINT ck_cycle_duration CHECK (duration_weeks BETWEEN 1 AND 12),
    ADD CONSTRAINT fk_cycle_project_ws
      FOREIGN KEY (project_id, workspace_id)
      REFERENCES strategy.projects (id, workspace_id);

  CREATE UNIQUE INDEX uix_active_cycle_per_project
    ON operating.twelve_week_cycles (workspace_id, project_id)
    WHERE status = 'ACTIVE' AND deleted_at IS NULL;
  ```

  Retain `lifecycle_stage`, `stage_version` and `stage_entered_at` for Workspace and Project, plus append-only workspace/project lifecycle events. Do not create `task_projects`, `okr_objective_projects`, BSC/PESTEL/SWOT/TOWS/maturity tables, framework stage-gate tables or portfolio tables. Lifecycle events record human transitions; they do not implement automatic stage progression.

- [ ] **Step 4: Define the minimal Agent and Control Plane baselines**

  Keep exact-hash spec registry, conversations, runs, tool calls, checkpoints, approval, idempotency, schedules/leases and event inbox/outbox. Keep identity, membership, entitlement, connector and policy tables. Exclude skill candidate promotion, workforce product, automation product, realtime and framework-specific policy data.

- [ ] **Step 5: Rebuild the schema fingerprint only from the new baseline**

  Run: `make test-db-reset && make schema-fingerprint-write`

  Expected: reset succeeds only against the three named test databases; fingerprint contains no forbidden table.

- [ ] **Step 6: Run baseline proof**

  Run: `pytest tests/db_baseline_candidate/test_startup_core_schema.py tests/e2e/test_founder_trial_baseline_reset.py -q`

  Expected: PASS, including a second reset with identical fingerprint and exact ledger.

- [ ] **Step 7: Commit the baseline**

  ```bash
  git add packages/agent/migrations services/cosa/migrations services/company/identity/migrations services/company/operations/migrations services/company/commercial/migrations services/company/finance-legal/migrations services/company/shared/db/schema tests/db_baseline_candidate tests/e2e/test_founder_trial_baseline_reset.py deploy/schema/fingerprints.json
  git commit -m "feat: add startup core database baseline"
  ```

### Task 3: Implement Company operating-loop commands and tenant proof

**Files:**

- Modify: `services/company/operations/services/{project.service,okr.service,initiative.service,twelve-week-year.service,task.service}.ts`
- Modify: `services/company/identity/services/workspace.service.ts`
- Modify: `services/company/operations/handlers/{project.handler,okr.handler,initiative.handler,twelve-week-year.handler,task.handler}.ts`
- Modify: `services/company/identity/handlers/workspace.handler.ts`
- Create: `services/company/operations/services/project-operating-loop.service.ts`
- Create: `services/company/operations/handlers/project-operating-loop.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/operations/api.ts`
- Create: `services/company/operations/tests/project-operating-loop.service.test.ts`
- Create: `services/company/operations/tests/project-operating-loop.handler.test.ts`

**Interfaces:**

- Produces `getProjectOperatingLoop(ctx, projectId): ProjectOperatingLoop`.
- Produces `transitionWorkspaceLifecycle(ctx, workspaceId, {toStage, expectedStageVersion, rationale})` and `transitionProjectLifecycle(ctx, projectId, {toStage, expectedStageVersion, rationale})`; both append immutable lifecycle events and reject stale versions.
- Produces `createObjective`, `createKeyResult`, `createInitiative`, `createCycle`, `createWeeklyPlan`, `createCommitment`, `createTask` commands that accept a project-scoped request and reject hierarchy/workspace mismatch.
- Produces `PATCH /identity/workspaces/:workspaceId/lifecycle`, `PATCH /operations/projects/:projectId/lifecycle`, `POST /operations/projects/:projectId/operating-loop/{objectives|cycles|weeks|commitments|tasks}` and `GET /operations/projects/:projectId/operating-loop`.

- [ ] **Step 1: Write failing service tests for hierarchy rejection**

  ```ts
  await expect(createInitiativeAuthorized(ctxA, {
    projectId: projectA.id.toString(),
    keyResultId: keyResultFromProjectB.id.toString(),
    title: "Must reject",
  })).rejects.toThrow(/project|workspace/i);

  await expect(advanceTaskService(ctxA, {
    taskId: draftUnplannedTask.id.toString(),
    status: "IN_PROGRESS",
  })).rejects.toThrow(/weekly commitment/i);

  await expect(transitionProjectLifecycle(ctxA, projectA.id.toString(), {
    toStage: "P2_SOLUTION_VALIDATION",
    expectedStageVersion: 0,
    rationale: "validated interviews",
  })).resolves.toMatchObject({ lifecycleStage: "P2_SOLUTION_VALIDATION", stageVersion: 1 });
  ```

- [ ] **Step 2: Run the focused service test and confirm it fails**

  Run: `cd services/company && npx vitest run operations/tests/project-operating-loop.service.test.ts`

  Expected: FAIL because existing optional/M:N paths permit an invalid link or task transition.

- [ ] **Step 3: Implement one project-scoped transaction boundary**

  `project-operating-loop.service.ts` must load `project` using `(id, workspaceId)`, create children inside a transaction and write task/commitment links from the verified parent rows. The direct task transition guard is:

  ```ts
  if (nextStatus === "IN_PROGRESS" && task.weeklyCommitmentId === null) {
    throw APIError.failedPrecondition("Task must belong to an active weekly commitment before it can start");
  }
  ```

  Use the repository's actual `APIError` equivalent if `failedPrecondition` is unavailable; do not return a raw `Error`.

  Implement lifecycle transitions in one transaction with the optimistic predicate. Do not call framework evaluation or a model:

  ```ts
  const updated = await tx.update(projects)
    .set({ lifecycleStage: toStage, stageVersion: expectedStageVersion + 1, stageEnteredAt: new Date() })
    .where(and(eq(projects.id, projectId), eq(projects.workspaceId, workspaceId), eq(projects.stageVersion, expectedStageVersion)))
    .returning();
  if (updated.length !== 1) throw APIError.aborted("Project lifecycle changed; reload before retrying");
  await tx.insert(projectLifecycleEvents).values({ workspaceId, projectId, fromStage, toStage, actorId, rationale });
  ```

- [ ] **Step 4: Add public handler authorization tests**

  Test missing bearer, wrong workspace header, valid member of another workspace, project from another workspace, and optimistic cycle revision conflict. Each must return the repository's public `unauthenticated`, `permissionDenied`, `notFound` or conflict response without leaking a foreign record.

- [ ] **Step 5: Run Company tests and typecheck**

  Run: `cd services/company && npx vitest run operations/tests/project-operating-loop.service.test.ts operations/tests/project-operating-loop.handler.test.ts && npm run typecheck`

  Expected: PASS.

- [ ] **Step 6: Commit the operating-loop vertical slice**

  ```bash
  git add services/company/operations
  git commit -m "feat: add project operating loop commands"
  ```

### Task 4: Make the shared contract the only public Startup Core route registry

**Files:**

- Modify: `shared/contracts/mvp-surface.json`
- Modify: `scripts/gen-mvp-contracts.mjs`
- Modify: `scripts/mvp_surface_check.py`
- Modify: `services/company/shared/contracts/mvp-surface.generated.ts` (generated)
- Modify: `apps/cosa/api/mvp_contracts_generated.py` (generated)
- Modify: `frontend/lib/core/network/mvp_endpoints.g.dart` (generated)
- Modify: `services/cosa/services/{mvp-contract-policy,surface-policy}.ts`
- Modify: `tests/contracts/test_founder_trial_mvp_surface.py`
- Create: `tests/contracts/test_startup_core_mvp_surface.py`
- Modify: `tests/quality/test_generated_mvp_contracts.py`

**Interfaces:**

- Produces contract capabilities `project.loop.read`, `project.okr.write`, `project.cycle.write`, `project.week.write`, `project.commitment.write`, `project.task.write` plus retained CRM, Sales, Marketing, Support, Finance, Legal, Vault/Knowledge, Skill and agent capabilities.
- Every project-bound capability has `requires_workspace: true`, `requires_project: true`, an owner, exact handler test and typed Flutter client symbol.

- [ ] **Step 1: Write a failing manifest test**

  ```python
  ids = {item["id"] for item in CONTRACT["capabilities"]}
  assert {"project.loop.read", "project.okr.write", "project.cycle.write", "project.task.write"} <= ids
  assert not any(token in item["id"] for item in CONTRACT["capabilities"] for token in ("bsc", "pestel", "swot", "tows", "maturity", "automation"))
  ```

- [ ] **Step 2: Run contract test and confirm it fails**

  Run: `pytest tests/contracts/test_startup_core_mvp_surface.py -q`

  Expected: FAIL because the current manifest still publishes Founder Trial and automation capability IDs.

- [ ] **Step 3: Replace the manifest entries and generator validation**

  Add `requires_project` to the source manifest format and make the generator reject an endpoint declared project-bound without a `:projectId` path parameter. Generate a typed `MvpEndpoint` constant for every retained live endpoint. Delete every framework/automation/Founder Trial-only entry rather than marking it disabled.

- [ ] **Step 4: Regenerate and assert no drift**

  Run: `make mvp-contracts-gen && make mvp-contracts-check && python3 scripts/mvp_surface_check.py`

  Expected: generated TS/Python/Dart files match the new source manifest.

- [ ] **Step 5: Run route and client contract gates**

  Run: `make frontend-api-contract-check && make route-inventory-check`

  Expected: PASS with no allowlist addition for a removed route.

- [ ] **Step 6: Commit contract replacement**

  ```bash
  git add shared/contracts scripts/gen-mvp-contracts.mjs scripts/mvp_surface_check.py services/company/shared/contracts apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart services/cosa/services tests/contracts tests/quality
  git commit -m "feat: define startup core public contract"
  ```

### Task 5: Replace Flutter strategy cockpit with one project operating screen

**Files:**

- Create: `frontend/lib/modules/projects/models/project_operating_loop.dart`
- Create: `frontend/lib/modules/projects/services/project_operating_loop_service.dart`
- Create: `frontend/lib/modules/projects/controllers/project_operating_loop_controller.dart`
- Create: `frontend/lib/modules/projects/views/project_operating_loop_view.dart`
- Create: `frontend/lib/modules/projects/services/project_lifecycle_service.dart`
- Create: `frontend/lib/modules/projects/views/widgets/lifecycle_header.dart`
- Create: `frontend/lib/modules/projects/views/widgets/{okr_section,cycle_week_section,commitment_task_section,evidence_decision_section}.dart`
- Modify: `frontend/lib/core/routing/{module_routes,app_routes,app_pages}.dart`
- Modify: `frontend/lib/modules/tasks/{controllers/tasks_controller.dart,services/task_service.dart,views/tasks_view.dart}`
- Delete: `frontend/lib/modules/strategy/views/tabs/{foundation_tab,strategy_lenses_tab,stage_gate_audit_tab,validation_studio_tab,project_roadmap_tab,project_funding_tab}.dart`
- Delete: `frontend/lib/modules/strategy/services/{strategy_lens_service,stage_gate_service,pmf_scoreboard_service,portfolio_service,canvas_service}.dart`
- Modify: `frontend/lib/core/localization/locales/{vi,en}/**.dart`
- Create: `frontend/test/modules/projects/project_operating_loop_service_test.dart`
- Create: `frontend/test/modules/projects/project_operating_loop_view_test.dart`

**Interfaces:**

- Produces `ProjectOperatingLoopService.get(String projectId)` using `MvpEndpoint.projectLoopRead`.
- Produces `ProjectOperatingLoopController` with `load`, `transitionLifecycle`, `createObjective`, `createCycle`, `createCommitment`, `createTask` and conflict-refresh handling.
- Produces canonical route `/work/projects/:projectId`; removes standalone OKR/12WY/framework routes.

- [ ] **Step 1: Write a failing typed-client test**

  ```dart
  test('gets a project loop through the generated endpoint', () async {
    final result = await service.get('42');
    expect(client.lastRequest.path, '/operations/projects/42/operating-loop');
    expect(result.project.id, '42');
  });
  ```

- [ ] **Step 2: Run Flutter test and confirm it fails**

  Run: `cd frontend && flutter test test/modules/projects/project_operating_loop_service_test.dart`

  Expected: FAIL because no project operating client/screen exists.

- [ ] **Step 3: Implement the project view and task binding**

  Render a lifecycle header and transition history before the four sections: `OKRs`, `Cycle & Weekly`, `Tasks`, `Evidence & Decisions`. The lifecycle header uses the typed lifecycle endpoint and current `stageVersion`; it shows the development stage but does not show a framework gate score or block work. Task creation sends project and weekly commitment IDs; task cards display project/week/commitment instead of relying on metadata. On cycle or lifecycle revision conflict, reload the loop before rendering the command again.

- [ ] **Step 4: Remove framework navigation and translations**

  Remove BSC/PESTEL/SWOT/TOWS/maturity/framework-stage-gate/roadmap/funding/canvas route registration, sidebar entries, voice/Hub commands, controllers, widgets and localization keys. Retain Workspace and Project lifecycle labels, transition commands, state history and context displays. Do not retain a PLANNED redirect or a mock response for a removed module.

- [ ] **Step 5: Run UI tests and analyzer**

  Run: `cd frontend && flutter test test/modules/projects/project_operating_loop_service_test.dart test/modules/projects/project_operating_loop_view_test.dart && flutter analyze`

  Expected: PASS.

- [ ] **Step 6: Commit the project UI**

  ```bash
  git add frontend/lib frontend/test
  git commit -m "feat: add project operating loop screen"
  ```

### Task 6: Retain companion startup domains through typed project context

**Files:**

- Modify: `services/company/commercial/services/{contact,lead,opportunity,interview,marketing-campaign,marketing-experiment}.service.ts`
- Modify: `services/company/commercial/handlers/*.handler.ts`
- Modify: `services/company/finance-legal/services/{budget-summary,financial-snapshot,financial-transaction,legal-obligation}.service.ts`
- Modify: `services/company/finance-legal/handlers/*.handler.ts`
- Modify: `services/company/operations/strategy/services/{evidence-lifecycle,decision-recording}.service.ts`
- Modify: `frontend/lib/modules/{sales,marketing,finance,legal}/**.dart`
- Create: `services/company/commercial/tests/project-context.test.ts`
- Create: `services/company/finance-legal/tests/project-context.test.ts`
- Create: `frontend/test/modules/projects/project_companion_context_test.dart`

**Interfaces:**

- Produces a typed `projectId` on project-relevant commercial, marketing, finance and legal commands.
- Produces explicit `submit...Evidence` commands that create a reviewable candidate rather than silently promoting external facts to evidence.
- Produces a Project loop context response with typed lists/references, not copied raw commercial/financial/legal payloads.

- [ ] **Step 1: Write failing cross-project tests**

  ```ts
  await expect(createMarketingExperiment({
    workspaceId: workspaceA,
    projectId: projectB,
    authorization: bearerA,
    name: "cross-project",
  })).rejects.toThrow(/not found|workspace/i);

  await expect(linkBudgetToProject({
    workspaceId: workspaceA,
    projectId: projectB,
    budgetId: budgetA,
  })).rejects.toThrow(/project/i);
  ```

- [ ] **Step 2: Run focused companion-domain tests and confirm they fail**

  Run: `cd services/company && npx vitest run commercial/tests/project-context.test.ts finance-legal/tests/project-context.test.ts`

  Expected: FAIL because legacy surfaces do not require or validate the direct project context.

- [ ] **Step 3: Implement typed project links and evidence provenance**

  Query every project-bearing record by `(id, workspace_id, project_id)`. Keep CRM customer/account truth workspace-scoped with typed N:M project links; require a single project link when a lead, interview, opportunity, campaign, marketing experiment, support fact, allocation, budget or obligation is used in the operating loop. Return source record ID, source type, author, observed timestamp and approval state with evidence.

- [ ] **Step 4: Preserve deterministic high-risk policy**

  For paid marketing, outbound sends, payment, accounting confirmation and legal commitment, require the existing capability/governance/approval path. Assert in tests that denial happens before a Company write and that workspace liquidity is returned separately from project budget.

- [ ] **Step 5: Run service and Flutter context tests**

  Run: `cd services/company && npx vitest run commercial/tests/project-context.test.ts finance-legal/tests/project-context.test.ts && npm run typecheck`

  Run: `cd frontend && flutter test test/modules/projects/project_companion_context_test.dart`

  Expected: PASS.

- [ ] **Step 6: Commit companion-domain integration**

  ```bash
  git add services/company/commercial services/company/finance-legal services/company/operations/strategy frontend/lib/modules frontend/test/modules/projects
  git commit -m "feat: link startup domains to project context"
  ```

### Task 7: Complete the safe local Vault/Knowledge vertical slice

**Files:**

- Modify: `apps/cosa/api/{vault_routes,knowledge_routes,vault_schemas,schemas,routes}.py`
- Modify: `apps/cosa/knowledge_ingestion/{dependencies,handler,publish,object_store}.py`
- Modify: `packages/agent/{vault,knowledge}/**.py`
- Modify: `apps/cosa/composition/{agent_plane,storage_factory,context_assembler}.py`
- Create: `apps/cosa/api/project_knowledge_routes.py`
- Create: `tests/apps/cosa/api/test_project_knowledge_routes.py`
- Create: `tests/integration/test_startup_core_knowledge_e2e.py`
- Create: `frontend/lib/modules/knowledge/{services,models,views}/**.dart`
- Create: `frontend/test/modules/knowledge/project_knowledge_service_test.dart`

**Interfaces:**

- Produces audited `POST /agent/vault/documents`, version upload/finalize, review, publish, reject, archive, revoke and purge commands.
- Produces `POST /agent/knowledge/projects/:projectId/search` with `{query, limit}` and citations `{documentId, versionId, chunkId, title, excerpt}`.
- Produces 404 for an unauthorized document or source ID, rather than revealing whether it exists.

- [ ] **Step 1: Write failing authorization and provenance tests**

  ```python
  response = client.post(
      f"/agent/knowledge/projects/{foreign_project_id}/search",
      headers=workspace_a_headers,
      json={"query": "pricing", "limit": 5},
  )
  assert response.status_code == 404

  assert result["citations"][0].keys() >= {"documentId", "versionId", "chunkId", "title", "excerpt"}
  ```

- [ ] **Step 2: Run focused Knowledge tests and confirm they fail**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_project_knowledge_routes.py -q`

  Expected: FAIL because Vault routes currently do not expose an authorized retrieval lifecycle.

- [ ] **Step 3: Wire the local lifecycle without remote raw-content fallback**

  Require the injected scanner/sandbox/object store in production. Persist document/version/ACL and ingestion state locally, enqueue references only, make reviewer approval the only transition that publishes a retrieval source, and enforce workspace + project context + ACL at search time. The result construction is:

  ```python
  return {
      "items": [
          {"text": hit.text, "citations": [hit.citation.to_dict()]}
          for hit in authorized_hits
      ]
  }
  ```

- [ ] **Step 4: Add Flutter Knowledge surface through generated endpoint symbols**

  Show document state, source provenance and project-scoped search citations. Never show an upload/retrieval CTA while the corresponding manifest capability is unavailable.

- [ ] **Step 5: Run local process and Flutter proofs**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_project_knowledge_routes.py tests/integration/test_startup_core_knowledge_e2e.py -q`

  Run: `cd frontend && flutter test test/modules/knowledge/project_knowledge_service_test.dart`

  Expected: PASS, including restart-safe retrieval and cross-workspace 404.

- [ ] **Step 6: Commit Vault/Knowledge slice**

  ```bash
  git add apps/cosa/api apps/cosa/knowledge_ingestion apps/cosa/composition packages/agent/vault packages/agent/knowledge tests/apps/cosa tests/integration frontend/lib/modules/knowledge frontend/test/modules/knowledge
  git commit -m "feat: add project scoped vault knowledge"
  ```

### Task 8: Scope retained Skills and agents to Workspace and Project

**Files:**

- Modify: `apps/cosa/agents/{specs,agent_profile_specs,seed,capability_risk_map}.py`
- Modify: `apps/cosa/worker/{handlers,wga_run,copilot_run,autopilot_run,run_core}.py`
- Modify: `apps/cosa/composition/{capability_registration,context_assembler,agent_plane}.py`
- Modify: `apps/cosa/api/{conversation_routes,model_policy_routes,skill_registry_routes}.py`
- Modify: `packages/agent/{contracts,governance,skills,runs}/**.py`
- Delete: `apps/cosa/worker/{kickoff_suggestion_run,outcome_analysis_run,work_package_run}.py`
- Delete: framework-only Skillpacks under `skillpacks/{strategy,analytics,lifecycle}/`
- Create: `tests/apps/cosa/worker/test_project_scoped_agent_run.py`
- Create: `tests/agent/test_project_capability_governance.py`

**Interfaces:**

- Retains profiles `operations`, `founder_assistant`, `marketing`, `finance`, `customer_support`, `customer_support_autopilot`.
- Adds mandatory `project_id` to retained project-operating agent requests and Company delegation claims.
- Produces `operations.task.create_draft` only; no agent can start an unplanned task or execute a high-risk companion action outside approval.

- [ ] **Step 1: Write failing agent context tests**

  ```python
  result = await execute_run_task(plane, stream, {
      "workspace_id": workspace_id,
      "agent_profile": "operations",
      "project_id": None,
  })
  assert result.status == "failed"
  assert result.error == "project_context_required"
  ```

- [ ] **Step 2: Run the focused agent tests and confirm they fail**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/worker/test_project_scoped_agent_run.py tests/agent/test_project_capability_governance.py -q`

  Expected: FAIL because current runs can resolve a generic Operations context without mandatory project ownership.

- [ ] **Step 3: Add project claim propagation and capability checks**

  Verify that the conversation/request principal may access the project before creating a durable task. Include `project_id` in the scoped Company delegation claim, request envelope and audit lineage. The capability boundary must reject a Company response whose `projectId` does not equal the pinned run project.

- [ ] **Step 4: Reduce agents and Skills without deleting retained domain capability**

  Remove framework skills and kickoff/framework worker branches. Keep code-authored exact-hash specs, static pinned Skill manifests and retained domain profiles. Remove runtime skill candidate/promotion/self-authoring routes; do not remove read-only Skill provenance required by an AgentSpec.

- [ ] **Step 5: Prove durable restart and approval behavior**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/worker/test_project_scoped_agent_run.py tests/agent/test_project_capability_governance.py tests/apps/cosa/worker/test_crash_recovery_subprocess.py -q`

  Expected: PASS; a restarted worker resumes/terminates safely, denied payment/send/legal actions do not reach Company, and unknown profiles fail closed.

- [ ] **Step 6: Commit agent scope changes**

  ```bash
  git add apps/cosa packages/agent skillpacks tests/apps/cosa tests/agent
  git commit -m "feat: scope agents to startup projects"
  ```

### Task 9: Delete legacy framework/product code, contracts and tests after replacement proof

**Files:**

- Delete: framework handlers/services/tests under `services/company/operations/strategy/` matching `pestel`, `swot`, `tows`, `maturity`, `strategy-analysis`, `strategic-objective`, `workspace-strategy-settings`, `pmf-scoreboard`, `gate-evaluation` and `stage-gate`; do not delete Workspace/Project lifecycle records, handlers, events or context adapters
- Delete: canvas, automation, portfolio, roadmap, funding, Academy and realtime implementation directories after `rg` proves no retained importer
- Delete: `frontend/lib/modules/{academy,automation,remote_access,workflows}/`
- Delete: framework/placeholder route entries in `frontend/lib/core/routing/`
- Delete: `services/realtime_agent/`, `services/company/academy/`, and their tests/configuration only after service startup references are removed
- Modify: `services/company/{operations,commercial,finance-legal}/api.ts`, `apps/cosa/api/routes.py`, `docker-compose.yml`, `services/docker-compose.yml`, `Makefile`, `.github/workflows/quality.yml`
- Create: `tests/quality/test_removed_startup_core_surfaces.py`

**Interfaces:**

- Produces an import/route contract where no retained startup module references a removed feature.
- Produces no public route, generated capability, route alias or UI placeholder for removed surfaces.

- [ ] **Step 1: Write a failing removal-surface test**

  ```python
  FORBIDDEN = ("bsc", "pestel", "swot", "tows", "porter", "maturity", "academy", "realtime_agent", "automation")
  for source in retained_source_files():
      assert not any(token in source.read_text().lower() for token in FORBIDDEN), source
  ```

  Exempt the historical `git` object database and this implementation plan; do not exempt runnable source, contract, deploy or generated route inventory. `lifecycle_stage`, lifecycle transition and lifecycle event references are explicitly retained and must not be included in this forbidden-token check.

- [ ] **Step 2: Run the removal test and confirm it fails**

  Run: `pytest tests/quality/test_removed_startup_core_surfaces.py -q`

  Expected: FAIL with concrete remaining import/route paths.

- [ ] **Step 3: Remove in dependency order**

  First remove handler/barrel exports and capability registration, then call sites, tests, frontend modules/routes/translations, Docker/CI service starts and finally the directories. For every directory, run before deletion:

  ```bash
  rg -n "<exact-module-import-or-route>" services apps packages frontend scripts Makefile docker-compose.yml services/docker-compose.yml .github
  ```

  Delete only when output contains no retained consumer.

- [ ] **Step 4: Regenerate inventories and run structural gates**

  Run: `make mvp-contracts-gen && make route-inventory && make mvp-contracts-check && make route-inventory-check && make frontend-boundary-check && make company-boundary-check`

  Expected: PASS; generated inventories do not list a removed endpoint.

- [ ] **Step 5: Run removal proof**

  Run: `pytest tests/quality/test_removed_startup_core_surfaces.py -q && make frontend-api-contract-check`

  Expected: PASS.

- [ ] **Step 6: Commit legacy product removal**

  ```bash
  git add -A services apps packages frontend skillpacks scripts Makefile docker-compose.yml services/docker-compose.yml .github tests shared/contracts docs/architecture/generated
  git commit -m "refactor: remove legacy strategy framework surfaces"
  ```

### Task 10: Cut documentation to Startup Core truth and prove the clean baseline

**Files:**

- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `DEPLOYMENT.md`
- Modify: `services/README.md`
- Modify: `frontend/README.md`
- Delete: `docs/academy/`
- Delete: `docs/archive/`
- Delete: framework/history-only documents in `docs/{implementation,features,integrations,recipes,development,runbooks,operations,architecture/reports,architecture/plans}/`
- Modify: `docs/architecture/overview/{00-tong-quan,01-bon-vung-kien-truc,02-workflow-nghiep-vu,03-agent-va-governance}.md`
- Modify: `docs/superpowers/specs/2026-09-10-cosa-startup-core-clean-slate-design.md`
- Modify: `docs/superpowers/plans/2026-09-10-cosa-startup-core-clean-slate.md`
- Modify: `scripts/check_doc_links.py`
- Create: `tests/e2e/test_startup_core_clean_baseline.py`

**Interfaces:**

- Produces a documentation index with retained architecture, Workspace/Project lifecycle, runbooks, contracts, tests and companion-domain behavior.
- Produces an E2E that constructs the startup loop, links companion facts, retrieves approved Knowledge and completes a governed agent run from empty test databases.

- [ ] **Step 1: Write the clean-baseline E2E before documentation deletion**

  ```python
  def test_startup_core_from_empty_baseline(stack):
      workspace = stack.create_workspace()
      project = stack.create_project(workspace)
      kr = stack.create_okr_with_key_result(project)
      initiative = stack.create_initiative(project, kr)
      cycle, week = stack.create_active_cycle_and_week(project, duration_weeks=12)
      commitment = stack.create_commitment(project, week, initiative)
      task = stack.create_task(project, commitment)
      stack.link_interview_evidence(project)
      stack.publish_and_search_vault_source(project, "pricing")
      stack.complete_governed_operations_run(project, task)
  ```

- [ ] **Step 2: Run E2E and confirm it fails before all slices land**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/e2e/test_startup_core_clean_baseline.py -q`

  Expected: FAIL until Tasks 2–8 are complete.

- [ ] **Step 3: Rewrite source-of-truth documentation**

  Make the README describe the Startup Core loop, Workspace/Project development lifecycle and retained companion domains; make CLAUDE list only active ADR/spec/plan documents. Mark the new design `ACCEPTED` only after its acceptance gate passes. Remove Founder Trial as source of truth and delete its superseded spec/plan after every inbound link is rewritten.

- [ ] **Step 4: Delete irrelevant documentation in reviewable batches**

  Delete Academy first, then archives/historical implementation reports, then framework documents. Before each batch run `rg -n "<document-path-or-title>" README.md CLAUDE.md DEPLOYMENT.md docs Makefile .github`; rewrite surviving active links in the same commit. Do not delete retained finance/legal, CRM/sales/marketing/support, Vault/Knowledge, Skills, governance, deployment or test documents.

- [ ] **Step 5: Run all documentation and release gates**

  Run: `make check-docs && make mvp-contracts-check && make contract-freeze-check && make verify && make e2e-cross-plane-smoke`

  Expected: PASS. If `make e2e-cross-plane-smoke` is blocked by missing local infrastructure, report the precise missing dependency and do not claim clean-baseline acceptance.

- [ ] **Step 6: Run the empty-baseline acceptance E2E**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/e2e/test_startup_core_clean_baseline.py tests/e2e/test_founder_trial_baseline_reset.py -q`

  Expected: PASS from a twice-reset empty test baseline.

- [ ] **Step 7: Commit documentation and acceptance evidence**

  ```bash
  git add -A README.md CLAUDE.md DEPLOYMENT.md services/README.md frontend/README.md docs scripts/check_doc_links.py tests/e2e docs/architecture/generated deploy/schema/fingerprints.json
  git commit -m "docs: cut over to startup core"
  ```

## Plan self-review

- Spec coverage: Tasks 1–2 establish clean-slate safety and mandatory data shape; Tasks 3–5 establish contract, operating loop and companion domains; Tasks 6–8 retain safe Vault/Knowledge, Skills and governed agents; Task 9 removes all excluded code; Task 10 updates documentation and proves the whole system from empty databases.
- Ordering: no deletion task precedes the working replacement it would invalidate. Schema reset is test-only until the final separately authorized execution preflight.
- No compatibility bridge: every task uses a new direct hierarchy and fresh contract; no task permits legacy route or data fallback.
- Evidence: each task begins red, names focused verification, and ends with a reviewable commit. The final task contains the only full clean-baseline acceptance claim.
