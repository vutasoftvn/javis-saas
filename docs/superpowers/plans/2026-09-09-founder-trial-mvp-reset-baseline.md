# Founder Trial MVP Reset Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Replace the test-only three-plane database history and legacy product surface with a fresh, verifiable Founder Trial MVP baseline.

**Architecture:** Company remains business authority, COSA remains membership, entitlement and connector authority, and Agent Platform becomes a small generic runtime. A test-only reset command recreates three named test databases from curated 001 Founder Trial baseline migrations. The shared MVP contract drives manifest, router, sidebar, typed Flutter clients and each live Founder Trial action.

**Tech Stack:** PostgreSQL, Encore and TypeScript, Drizzle ORM, Node.js, Python and asyncpg, Flutter and GetX, Vitest, pytest, Flutter test.

**Spec:** docs/superpowers/specs/2026-09-09-founder-trial-mvp-reset-baseline-design.md

## Global Constraints

- Work directly on main; do not create a git worktree.
- Preserve the existing user edit to frontend/test/flutter_test_config.dart. Do not stage, revert or format it.
- Test reset requires APP_ENV=test and TEST_DATABASE_RESET=CONFIRM_FOUNDER_TRIAL_MVP_RESET.
- Reset targets are exactly javis_agent_test, javis_cosa_test and javis_workspace_test. A mismatch fails before DDL.
- Test reset reads no fallback non-test URL and is absent from deploy, migrate-all, dev-migrate and dev-stack.
- Company is business truth. Agent Platform never writes the Company database directly.
- Do not add venture_lifecycle_plans, a lifecycle state machine, domain packets, persistent domain agents, automatic payment, campaign send, lead conversion, phase transition or founder decision.
- WorkspaceCapabilityManifest is the only UI-routing authority; ModuleVisibility is removed after migration.
- Each live public endpoint has handler authorization, tenant-scoped service access, shared contract entry, backend negative test and Flutter typed-client test.
- All new visible Flutter strings have vi-VN and en-US values.
- Delete a legacy migration, route, client or document only after its replacement has passed the named task tests.

---

## Dependency order

~~~text
Task 1 reset safety
        |
Task 2 shared contract
        |
        +---- Task 3 active-cycle command ----+
        +---- Task 4 truthful Brief ----------+---- Task 6 Control Plane manifest
        +---- Task 5 CRM, Marketing, Finance -+              |
                                                        Task 7 Agent core
                                                               |
                                                Task 8 Flutter navigation
                                                               |
                                             Task 9 Flutter Founder Trial
                                                               |
                                           Task 10 migration replacement
                                                               |
                                      Task 11 fresh E2E and document cutover
~~~

### Task 1: Add test-only reset safety

**Files:**

- Create: scripts/test-db-reset-lib.mjs
- Create: scripts/test-db-reset.mjs
- Create: tests/scripts/test_test_db_reset.mjs
- Create: tests/db_baseline_candidate/test_test_db_reset_contract.py
- Modify: Makefile
- Modify: .env.example

**Interfaces:**

- Produces parseResetTargets(env), assertResetPreconditions(env, targets), resetPlane(target), and runTestDatabaseReset(env).
- ResetTarget has plane, databaseName, migratorUrl, applicationUrl, migratorRole and migrate command fields.
- Later tasks call only make test-db-reset. No task uses raw broad deletion.

- [x] **Step 1: Write failing precondition tests**

Create tests/scripts/test_test_db_reset.mjs:

~~~js
import test from "node:test";
import assert from "node:assert/strict";
import { assertResetPreconditions, parseResetTargets } from "../../scripts/test-db-reset-lib.mjs";

const safeEnv = {
  APP_ENV: "test",
  TEST_DATABASE_RESET: "CONFIRM_FOUNDER_TRIAL_MVP_RESET",
  AGENT_TEST_MIGRATOR_DATABASE_URL: "postgresql://agent_migrator:x@127.0.0.1/javis_agent_test",
  COSA_TEST_MIGRATOR_DATABASE_URL: "postgresql://cosa_migrator:x@127.0.0.1/javis_cosa_test",
  WORKSPACE_TEST_MIGRATOR_DATABASE_URL: "postgresql://workspace_migrator:x@127.0.0.1/javis_workspace_test",
};

test("accepts only three exact test database names", () => {
  assert.doesNotThrow(() => assertResetPreconditions(safeEnv, parseResetTargets(safeEnv)));
  assert.throws(
    () => assertResetPreconditions({ ...safeEnv, APP_ENV: "development" }, parseResetTargets(safeEnv)),
    /APP_ENV=test/
  );
});
~~~

Add tests for absent confirmation, a URL ending in cosa, duplicate normalized
host-port-database tuple, a test URL equal to COSA_MIGRATOR_DATABASE_URL and a
missing test migrator URL.

- [x] **Step 2: Prove the test is red**

Run: node --test tests/scripts/test_test_db_reset.mjs
Expected: FAIL because the reset library does not exist.

- [x] **Step 3: Implement fail-closed reset parsing**

Create scripts/test-db-reset-lib.mjs with this immutable target metadata:

~~~js
export const TEST_RESET_TARGETS = [
  ["agent", "javis_agent_test", "AGENT_TEST_MIGRATOR_DATABASE_URL", "AGENT_TEST_DATABASE_URL",
   "agent_migrator", [process.env.PYTHON || ".venv/bin/python", "-m", "packages.agent.scripts.migrate"], "."],
  ["cosa", "javis_cosa_test", "COSA_TEST_MIGRATOR_DATABASE_URL", "COSA_TEST_DATABASE_URL",
   "cosa_migrator", ["node", "scripts/migrate.mjs"], "services/cosa"],
  ["workspace", "javis_workspace_test", "WORKSPACE_TEST_MIGRATOR_DATABASE_URL",
   "WORKSPACE_TEST_DATABASE_URL", "workspace_migrator", ["node", "scripts/migrate.mjs"], "services/company"],
];
~~~

Parse URL with URL, normalize host, default port 5432 and decoded database name.
Validate the exact confirmation, exact APP_ENV, three names, distinct tuples and
inequality with every defined AGENT, COSA and WORKSPACE non-test URL.

The wrapper scripts/test-db-reset.mjs connects through only the test migrator
URL. Per plane, it verifies SELECT current_database(), locks
founder-trial-test-reset plus plane name, fails if a non-system/non-public
schema owner is not the expected fixed migrator role, runs DROP OWNED BY on that
fixed role, drops remaining non-system schemas owned by it, restores REVOKE
CREATE ON SCHEMA public FROM PUBLIC, then launches that plane migration.

The implementation must not run DROP DATABASE, DROP SCHEMA public, DROP OWNED
BY PUBLIC, a volume command, a shell delete or an environment-derived SQL
identifier. Extensions in public, including vector, stay installed.

- [x] **Step 4: Add static guard and Make target**

Create the Python contract:

~~~python
def test_reset_validates_before_destructive_sql():
    source = (ROOT / "scripts/test-db-reset-lib.mjs").read_text()
    assert "CONFIRM_FOUNDER_TRIAL_MVP_RESET" in source
    assert source.index("assertResetPreconditions") < source.index("DROP OWNED BY")
    assert "DROP DATABASE" not in source
    assert "DROP SCHEMA public" not in source
~~~

Add to Makefile:

~~~make
test-db-reset: ## Recreate only Founder Trial test databases
	APP_ENV=test TEST_DATABASE_RESET=CONFIRM_FOUNDER_TRIAL_MVP_RESET node scripts/test-db-reset.mjs
~~~

Document empty test-only URL variable names in .env.example; do not add
credentials or a default connection string.

- [x] **Step 5: Verify and commit**

Run:

~~~bash
node --test tests/scripts/test_test_db_reset.mjs
.venv/bin/python -m pytest tests/db_baseline_candidate/test_test_db_reset_contract.py -q
~~~

Expected: PASS. Do not execute make test-db-reset before Task 9.

~~~bash
git add Makefile .env.example scripts/test-db-reset-lib.mjs scripts/test-db-reset.mjs \
  tests/scripts/test_test_db_reset.mjs tests/db_baseline_candidate/test_test_db_reset_contract.py
git commit -m "feat(test): add guarded founder-trial database reset"
~~~

### Task 2: Replace the shared MVP contract with the exact R1 surface

**Files:**

- Modify: shared/contracts/mvp-surface.json
- Regenerate: services/company/shared/contracts/mvp-surface.generated.ts
- Regenerate: frontend/lib/core/network/mvp_endpoints.g.dart
- Modify: scripts/frontend-api-contract-allowlist.json
- Create: tests/contracts/test_founder_trial_mvp_surface.py

**Interfaces:**

- Produces only these live capability IDs:

~~~text
settings.capability_manifest.read
strategy.founder_trial.board.read
strategy.operating_cycle.resize
strategy.assumption.create
strategy.assumptions.ranked
strategy.founder_trial.experiment.create
strategy.evidence.review
strategy.decision.create
strategy.founder_brief.read
commercial.contact.create
commercial.lead.create
commercial.interview.create
commercial.interview.submit_evidence
marketing.campaign.create
marketing.campaign.list
marketing.experiment.create
marketing.experiment.list
finance.budget_summary.read
finance.snapshot.latest
~~~

- [x] **Step 1: Write the failing exact-contract test**

Create tests/contracts/test_founder_trial_mvp_surface.py:

~~~python
def test_mvp_surface_is_exactly_founder_trial_r1():
    ids = {row["id"] for row in load_contract()["capabilities"]}
    assert ids == R1_IDS

def test_each_r1_capability_has_real_evidence_paths():
    for row in load_contract()["capabilities"]:
        assert row["enabled"] is True
        assert row["requires_workspace"] is True
        assert Path(row["backend_test"]).exists()
        assert Path(row["flutter_test"]).exists()
        assert Path(row["integration_test"]).exists()
~~~

- [x] **Step 2: Prove the current broad contract is red**

Run: .venv/bin/python -m pytest tests/contracts/test_founder_trial_mvp_surface.py -q
Expected: FAIL because canvas, strategy analysis, legacy marketing, and other
non-R1 endpoints are still listed.

- [x] **Step 3: Replace contract, regenerate clients and remove stale allowlist entries**

Use the exact endpoint shapes:

~~~text
GET   /platform/workspaces/:workspaceId/capability-manifest
GET   /operations/projects/:projectId/founder-trial-board
PATCH /operations/projects/:projectId/operating-cycle
POST  /operations/strategy/assumptions
GET   /operations/strategy/projects/:projectId/ranked-assumptions
POST  /operations/projects/:projectId/founder-trial/experiments
POST  /operations/strategy/evidence/:id/review
POST  /operations/strategy/decision-records
GET   /operations/projects/:projectId/founder-brief
POST  /commercial/contacts
POST  /commercial/leads
POST  /operations/strategy/interviews
POST  /operations/strategy/interviews/:id/submit-evidence
POST  /commercial/marketing/campaigns
GET   /commercial/marketing/campaigns
POST  /commercial/marketing/experiments
GET   /commercial/marketing/experiments
GET   /finance/budget-summary
GET   /finance/snapshots/latest
~~~

Run make mvp-contracts-gen. Remove every marketing legacy and revenue legacy
allowlist entry; never replace those entries with a wildcard.

- [x] **Step 4: Verify and commit**

Run:

~~~bash
.venv/bin/python -m pytest tests/contracts/test_founder_trial_mvp_surface.py -q
make mvp-contracts-check mvp-surface-check
~~~

Expected: PASS.

~~~bash
git add shared/contracts/mvp-surface.json services/company/shared/contracts/mvp-surface.generated.ts \
  frontend/lib/core/network/mvp_endpoints.g.dart scripts/frontend-api-contract-allowlist.json \
  tests/contracts/test_founder_trial_mvp_surface.py
git commit -m "feat(contract): restrict mvp surface to founder trial"
~~~

### Task 3: Implement the active Operating Cycle resize command

**Files:**

- Modify: services/company/operations/strategy/services/project-operating-setup.service.ts
- Modify: services/company/operations/strategy/handlers/project-operating-setup.handler.ts
- Modify: services/company/operations/strategy/services/founder-trial-board.service.ts
- Modify: services/company/operations/services/twelve-week-year.service.ts
- Modify: services/company/operations/handlers/twelve-week-year.handler.ts
- Create: services/company/operations/tests/active-cycle-resize.test.ts
- Modify: services/company/operations/tests/cycle-duration-roundtrip.test.ts
- Modify: services/company/operations/tests/founder-trial-board.service.test.ts

**Interfaces:**

- Produces resizeProjectOperatingCycle(ctx, projectId, { cycleId, durationWeeks,
  expectedRevision, reason }).
- Exposes PATCH /operations/projects/:projectId/operating-cycle.
- FounderTrialCycleView includes revision.

- [x] **Step 1: Write failing active-cycle tests**

~~~ts
it("resizes an ACTIVE cycle atomically and preserves completed review", async () => {
  const { ctx, project, cycle } = await createActivatedProjectWithCycle({ durationWeeks: 10 });
  await completeReview(ctx, cycle.id, { scheduledWeekNo: 1 });
  const changed = await resizeProjectOperatingCycle(ctx, project.id, {
    cycleId: String(cycle.id), durationWeeks: 6, expectedRevision: 1, reason: "Founder narrowed trial",
  });
  expect(changed.revision).toBe(2);
  expect(await setupDuration(project.id)).toBe(6);
  expect(await review(cycle.id, "WEEKLY", 1)).toMatchObject({ status: "COMPLETED" });
  expect(await review(cycle.id, "WEEKLY", 10)).toMatchObject({ status: "SUPERSEDED" });
  expect(await cycleRevisionCount(cycle.id)).toBe(1);
});

it("rejects stale revision and another workspace cycle", async () => {
  await expect(resizeProjectOperatingCycle(ctx, project.id, staleRequest)).rejects.toThrow(/revision conflict/);
  await expect(resizeProjectOperatingCycle(otherCtx, project.id, validRequest)).rejects.toThrow();
});
~~~

Add a 6 to 10 test that proves added review slots appear once.

- [x] **Step 2: Confirm existing behavior fails**

Run:

~~~bash
cd services/company && encore test operations/tests/active-cycle-resize.test.ts \
  operations/tests/cycle-duration-roundtrip.test.ts
~~~

Expected: FAIL because the existing Flutter-facing PUT refuses ACTIVE setup.

- [x] **Step 3: Implement the single project-scoped transaction**

In one transaction, verify project workspace, select non-deleted cycle by
cycleId plus projectId plus workspaceId, compare revision, validate integer
duration 1..12, call rescheduleCycleReviews, update cycle duration/end date/
revision, update project_operating_setups.cycleDurationWeeks, insert one
cycle_revisions audit record with before/after review schedule, and return the
refreshed Board cycle. Board review query filters cycle ID, workspace ID and
deletedAt.

Retire public duration update through PATCH /operations/cycles/:id. The old
generic endpoint may stay only for non-duration internal use if a direct caller
exists; no Flutter contract may expose it.

- [x] **Step 4: Verify and commit**

~~~bash
cd services/company && encore test operations/tests/active-cycle-resize.test.ts \
  operations/tests/cycle-duration-roundtrip.test.ts \
  operations/tests/founder-trial-board.service.test.ts
npm run typecheck
git add operations
git commit -m "feat(operations): resize active founder trial cycles safely"
~~~

### Task 4: Make evidence coverage and Founder Brief truthful

**Files:**

- Modify: services/company/operations/strategy/services/founder-trial-board.service.ts
- Modify: services/company/operations/strategy/services/founder-brief.service.ts
- Modify: services/company/operations/strategy/handlers/founder-brief.handler.ts
- Modify: services/company/operations/tests/founder-brief.service.test.ts
- Create: services/company/operations/tests/founder-trial-evidence-boundary.test.ts

**Interfaces:**

- Evidence has linkedToFounderTrialAssumption, computed by same-project
  experiment-to-assumption join.
- Axis state is NOT_ASSESSED, NO_EVIDENCE, EVIDENCE_PRESENT,
  CONFIGURATION_REQUIRED or UNAVAILABLE.
- Economics axis contains separate projectBudget and workspaceLiquidity
  subcomponents.
- Founder Brief returns non-authoritative nextReviewFocus, not a decision
  suggestion.

- [x] **Step 1: Write failing attribution and finance-composition tests**

~~~ts
it("excludes approved evidence from a generic experiment without assumptionId", async () => {
  const brief = await seededBrief({ approvedGenericExperimentEvidence: true });
  expect(axis(brief, "problem").state).toBe("NO_EVIDENCE");
  expect(axis(brief, "solution").state).toBe("NO_EVIDENCE");
});

it("does not call project economics tracking when only a workspace snapshot exists", async () => {
  const economics = axis(await seededBrief({ workspaceSnapshot: true }), "economics");
  expect(economics.projectBudget.state).toBe("CONFIGURATION_REQUIRED");
  expect(economics.workspaceLiquidity.state).toBe("EVIDENCE_PRESENT");
});
~~~

Also cover unlinked evidence, cross-project experiment evidence and soft-deleted
review exclusion.

- [x] **Step 2: Confirm existing implementation is red**

Run:

~~~bash
cd services/company && encore test operations/tests/founder-trial-evidence-boundary.test.ts \
  operations/tests/founder-brief.service.test.ts
~~~

Expected: FAIL because generic linked evidence is counted and cash changes the
single economics state.

- [x] **Step 3: Implement coverage-only Brief**

Build a map of only Board experiments that have an assumption owned by the
Board project. Approved evidence contributes only through that map. Keep
successCriteria display-only; never parse its text into a pass/fail outcome.
Replace supported, tracking and suggestedDecision with the types declared above.
DecisionRecord remains the sole source for proceed, pivot, kill and hold.

- [x] **Step 4: Verify and commit**

~~~bash
cd services/company && encore test operations/tests/founder-trial-board.service.test.ts \
  operations/tests/founder-trial-evidence-boundary.test.ts \
  operations/tests/founder-brief.service.test.ts
git add operations/strategy
git commit -m "fix(strategy): make founder brief evidence coverage truthful"
~~~

### Task 5: Retain only project-scoped CRM, pilot Marketing and factual Finance/CAS

**Files:**

- Modify: services/company/shared/db/schema/commercial.ts
- Modify: services/company/shared/db/schema/finance-legal.ts
- Modify: services/company/commercial/handlers/contact.handler.ts
- Modify: services/company/commercial/handlers/lead.handler.ts
- Modify: services/company/commercial/handlers/marketing.handler.ts
- Modify: services/company/operations/strategy/handlers/interview.handler.ts
- Modify: services/company/finance-legal/handlers/budget-summary.handler.ts
- Modify: services/company/finance-legal/handlers/finance-snapshot.handler.ts
- Create: services/company/commercial/tests/founder-trial-commercial-http.contract.test.ts
- Create: services/company/finance-legal/tests/founder-trial-finance-read-model.test.ts

**Interfaces:**

- Contacts use sales.contact_projects. Leads and interviews carry a typed
  project foreign key.
- Campaign/experiment list and create require projectId.
- BudgetSummaryView and WorkspaceLiquidityView are independent typed results.

- [x] **Step 1: Write failing tenant and false-empty tests**

~~~ts
await expect(createCampaign(ctxA, { projectId: projectB.id, title: "wrong" }))
  .rejects.toThrow(/project/i);
await expect(submitInterviewAsEvidence(ctxB, { id: interviewA.id })).rejects.toThrow();

const finance = await founderTrialFinance(ctx, project.id);
expect(finance.projectBudget.coverage).toBe("NO_ENVELOPE");
expect(finance.workspaceLiquidity.state).toBe("EVIDENCE_PRESENT");
~~~

Add CAS missing and failed cases; neither may return a fake numeric zero.

- [ ] **Step 2: Implement retained services and remove legacy source**

> Trạng thái 2026-09-10: phần "implement retained services" đã xong và có test
> (commit `fd682d47`). Phần "remove legacy source" bị hoãn — các handler/service/test
> legacy (`finance-tt58`, `payment-request`/`payment-allocation`, `ai-compliance-*`,
> `legal-applicability`, legacy marketing) vẫn còn trong cây, chỉ bị gỡ khỏi
> `shared/contracts/mvp-surface.json`. Xoá hẳn để lại cho một dọn dẹp sau.

The future baseline retains:

~~~text
sales.contacts, sales.sales_leads, sales.contact_projects
commercial.marketing_campaigns, commercial.marketing_experiments
strategy.interviews
finance.bank_connections, finance.cas_link_sessions, finance.cas_webhook_inbox,
finance.cas_sync_inbox, finance.bank_transactions, finance.financial_transactions,
finance.finance_exceptions, finance.financial_snapshots, finance.project_budget_envelopes
~~~

Remove legacy marketing context, forms, objectives, learnings, metrics,
attribution, recommendations, loops, skill execution, revenue cockpit,
engagement/outreach, TT58 reporting, payment request/allocation, accounting-book
confirmation, legal applicability and AI-compliance routes after import and
route inventory show no retained caller.

- [x] **Step 3: Verify and commit**

~~~bash
cd services/company && encore test commercial/tests/founder-trial-crm.contract.test.ts \
  commercial/tests/founder-trial-marketing-project.test.ts \
  commercial/tests/founder-trial-commercial-http.contract.test.ts \
  finance-legal/tests/founder-trial-finance-read-model.test.ts
cd ../.. && make mvp-surface-check frontend-api-contract-check
git add services/company/commercial services/company/finance-legal services/company/shared/db/schema
git commit -m "feat(company): reduce commercial and finance to founder trial"
~~~

### Task 6: Bind Capability Manifest to the shared contract

**Files:**

- Modify: services/cosa/services/surface-policy.ts
- Modify: services/cosa/services/workspace-settings.service.ts
- Modify: services/cosa/handlers/workspace-settings.handler.ts
- Create: services/cosa/services/mvp-contract-policy.ts
- Create: services/cosa/tests/workspace-capability-contract.test.ts
- Modify: services/cosa/tests/workspace-settings.test.ts

**Interfaces:**

- validateSurfacePolicyAgainstMvpContract(policy, contract) rejects AVAILABLE or
  PILOT surface without enabled contract IDs.
- Each live manifest entry has non-empty requiredCapabilities.
- Only PLANNED surface has null contractEndpoint.

- [x] **Step 1: Write failing policy tests**

~~~ts
it("rejects an AVAILABLE surface with no enabled contract capability", () => {
  expect(() => validateSurfacePolicyAgainstMvpContract([
    { surfaceKey: "founder_trial.board", defaultStatus: "AVAILABLE", requiredCapabilities: [] },
  ], contract)).toThrow(/requiredCapabilities/);
});

it("reports cash configuration required only when entitlement or CAS is absent", async () => {
  expect((await manifest({ finance: true, cas: false })).surface("finance.cash_liquidity").surfaceStatus)
    .toBe("CONFIGURATION_REQUIRED");
});
~~~

- [x] **Step 2: Implement validated static policy**

Import generated contract metadata through the new adapter. Map every AVAILABLE
and PILOT spec surface to its explicit capability IDs. Validate once at service
start and in unit tests, not by reading JSON on each HTTP request. Preserve
operator downgrade only; an operator cannot force AVAILABLE.

- [x] **Step 3: Verify and commit**

~~~bash
cd services/cosa && encore test tests/workspace-capability-contract.test.ts \
  tests/workspace-settings.test.ts
npm run typecheck
git add services/cosa/services services/cosa/handlers services/cosa/tests
git commit -m "feat(cosa): bind capability manifest to mvp contract"
~~~

### Task 7: Reduce Agent Platform to generic runtime core

**Files:**

- Modify: packages/agent/scripts/migrate.py
- Modify: packages/agent/registry/repository.py
- Modify: packages/agent/governance/providers/postgres.py
- Modify: packages/agent/conversations/repository.py
- Modify: apps/cosa/api/routes.py
- Modify: apps/cosa/api/model_policy_routes.py
- Modify: apps/cosa/api/conversation_routes.py
- Modify: apps/cosa/composition/storage_factory.py
- Create: tests/agent/test_founder_trial_agent_baseline.py
- Delete: out-of-scope Agent API, worker and storage modules after their imports
  have been removed

**Interfaces:**

- Retained Agent features are conversation, generic run/checkpoint/event/tool
  call, approval/idempotency, exact-hash registry and model provider policy.
- The agent runtime has no Company database credential or Company source import.

- [x] **Step 1: Write failing API/import allowlist tests**

~~~python
def test_agent_routes_exclude_out_of_scope_surfaces():
    source = (ROOT / "apps/cosa/api/routes.py").read_text()
    for forbidden in ("vault_routes", "workforce_routes", "schedule_routes",
                      "skill_registry_routes", "autopilot_metrics_routes"):
        assert forbidden not in source

def test_agent_runtime_has_no_company_database_dependency():
    source = (ROOT / "apps/cosa/composition/storage_factory.py").read_text()
    assert "WORKSPACE_DATABASE_URL" not in source
    assert "services.company" not in source
~~~

- [ ] **Step 2: Remove out-of-scope registration and persistence callers**

> Trạng thái 2026-09-10: wiring out-of-scope đã gỡ khỏi `apps/cosa/api/routes.py`
> và boundary "no Company DB" đã có test (commit `57ed48b6`). Nhưng các file module
> mồ côi (`vault_routes.py`, `workforce_routes.py`, `schedule_routes.py`,
> `skill_registry_routes.py`, `autopilot_metrics_routes.py`, …) chưa `git rm` —
> chúng chỉ không còn được import.

Keep exact-hash AgentSpec resolution and governance approval rules. Remove
Vault, knowledge, workforce, schedule, skill mutation, evaluation promotion,
autopilot, voice and external automation registration plus their direct callers.
Do not introduce an in-memory fallback for a configured production runtime.

- [x] **Step 3: Verify and commit**

~~~bash
.venv/bin/python -m pytest tests/agent/test_founder_trial_agent_baseline.py \
  tests/agent/scripts/test_migrate.py -q
make apps-cosa-test
git add packages/agent apps/cosa tests/agent tests/apps/cosa
git commit -m "refactor(agent): retain founder trial runtime core only"
~~~

### Task 8: Make Flutter session, routing and sidebar manifest-owned

**Files:**

- Modify: frontend/lib/core/services/workspace_capability_manifest_controller.dart
- Modify: frontend/lib/core/services/workspace_capability_manifest_service.dart
- Modify: frontend/lib/core/session/session_controller.dart
- Modify: frontend/lib/core/routing/module_routes.dart
- Modify: frontend/lib/modules/dashboard/models/dashboard_nav_config.dart
- Modify: frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Create: frontend/test/core/services/workspace_capability_manifest_workspace_test.dart
- Create: frontend/test/core/routing/founder_trial_manifest_route_test.dart
- Create: frontend/test/modules/dashboard/founder_trial_sidebar_test.dart

**Interfaces:**

- Controller exposes reloadForWorkspace(workspaceId), beginWorkspaceSwitch and
  currentWorkspaceId.
- statusFor returns UNAVAILABLE unless loaded response workspaceId equals
  currentWorkspaceId.
- ManifestRouteGuardMiddleware replaces ModuleVisibility guard and old dashboard
  index decisions for all retained modules.

- [x] **Step 1: Write failing workspace-switch and route tests**

~~~dart
test("workspace switch clears old manifest before the next response", () async {
  await controller.reloadForWorkspace("ws-a");
  controller.beginWorkspaceSwitch("ws-b");
  expect(controller.statusFor("founder_trial.board"), SurfaceStatus.unavailable);
});

testWidgets("planned marketing opens roadmap, not legacy cockpit", (t) async {
  await pumpWithManifest(t, {"marketing.experiments": "PLANNED"});
  await t.tap(find.text("Marketing"));
  expect(find.byKey(const Key("surface_state_planned")), findsOneWidget);
  expect(find.byType(MarketingCockpitView), findsNothing);
});
~~~

Cover logout, stale prior-workspace response, manifest HTTP failure and Finance
configuration-required state.

- [ ] **Step 2: Implement one client authority**

> Trạng thái 2026-09-10: manifest-owned navigation, workspace-switch clearing và
> sidebar trim đã xong và có test (commits `6dc7f716`, `7ab5022c`, `8cd93a14`).
> Nhưng `ModuleVisibility` controller/service/`ModuleVisibilitySettingsCard` chưa
> bị xoá — vẫn còn wired vào `settings_view.dart` (nay chạy qua adapter đọc từ
> manifest). Xoá hẳn để lại cho sau.

Pass workspaceId into manifest fetch. During session commit reload the new
workspace manifest after API runtime setup; on logout clear it. Ignore a
response for a non-current workspace.

Sidebar retains only Founder Trial, CRM, Marketing Pilot, Finance and Settings.
Routes render PLANNED, CONFIGURATION_REQUIRED or UNAVAILABLE state rather than
opening old views. Delete ModuleVisibility controller/service/routes/tests and
legacy dashboard index fallback after no caller remains.

- [x] **Step 3: Verify and commit**

~~~bash
cd frontend && flutter test test/core/services/workspace_capability_manifest_controller_test.dart \
  test/core/services/workspace_capability_manifest_workspace_test.dart \
  test/core/routing/founder_trial_manifest_route_test.dart \
  test/modules/dashboard/founder_trial_sidebar_test.dart
flutter analyze --no-pub
git add lib/core lib/modules/dashboard lib/modules/hologram_hub test/core test/modules/dashboard
git commit -m "feat(frontend): gate navigation with workspace manifest"
~~~

Expected: tests pass. The existing warning in test/flutter_test_config.dart is
user-owned and remains outside this commit.

### Task 9: Complete and localize Founder Trial Board

**Files:**

- Modify: frontend/lib/modules/strategy/views/strategy_view.dart
- Modify: frontend/lib/modules/strategy/views/tabs/founder_trial_tab.dart
- Modify: frontend/lib/modules/strategy/founder_trial/founder_trial_board_models.dart
- Modify: frontend/lib/modules/strategy/founder_trial/founder_trial_board_service.dart
- Modify: frontend/lib/modules/strategy/founder_trial/founder_trial_board_view.dart
- Modify: frontend/lib/modules/strategy/founder_trial/founder_brief_models.dart
- Modify: frontend/lib/modules/strategy/founder_trial/founder_brief_service.dart
- Create: frontend/lib/modules/strategy/founder_trial/founder_trial_commands.dart
- Modify: frontend/lib/core/localization/app_translations.dart and source maps
- Create: frontend/test/modules/strategy/founder_trial_full_loop_test.dart

**Interfaces:**

- Board cycle includes ID and revision. Board contains separate projectBudget and
  workspaceLiquidity summaries.
- FounderTrialCommands contains resizeCycle, createAssumption, createExperiment,
  submitInterviewEvidence, reviewEvidence and createDecision.
- FounderBrief contains five coverage axes and nextReviewFocus.

- [x] **Step 1: Write failing UI golden-path test**

~~~dart
testWidgets("founder completes strict evidence loop and sees review focus", (t) async {
  await pumpFounderTrial(t, manifest: availableFounderTrialManifest);
  await t.tap(find.byKey(const Key("create_assumption")));
  await enterAndSubmitAssumption(t, "Founders feel weekly cash uncertainty");
  await t.tap(find.byKey(const Key("create_experiment")));
  await enterStrictExperiment(t, method: "interview", criteria: "5 of 10");
  await t.tap(find.byKey(const Key("submit_interview_evidence")));
  await approveEvidence(t);
  expect(find.textContaining("Evidence present"), findsWidgets);
  expect(find.textContaining("Review focus"), findsOneWidget);
  expect(find.textContaining("Proceed"), findsNothing);
});
~~~

Add cases for no cycle, 412 resize conflict, no budget plus cash present, missing
CAS, unlinked evidence, English locale and PLANNED analysis card.

- [x] **Step 2: Implement partial-truth Board and commands**

Load Board, Brief, Budget and Liquidity through separate typed requests. A failed
CAS request does not hide a valid Board. Replace draft operating setup PUT with
the Task 3 PATCH and expected cycle revision.

Render this ordered composition:

~~~text
Start
This week
Evidence
Cash
Decision
~~~

Strict command sheets require assumption, method and success criteria before an
experiment request. Render review controls only when manifest and role allow.
Use a reactive parent for manifest-dependent cards. Give assumptions,
experiments and evidence distinct empty states. Render nextReviewFocus as
non-authoritative review context and retain an explicit DecisionRecord form.

Replace legacy strategy tabs with the Board and a manifest-driven roadmap card.
Use translation keys for all visible R1 strings in vi-VN and en-US.

- [x] **Step 3: Verify and commit**

~~~bash
cd frontend && flutter test test/modules/strategy/founder_trial_full_loop_test.dart \
  test/modules/strategy/founder_trial_board_service_test.dart \
  test/modules/strategy/founder_trial_board_view_test.dart \
  test/modules/strategy/founder_brief_service_test.dart
flutter analyze --no-pub
git add lib/modules/strategy lib/core/localization test/modules/strategy
git commit -m "feat(frontend): complete localized founder trial loop"
~~~

### Task 10: Replace migration histories with six curated baselines

**Files:**

- Create: packages/agent/migrations/001_founder_trial_mvp_baseline.sql
- Create: services/cosa/migrations/001_founder_trial_mvp_baseline.up.sql
- Create: services/company/identity/migrations/001_founder_trial_mvp_baseline.up.sql
- Create: services/company/operations/migrations/001_founder_trial_mvp_baseline.up.sql
- Create: services/company/commercial/migrations/001_founder_trial_mvp_baseline.up.sql
- Create: services/company/finance-legal/migrations/001_founder_trial_mvp_baseline.up.sql
- Modify: packages/agent/scripts/migrate.py
- Modify: services/cosa/scripts/migrate.mjs
- Modify: services/company/scripts/migrate.mjs
- Modify: scripts/check-migration-backward-compat.mjs
- Modify: scripts/test-migration-rollback.mjs
- Modify: deploy/schema/fingerprints.json
- Create: tests/e2e/test_founder_trial_baseline_reset.py
- Create: tests/quality/test_founder_trial_baseline_inventory.py
- Delete: historical migration trees under packages/agent/migrations,
  services/cosa/migrations and services/company/academy,commercial,finance-legal,
  identity,operations migrations

**Interfaces:**

- Normal apply and check remain. Company/COSA retain read-only check-pending.
- All runners reject the historical baseline flag.
- The initial ledger contains one 001 row for Agent, one for COSA and four for
  Company service groups.

- [x] **Step 1: Write failing reset and inventory tests**

~~~python
def test_reset_has_only_curated_001_ledger_rows():
    run_make("test-db-reset")
    run_make("test-db-reset")
    assert rows_for("agent") == [("agent", "001_founder_trial_mvp_baseline.sql")]
    assert rows_for("cosa") == [("cosa", "001_founder_trial_mvp_baseline.up.sql")]
    assert set(rows_for_company()) == {
        ("identity", "001_founder_trial_mvp_baseline.up.sql"),
        ("operations", "001_founder_trial_mvp_baseline.up.sql"),
        ("commercial", "001_founder_trial_mvp_baseline.up.sql"),
        ("finance-legal", "001_founder_trial_mvp_baseline.up.sql"),
    }
~~~

The inventory test asserts Company schemas are core, strategy, operating, sales,
commercial, finance and integration; COSA schemas are cosa and control_plane;
Agent schemas are agent, agent_governance, agent_registry, agent_conversation and
models. Assert academy, legal, validation, engagement, vault, knowledge and
agent_evals do not exist.

- [x] **Step 2: Author exact baseline allowlists**

Company baseline tables:

~~~text
core.workspaces, core.workspace_slugs, core.user_projections,
core.workspace_memberships, core.permission_definitions, core.workspace_roles,
core.role_permissions, core.member_role_assignments, core.cosa_delegation_replays
strategy.projects, strategy.assumptions, strategy.experiments, strategy.evidence,
strategy.evidence_ingestions, strategy.interviews, strategy.decision_records,
strategy.project_operating_setups, strategy.workspace_strategy_settings
operating.twelve_week_cycles, operating.cycle_reviews, operating.cycle_revisions,
operating.tasks, operating.weekly_plans, operating.weekly_commitments
sales.contacts, sales.sales_leads, sales.contact_projects
commercial.marketing_campaigns, commercial.marketing_experiments
finance.bank_connections, finance.cas_link_sessions, finance.cas_webhook_inbox,
finance.cas_sync_inbox, finance.bank_transactions, finance.financial_transactions,
finance.finance_exceptions, finance.financial_snapshots, finance.project_budget_envelopes
integration.event_outbox, integration.event_audit
~~~

Agent baseline contains only tables used by retained run, governance,
conversation, registry, model-policy and capability/event repositories. COSA
baseline contains only profile/membership, entitlement, connector, manifest
override/audit and retained runtime/model-setting tables.

Author DDL from the retained source files, with composite tenant foreign keys,
constraints, indexes and role grants. A legacy full schema dump can be compared
for constraints but must never be committed wholesale.

- [x] **Step 3: Replace histories and runner behavior**

Use scoped git rm on only the migration directories listed in this task, then
add the six baselines. Remove historical baseline parsing and behavior from all
three runners. A ledger containing pre-baseline rows fails with an instruction
to invoke only the guarded test reset.

Update rollback and compatibility tools so 001 cannot roll back and only
migrations after 001 require paired down SQL and compatibility review. Align all
retained Drizzle/Python source schemas with the new table allowlists. Remove
unused ORM exports/imports in the same commit.

- [x] **Step 4: Verify and commit**

~~~bash
make test-db-reset
make test-db-reset
.venv/bin/python -m pytest tests/e2e/test_founder_trial_baseline_reset.py \
  tests/quality/test_founder_trial_baseline_inventory.py -q
make schema-fingerprint-write
make schema-fingerprint-check
git add -A packages/agent/migrations services/cosa/migrations services/company \
  packages/agent/scripts/migrate.py services/cosa/scripts/migrate.mjs \
  services/company/scripts/migrate.mjs scripts deploy/schema tests/e2e tests/quality
git commit -m "refactor(db): reset three planes to founder trial baseline"
~~~

### Task 11: Prove the fresh-database R1 flow and remove superseded documents

**Files:**

- Modify: tests/e2e/test_founder_trial_http.py
- Create: tests/e2e/test_founder_trial_full_stack.py
- Modify: tests/e2e/test_cross_plane_smoke.py
- Modify: CLAUDE.md
- Delete: docs/superpowers/specs/2026-09-09-founder-trial-domain-agent-mvp-design.md
- Delete: docs/superpowers/specs/2026-09-09-founder-trial-r1-reconciled-plan.md
- Delete: docs/superpowers/plans/2026-09-09-founder-trial-evidence-crm-marketing-finance.md
- Delete: docs/superpowers/plans/2026-09-09-codebase-truthful-ui-remediation.md
- Delete: docs/superpowers/plans/2026-09-09-founder-trial-lifecycle-and-truthful-ui.md
- Delete: docs/superpowers/plans/2026-09-09-founder-trial-agent-orchestration.md
- Regenerate: docs/architecture/generated/route-inventory.md
- Regenerate: docs/architecture/generated/company-usage-inventory.md

**Interfaces:**

- test_founder_trial_full_stack.py is release proof for the exact R1 flow on
  Task 10 fresh databases.
- The new spec and this plan are the sole Founder Trial sources in CLAUDE.md.

- [x] **Step 1: Write real HTTP full-stack test**

~~~python
project = create_project(headers_a)
cycle = activate_cycle(project, duration_weeks=6)
assert resize_cycle(project, cycle["id"], cycle["revision"], 10).status_code == 200
assumption = create_assumption(project)
experiment = create_strict_experiment(project, assumption, "interview", "5 of 10")
interview = create_interview(project)
evidence = submit_interview_as_evidence(interview)
approve_evidence(evidence)
brief = founder_brief(project)
assert brief["axes"]["problem"]["state"] == "EVIDENCE_PRESENT"
assert brief["axes"]["economics"]["projectBudget"]["state"] == "CONFIGURATION_REQUIRED"
assert create_decision(project, "hold").status_code == 200
assert cross_workspace_read_or_mutate(headers_b, project).status_code in (403, 404)
~~~

Add stale-cycle-revision, missing CAS and stale manifest negative cases. Use
real HTTP with no mock transport.

- [x] **Step 2: Run E2E before documentation deletion**

~~~bash
make test-db-reset
.venv/bin/python -m pytest tests/e2e/test_founder_trial_http.py \
  tests/e2e/test_founder_trial_full_stack.py -q
make e2e-cross-plane-smoke
~~~

Expected: PASS. Collection alone is not evidence.

- [x] **Step 3: Perform document cutover and full release gates**

Use git rm for the six exact superseded documents. Update CLAUDE.md to cite only
the new spec and this plan as Founder Trial sources. Do not remove ADRs or
generic finance/legal documentation. Regenerate inventories and repair every
stale link without adding allowlist exceptions.

~~~bash
make test-db-reset
make mvp-contracts-check mvp-surface-check frontend-api-contract-check route-inventory-check
make company-boundary-check encore-handler-boundary-check ts-suppression-check
make services-test
make apps-cosa-test
make frontend-test
make frontend-analyze
make e2e-test
make e2e-cross-plane-smoke
git diff --check
git status --short
~~~

Expected: all gates pass. The only pre-existing edit may be
frontend/test/flutter_test_config.dart and must remain uncommitted.

- [x] **Step 4: Commit**

~~~bash
git add CLAUDE.md docs shared/contracts scripts tests services packages apps \
  frontend/lib frontend/test/core frontend/test/modules
git diff --cached -- frontend/test/flutter_test_config.dart
git commit -m "docs: cut over to founder trial mvp baseline"
~~~

The cached diff for frontend/test/flutter_test_config.dart must be empty. If it
is not, unstage only that path with git restore --staged; never discard the
user's working-tree edit.

## Plan self-review

| Spec requirement | Implementing tasks |
|---|---|
| Exact three-plane test reset and safety | 1, 10 |
| Curated baseline, no historical migration marking | 10 |
| Active cycle resize and review revision | 3 |
| Strict evidence and factual Founder Brief | 4 |
| CRM, Marketing and CAS/budget boundary | 5 |
| Contract-backed Control Plane manifest | 2, 6 |
| Small generic Agent Platform | 7, 10 |
| Manifest-only navigation and workspace switch | 8 |
| Localized Founder Trial Board and commands | 9 |
| Legacy source/document removal and fresh E2E proof | 5, 7, 9, 10, 11 |

The plan uses the same reset names, confirmation phrase, capability IDs, route
names and post-baseline migration rule throughout. Company intentionally has
four baseline ledger rows; Agent and COSA have one each.

---

## Trạng thái reconcile (2026-09-10)

Tất cả 11 task đều đã có commit landed trên `main` và deliverable + test tương ứng
tồn tại trong cây:

| Task | Commit chính | Ghi chú |
|---|---|---|
| 1 | `7626bf43` | xong |
| 2 | `e37b2c9f` | xong — `mvp-surface.json` version `2026-09-09-founder-trial-r1` |
| 3 | `b3bf6744` | xong |
| 4 | `117c9f5a` | xong |
| 5 | `fd682d47` | **một phần** — retained services + read model xong; xoá legacy source hoãn (xem Step 2) |
| 6 | `bb47062c` | xong |
| 7 | `57ed48b6` | **một phần** — route wiring + company-DB boundary xong; xoá file module mồ côi hoãn (xem Step 2) |
| 8 | `6dc7f716`, `7ab5022c`, `8cd93a14` | **một phần** — manifest-owned nav xong; xoá `ModuleVisibility` hoãn (xem Step 2) |
| 9 | `35910c51`, `daf5475a`, `a05e34d4` | xong |
| 10 | `81461673`, `8bd8a8c8`, `766c4906`, `f1898952` | xong — nhưng squash `001` bắt hụt schema, xem mục dưới |
| 11 | `766c4906`, `24a6908b` | xong |

## Post-cutover baseline restore — kết quả epic SP-A (2026-09-10)

Squash `pg_dump` của Task 10 (`001_founder_trial_mvp_baseline`) chỉ chụp được
khoảng **25%** schema company đã khai báo và làm rơi nhiều object mà code R1 đang
chạy vẫn cần. Epic SP-A
(`docs/superpowers/plans/2026-09-10-baseline-completeness-harness-health.md`) khôi
phục toàn bộ phần đó dưới dạng migration **expand-only** — không sửa `001`:

- `services/company/identity/migrations/002_restore_business_policy_tables.up.sql`
  — `core.workspace_policy_versions` + cutover markers; GENERATED IDENTITY trên
  `integration.event_outbox` / `event_audit`. (commit `a9709b70`)
- `packages/agent/migrations/004_restore_baseline_identity_columns.sql`
  — GENERATED IDENTITY trên 3 cột sequence của agent (`a9709b70`); **được sửa lại
  bởi** `packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.sql` —
  gỡ IDENTITY mà `004` gắn nhầm vào `agent.runtime_signal_outbox.sequence` (đây là
  natural key do caller cung cấp); mọi `enqueue_runtime_signal` đều fail trên
  baseline mới. (SP-A Task 5A, commit `0bd74844`)
- `services/cosa/migrations/004_seed_canonical_cosa_roles.up.sql`
  — `cosa.roles` thiếu `member`. (commit `a9709b70`)
- `services/company/finance-legal/migrations/002_restore_baseline_gaps.up.sql`
  — toàn bộ schema `legal` (~23 bảng, cấu trúc). (SP-A Task 1)
- `services/cosa/migrations/005_restore_baseline_gaps.up.sql`
  — `control_plane.document_ingestions` + `document_ingestion_audit_events`.
  (SP-A Task 2)
- `services/company/operations/migrations/004_restore_baseline_gaps.up.sql`
  — bảng runtime operating/strategy (`task_projects`, `runtime_source_signals`,
  `canvases`, …). (SP-A Task 5B)
- `services/company/finance-legal/migrations/003_restore_finance_baseline_gaps.up.sql`
  — 20 bảng `finance.*` bị thiếu. (SP-A Task 5C)
- `services/company/commercial/migrations/002_restore_baseline_gaps.up.sql`
  — 22 bảng `commercial.*` / `sales.*` bị thiếu. (SP-A Task 5C2)
- `services/company/operations/migrations/005_restore_baseline_gaps.up.sql`
  — 53 bảng `operating.*` / `strategy.*` bị thiếu. (SP-A Task 5C3)
- `services/company/finance-legal/migrations/004_seed_ai_legal_applicability_corpus.up.sql`
  — seed nội dung regulation (9 sources / 9 versions / 6 rules), giữ trạng thái
  `PENDING_REVIEW`. (SP-A Task 5F)

Kết quả: golden fingerprint nhóm `workspace` đi từ **70 → 171 bảng** sau SP-A.

**Cố ý KHÔNG khôi phục** (PLANNED, không thuộc R1 — reset spec §7.3): các schema
`vault`, `knowledge`, `agent_memory`, `agent_evals`, `agent_artifact` và
`engagement`. Test suite cũ của chúng bị `skip` kèm tham chiếu spec (SP-A Task 5D),
không re-enable.

**Follow-up ngoài phạm vi SP-A** (ghi lại cho sau): `make e2e-test` chưa nằm trong
CI; `apps/cosa/composition/kernel_factory.py` coi `model=` là tín hiệu "đây là
test" và âm thầm dựng `CosaDataModelGate(client=None)` (production không ảnh hưởng —
`model=None` → real client); schema `engagement.*` vẫn vắng (35 file vitest
`services/company/*/tests/customer-engagement/*`, chỉ chạy trong `services-test`);
DB `workspace` dev bị lệch checksum ở `identity/002` (operator: reset DB hoặc sửa
dòng trong `schema_migrations`).

**Regression guard:** `tests/quality/test_baseline_identity_columns.py` (theo dõi
6 cột DB-generated).
