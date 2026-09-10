# COSA Startup Core Clean-Slate — Execution Status & Gap Audit

> Companion to `2026-09-10-cosa-startup-core-clean-slate.md`. Records the verified
> state of the plan on 2026-09-10 and the phased structure for finishing it safely.

## Verified state (2026-09-10, `main` @ `4a3e5801`)

| Task | Commit | Verified state |
|---|---|---|
| 1 Reset identity → Startup Core | `8912b085` | ✅ `node --test tests/scripts/test_test_db_reset.mjs` 6/6 pass. `RESET_CONFIRMATION = CONFIRM_COSA_STARTUP_CORE_RESET`. |
| 2 Empty three-plane baseline | `d8ed690d` | ⚠️ Migration ledger renamed, but the baseline is **not empty**: `001_cosa_startup_core_baseline.up.sql` still creates `lifecycle_stage` / `stage_version` / `pestel_snapshots` / `tows_selection_limit` / `project_operating_setups` stage-gates. |
| 3 Operating-loop commands | `798dcd03` | ⚠️ New `project-operating-loop.*` files landed, but `okr.service.ts` / `initiative.service.ts` still **require** `towsOptionId` + `strategicObjectiveId` provenance and join `tows_options` / `strategic_objectives`. |
| 4 Shared contract as route registry | `f083ed1b` | ✅ `tests/contracts/test_startup_core_mvp_surface.py` 2/2 pass. |
| 5 Flutter project operating screen | `86db9b8c` | ⚠️ `frontend/lib/modules/projects/` slice added, but `frontend/lib/modules/strategy/` (84 files) + `hologram_hub` lens widgets still present and routed. |
| 6 Companion domains via project context | `9900e836` | Present; not independently re-verified. |
| 7 Vault/Knowledge slice | `342e65ef` | Present; not independently re-verified. |
| 8 Scope Skills/agents to project | `8b5ea05a` | Present; not independently re-verified. |
| 9 Delete legacy framework code/routes | `4a3e5801` (partial) | ❌ **~30%.** Academy / automation / workflows / remote_access / realtime_agent modules removed + `tests/quality/test_removed_startup_core_surfaces.py` added. That test **FAILS**: 134 forbidden references across 69 active-source files. |
| 10 Documentation cutover + clean-baseline E2E | — | ❌ Not started. `docs/academy/` (525 files), `docs/archive/`, Founder Trial spec/plan still present. No `tests/e2e/test_startup_core_clean_baseline.py`. New design spec still `Status: Proposed for review`. |

## Core gap

The plan's self-review asserts *"no deletion task precedes the working replacement it would invalidate."* The committed reality violates this: Tasks 2–8 were merged as **additive layers on top of the retained Founder Trial framework**, so Task 9 is not leaf-file deletion — it is the clean-slate itself.

Concrete entanglements:

1. **Schema ↔ migration drift already exists.** `services/company/shared/db/schema/strategy.ts` defines **34** `strategySchema.table(...)` (stage_policies, gate_evaluations, venture_profiles, workspace_stage_transitions, project_stage_*, pmf_scoreboard_runs, maturity_assessments, canvases, workspace_strategy_settings, strategic_objectives, bsc_focus_scopes, pestel_signals, resource_capability_assessments, swot_items, tows_options, tows_option_evaluations, pilot_runs, next_best_actions, …). The committed baseline migration creates only **12** strategy tables. Code paths query tables the baseline never creates.
2. **Retained operating-loop services carry framework coupling.** `okr.service.ts` throws `"towsOptionId is required when strategicObjectiveId is provided"`; `initiative.service.ts` validates `sourceTowsOptionId` SELECTED status; `autonomy-classifier.ts` routes on `pestel.` / `swot.` / `tows.` capability prefixes.

## Change surface to finish Tasks 9–10

- `frontend/lib/modules/strategy/` — 84 files, + 26 strategy tests, + ~15 `hologram_hub` lens/stage files, + routing (`module_routes`, `app_routes`, `app_pages`), bindings, `vi_strategy.dart` / `en_strategy.dart` / `app_translations.dart` / `app_toast.dart`.
- `services/company/operations/strategy/` — 102 `.ts`; plus edits across the 157 non-strategy operations `.ts` (okr / initiative / twelve-week-year / task / autonomy-classifier / permission-catalog).
- `services/company` baseline migration + `shared/db/schema/{operations,strategy,index}.ts` + `deploy/schema/fingerprints.json` + `services/company/encore.gen/*` (regenerated).
- `apps/cosa` — 4 Python files (`capabilities/project_lifecycle.py`, agent specs / capability risk map).
- `services/cosa` — capability manifest tests.
- Docs — `docs/academy/` (525), `docs/archive/` (5), framework docs in `docs/{implementation,features,integrations,recipes}/`, README / CLAUDE / DEPLOYMENT, Founder Trial spec + plan.
- Gates to pass green: `make verify` (lint + typecheck + boundary + skillpacks + tenancy + contract-freeze + all backend/frontend suites) and `make e2e-cross-plane-smoke`.

This is a multi-session programme, not a single pass. It cannot land as one commit without leaving `main` unbuildable for concurrent sessions.

## Execution log

| Commit | Phase | Result |
|---|---|---|
| `d2a8bfe5` | — | this audit doc |
| `154aa71a` | A0 | fix `main` broken company typecheck (dangling `academy/contracts`) |
| `6fa586ae` | A1a | delete 65 framework strategy files (stage-gate / venture / TOWS / PESTEL / SWOT / PMF / maturity / strategy-analysis / strategy-copilot / founder-trial-board / old kickoff) + framework-coupled tests |
| `f61e199d` | A1b | delete canvas subsystem (11 files) |
| `9d1c347b` | A1c | decouple `decision-recording` / `okr` / `initiative` / `cycle-review` from gate-eval + TOWS + PESTEL |
| `90cadb1a` | A1c | drop pestel/swot/tows capability routing from `autonomy-classifier` |
| `26d2d4dc` | A1d | trim `workspace_strategy_settings` service/handler to operating-loop columns |
| `a40d49f6` | A1e | drop `strategy.analysis.write` / `strategy.option.select` permissions |
| `ba23dd95` | A1e | drop 19 framework tables from `strategy.ts` + baseline migration; regen fingerprint (`main`'s was already stale — Gate D failing before, passes now); `make test-db-reset` applies clean; `test_startup_core_schema.py` passes |
| `93ca2419` | (user) | plan/spec corrected: **Workspace W0-W5 / Project P0-P6 lifecycle is retained** — only BSC/PESTEL/SWOT/TOWS/Porter/maturity + framework stage-gate/scoreboard + auto-progression removed |
| `e40af06b` | B | drop framework `strategy.gate_evaluation.create` + `analytics.pmf_scoreboard.*` + `venture.stage.assess` (hardcoded readiness scorer) capabilities from `apps/cosa`; delete `product/outcome-roadmap` skillpack + framework acceptance tests |
| `ee0445e3` | 3 (corrected) | **rebuild clean lifecycle transitions**: `core.workspace_lifecycle_events` + `strategy.project_lifecycle_events` (append-only) + `transitionWorkspaceLifecycle` / `transitionProjectLifecycle` (CAS on `stage_version`, ≤1 step forward, backward needs rationale, founder/admin only, **no gate, no model, no auto**) + `PATCH /identity/workspaces/:id/lifecycle` + `PATCH /operations/projects/:id/lifecycle` + 10 green tests |

**Lifecycle audit result:** `projects.lifecycle_stage`/`stage_version`/`stage_entered_at` (operations.ts + migration) and workspace `lifecycle_stage`/`stage_version`/`stage_entered_at` (identity.ts + migration) with their CHECK enums were never removed by Phase A. `project-action-context.service.ts` still exposes lifecycle as agent context. The gate-coupled *transition* code removed in `6fa586ae` is replaced clean by `ee0445e3`.

Every commit: `npm run typecheck` + `make company-boundary-check` green; retained
operating-loop / integrity tests show only the pre-existing baseline schema-drift
failures (identical count before and after each change), no new regressions.

**Phase A backend clean-slate is complete and verified.** `services/company`
carries no `pestel/swot/tows/pmf-scoreboard/maturity-assessment` token outside
tests; the three test DBs re-migrate from the trimmed baseline; schema
fingerprint Gate D passes.

**Remaining (still multi-session):**
- Stage-roster removal — `task.service.listStageRosterService` +
  `task.handler.getStageRoster` + `apps/cosa` `/agent/workforce/stage-roster` +
  Flutter `hologram_hub`/`workforce` stage-roster widgets +
  `project_operating_setups` stage columns.
- `projects.lifecycle_stage / stage_version / stage_entered_at` — deeply wired
  into retained `project.service`, `project-operating-loop.service` (Task 3),
  `project-action-context.service`; not a removal-test token, deferred.
- Phase B — `apps/cosa/capabilities/project_lifecycle.py` PMF block +
  `services/cosa/tests/workspace-capability-manifest.test.ts` +
  `services/docker-compose.yml` realtime_agent.
- Phase C — Flutter `modules/strategy` (84) + `hologram_hub` framework
  (controller mixins `HubLensesMixin`/`HubGateMixin`/`HubStageMixin`/
  `HubTwelveWyMixin`, `strategy_navigation_panel`, `strategy_floating_action_bar`,
  `widgets/lenses/`), `data/models/strategy_lens_model.dart`,
  `vi_strategy.dart`/`en_strategy.dart`, routes.
- Phase D — `make mvp-contracts-gen` + `route-inventory` + make
  `test_removed_startup_core_surfaces.py` pass.
- Phase E (Task 10) — README/CLAUDE/DEPLOYMENT rewrite; delete `docs/academy`
  (525) + `docs/archive` + Founder Trial spec/plan; `tests/e2e/test_startup_core_clean_baseline.py`;
  `make verify` + `make e2e-cross-plane-smoke`.

## Final session state (2026-09-10)

| Phase | Status |
|---|---|
| **A** — Company backend clean-slate | ✅ done + verified (typecheck, boundary, test-db-reset, schema fingerprint Gate D) |
| **Lifecycle rebuild** (corrected scope) | ✅ done — `*_lifecycle_events` tables + `transition{Workspace,Project}Lifecycle` + 4 endpoints + 10 tests |
| **B** — apps/cosa | ✅ done — framework gate/pmf/venture-assess capabilities + `outcome-roadmap` skillpack removed |
| **C** — Flutter clean-slate | ✅ done — `modules/strategy` split (8 retained services kept, ~76 framework files deleted), `hologram_hub` framework mixins/widgets removed, `create_first_project_view` replaces the kickoff wizard, l10n framework keys purged. **`flutter analyze`: No issues found. `flutter test`: 703 passed.** |
| **D** — contracts + inventories + removal test | ✅ done — `test_removed_startup_core_surfaces.py` passes; route-inventory + company-usage-inventory + mvp-contracts + frontend-api-contract all regenerated & green |
| **E** — docs | ⚠️ partial — `docs/academy` (525) + `docs/archive` (5) deleted; CLAUDE.md source-of-truth updated (startup-core design, lifecycle retained); 27 dead code-links in history docs neutralized; `make check-docs` green; `make lint` unblocked. **Remaining: README/DEPLOYMENT rewrites, delete superseded Founder Trial spec/plan (many inbound refs), mark design spec ACCEPTED, `tests/e2e/test_startup_core_clean_baseline.py`.** |

### `make verify` blocker — pre-existing Task-2 debt, partially reduced

`make verify` fails at `tenancy-check` (= full `services/company` vitest). This is the **baseline schema/migration drift that predates this session**: the committed `001_cosa_startup_core_baseline` (Task 2) was curated down to a subset the Drizzle schema + tests still exceed. Progress this session:

- `0801c6a8` — `operations/migrations/002_restore_baseline_gaps.up.sql` restores 13 retained companion tables 001 omitted (okr_cycles, next_best_actions, pilot_runs, weekly_reviews, metric_contracts/snapshots, venture_profiles, discovery_signals, initiative_key_results, automation_*); `shared/db/schema/academy.ts` deleted (dead). `make test-db-reset` applies clean. **Full `services/company` vitest: 440 → 388 failed (+52 passing).**

**Still to do to reach green** (all Task-2 service-layer reconciliation, no plan re-scoping):
1. `operations/services/{project,task,execution-plan,project-link}.service.ts` + handlers still query the **M:N tables the clean-slate drops** — `strategy.portfolios`, `operating.task_projects`, `strategy.okr_objective_projects` — and `okr_objectives.cycle_id`. Rewrite them to the direct `tasks.project_id` / `okr_objectives.project_id` model (columns already present in `001`), then delete `portfolios`/`taskProjects`/`okrObjectiveProjects`/`portfolioProjects` from `shared/db/schema/operations.ts` and their tests (`composite-uniqueness.test.ts`, `task-stage-roster.test.ts`, portfolio assertions in `project.test.ts`).
2. Local dev `workspace` DB is polluted (173 tables, `node scripts/migrate.mjs` fails on it with `column "project_id" does not exist` because `001`'s content changed after it was first applied). Reset it — `make db-bootstrap` / drop+recreate the three dev DBs then `make dev-migrate` — so `make schema-fingerprint-check` (which introspects `WORKSPACE_MIGRATOR_DATABASE_URL` = dev, not the test DB) matches the golden. The golden itself must then be regenerated: the correct clean-baseline fingerprint is agent 21 / cosa 29 / workspace 150 tables (from `make test-db-reset` + `WORKSPACE_MIGRATOR_DATABASE_URL=$WORKSPACE_TEST_MIGRATOR_DATABASE_URL node scripts/schema-fingerprint.mjs --write`), vs the committed golden's 36/40/173 which came from the polluted dev DB.
3. Then `make verify` + `make e2e-cross-plane-smoke`; on green, bump the design spec from `ACCEPTED (implementation IN PROGRESS)` to `VERIFIED`.

### Session 2026-09-11 — steps 1 + 2 done; `make verify` still red (debt larger than estimated)

Commits on `main`: `50da7667` → `e7cd1967` → `3523439d`.

- **Step 1a — M:N link removal (`50da7667`).** Dropped `portfolios` /
  `portfolio_projects` / `task_projects` / `okr_objective_projects` from the
  Drizzle schema + the `projects`→`portfolios` composite FK (`projects.portfolio_id`
  kept as an inert bare column matching `001`). Deleted `project-link.service.ts`
  and its 7 `expose:true` endpoints (task↔projects, objective↔projects
  link/unlink/list) from `okr.handler` / `task.handler`; none were in
  `mvp-surface.json`, no frontend caller. Dropped portfolio CRUD +
  `/operations/portfolios`. `okr.service` / `task.service` now read the direct
  `project_id` column; `listStageRosterService` joins `tasks.project_id`
  directly (function + cross-plane `getStageRoster` endpoint kept per decision —
  `project_operating_setups` is retained in `001`); `execution-plan.service`
  no longer double-writes `task_projects`. Deleted `link-tables-schema.test.ts`,
  `project-link.test.ts`, `workspace-scoped-links.test.ts`; trimmed portfolio /
  M:N assertions from `project` / `okr` / `task` / `composite-uniqueness` /
  `task-stage-roster` tests. typecheck + `encore check` + `company-boundary-check`
  green.
- **Step 1b — test-fixture project seed (`e7cd1967`).** `createObjective` /
  `createTask` require a project in the workspace (design §156 — workspaces
  start empty, founder creates the first project). `makeAuthedWorkspace` /
  `makeCycle` in `okr.test` / `task.test` now seed a "Default Project" and
  return its id. `okr.test` "creates an objective under a cycle" no longer
  asserts `objective.cycleId` round-trips — the clean `okr_objectives` has **no
  `cycle_id` column**; `cycleId` is validated at create time but not persisted.
  `okr` + `task` + `task-stage-roster` + `project` test files: 42/42 green.
- **Step 2 — golden fingerprint regen + dev DB reset (`3523439d`).**
  `make test-db-reset`, then regenerated `deploy/schema/fingerprints.json` from
  the `*_TEST_MIGRATOR_DATABASE_URL`s → **agent 21 / cosa 29 / workspace 150**
  (was 36/40/173 from the polluted dev DB). Dropped + recreated + re-granted +
  re-migrated the three dev DBs (`agent` / `cosa` / `workspace`).
  `make schema-fingerprint-check` (Gate D) **green**.

**Update (same session, continued).** Task-2 reconciliation finished in batches
— full `services/company` vitest **388 → 0 failed (1281/1281)**; typecheck +
Gate D green. Commits after `3523439d`:

| Commit | Batch | Effect |
|---|---|---|
| `9476eb99` | regen `route-inventory.md` after the M:N endpoint removal | — |
| `b0bc4035` | **`commercial/002_restore_engagement_baseline`** — `001` omitted the whole `engagement.*` schema (Human Desk + copilot + channels + automation + autopilot); replays the 5 deleted pre-clean-slate migrations. `engagement` added to the fingerprint scope. | 328 → 161 |
| `b9aa837a` | seed a default `strategy.projects` (id == workspaceId) in `createTestWorkspaceWithMember` / `createSecondWorkspace` / `createTestSession` so direct-insert tests satisfy the composite `project_id` FK | 161 → 67 |
| `3b468b42` | **`identity/002_seed_permission_definitions`** (26 keys, `role_permissions` FK) + **`finance-legal/002_restore_legal_mvp_tables`** (`legal.legal_obligations` / `legal.legal_checklist_items`) | 67 → 52 |
| `6da9116b` | **`operations/003_restore_upsert_constraints`** — restore PK on `workspace_execution_settings` / `workspace_capability_policy` + plain `uix_weekly_plan_cycle_week`; the `ON CONFLICT` upserts were failing 42P10 | 52 → 16 |
| `68a3047e` | **`operations/004_restore_execution_plan_constraints`** (project FK + one-draft partial unique) + **`finance-legal/003_seed_tt58_nq86`** (regulation catalog, rule id=301) | 16 → 14 |
| `0bb44acd` | `createTaskService` requires an APPROVED initiative on a direct `initiativeId` link (was `requireApproved=false`) | behaviour |
| `b2ece707` | operations fixture reconciliation — `seedObjectiveWithKeyResult` (initiative needs a KR), one-ACTIVE-cycle-per-project in multi-cycle tests, stage-roster + executive-context "empty workspace" expectations | 14 → 1 |
| `e2df4c17` | **`finance-legal/004_correct_tt58_predicate`** — rule 301 predicate to `{"entity_status":"VERIFIED","accounting_regime":"TT58_2026"}` (migration-39 correction) | 1 → 0 |

Golden fingerprint after all migrations: **agent 21 / cosa 29 / workspace 181**.
Remaining before VERIFIED: `make verify` (all services + lint + boundary +
frontend) and `make e2e-cross-plane-smoke`, then bump the design spec.

## Phased execution (each phase = its own green commit + checkpoint)

- **Phase A — Company backend clean-slate.** Reconcile Drizzle schema ↔ baseline migration to the retained set; strip `tows` / `strategic_objective` / `stage` coupling from `okr` / `initiative` / `twelve-week-year` / `task` services + handlers + tests; delete framework services/handlers/tests (`stage-*`, `gate-evaluation`, `pmf-scoreboard`, `maturity-assessment`, `workspace-strategy-settings`, `strategic-objective`, `strategy-analysis`, `tows-option`, `strategy-copilot`, `venture-*`, `discovery-signal`, `founder-*`, `pilot-run`); fix `permission-catalog` + `autonomy-classifier`. Green: `cd services/company && npm run typecheck && npx vitest run` + `make company-boundary-check` + schema-fingerprint regen + `tests/db_baseline_candidate`.
- **Phase B — apps/cosa + services/cosa.** Remove framework capabilities/specs; fix capability manifest tests. Green: `make agent-test apps-cosa-test services-test-cosa`.
- **`main` Flutter baseline fixed** (`e109f3d7`): 14 orphan `test/`/`integration_test/` files for the academy/automation/workflows/remote_access modules deleted in `4a3e5801` were putting `flutter analyze` at 185 errors on `main`; deleted them → `flutter analyze` clean.
- **Phase C partial progress is in `git stash` `phase-c-wip-155to13-errors`** (not committed — it does not `flutter analyze` clean yet). It took the framework-file deletion + facade slim + hub-controller rewire from 155 → 13 remaining `lib/` errors. What it already does: deletes framework strategy services/controllers/views/widgets (keeps `strategy_service_base`/`strategy_mvp_client`/`project_service`/`okr_service`/`twelve_week_service`/`next_best_action_service`/`execution_plan_service`), slims `strategy_service.dart` facade to okr+twelve_week+project only, drops `HubStage/Lenses/Gate/TwelveWy` mixins + framework service fields from `hologram_hub_controller`, removes `ceoNextActions` from `hub_command_mixin`, trims `work_overview_controller`/`work_overview_tab` OKR-12WY summary to OKR-only, deletes framework `data/models`. **Still to do in that WIP** (13 `lib/` errors + test errors): gut the old project-kickoff / "first week actions" feature — `founder_command_center_controller` (`activeProjectSetup`, `needsProjectSetup`, `_applyFirstWeekActionOptimistically`, `toggleFirstWeekActionStatus`, `updateFirstWeekActionSchedule`, `_refreshActiveProjectSetup`), `hologram_hub_view.dart` (`_buildSetupIncompleteCard`, `_buildActiveOperatingSetupCard`, the setup Obx block), `top3_focus_widget.dart` (`FirstWeekActionDraft`); then `core/routing/{module_routes,app_pages}.dart` (strategy route + `WorkspaceModule.{strategy,okrs,twelveWy,projectRoadmap,projectFunding,templateLibrary}` entries + `project_setup_*` imports); localization framework keys; ~26 `test/**/strateg*` + hologram_hub framework tests. Recover with `git stash pop stash@{0}` (verify the stash name first — other sessions' stashes coexist).
- **Phase C — Flutter clean-slate.** ONE atomic change (interdependent — `flutter analyze` only goes green once everything below lands together).
  - ⚠️ **`modules/strategy` is NOT purely framework — do not bulk-delete it.** Verified by attempt: `lib/modules/hologram_hub` (retained `/hub` screen, via `HubCommandMixin` + `founder_command_center_controller`) imports `modules/strategy/services/strategy_service.dart` for `getCeoNextActions` / `getTwelveWeekCycles` / `getCycleTimeline` / `getProjects` / `createBasicProject`; `modules/tasks/controllers/work_overview_controller.dart` imports `twelve_wy_service.dart`; `core/routing` imports `project_setup_*`. Phase C must **split** `modules/strategy/services/` (~20 files): keep `strategy_service`, `strategy_service_base`, `strategy_mvp_client`, `project_service`, `okr_service`, `twelve_week_service`, `next_best_action_service`, `execution_plan_service` (retained); delete `strategy_lens_service`, `stage_gate_service`, `stage_service`, `pmf_scoreboard_service`, `portfolio_service`, `canvas_service`, `strategy_workflow_service`, `validation_service`, `twelve_wy_service`, `pilot_run_service`, `founder_service`, `project_operating_setup_service` (framework). Then rewire `hologram_hub_controller` to drop the 4 framework mixins (`hub_stage/lenses/gate/twelve_wy`) + 5 framework service fields but keep `strategyService` for `HubCommandMixin`. Delete `strategy/{controllers,views,widgets,bindings}/` framework surfaces, keeping whatever the retained routes need.
  - `frontend/test/**/strateg*` (26 files) — split the same way.
  - `frontend/lib/data/models/`: delete `pmf_scoreboard_model.dart`, `strategy_lens_model.dart`, `stage_gate_model.dart`, `validation_models.dart`; trim `tows` field from `twelve_wy_model.dart`.
  - `frontend/lib/modules/hologram_hub/` (107 files — the `/hub` screen + chat/voice host, NOT a framework module; wired into `core/session/session_controller.dart`, `core/shell/app_shell*.dart`, `core/routing/{app_pages,project_setup_guard_middleware}.dart`). Remove only the framework sub-features:
    - `widgets/lenses/`, `widgets/stage_gate/`, `widgets/twelve_wy/`, `widgets/stage_adaptive_domain_panel.dart`, `widgets/stage_policy_dialog.dart`, `widgets/stage_selector_header.dart`, `widgets/strategy_floating_action_bar.dart`, `widgets/strategy_navigation_panel.dart`, `widgets/project_validation_card.dart`, `views/widgets/stage_roster_panel.dart`, `views/widgets/stage_workforce_badge.dart`, `views/widgets/funding_readiness_card.dart`
    - `controllers/mixins/{hub_stage_mixin,hub_lenses_mixin,hub_gate_mixin,hub_twelve_wy_mixin}.dart`
    - `controllers/hologram_hub_controller.dart`: drop those 4 mixins + injected `StrategyService`/`StageService`/`StrategyLensService`/`StageGateService`/`TwelveWyService` fields/getters/ctor params + all call sites; keep Auth/Command/Chat/Voice/Evidence/ControlPlane.
    - matching `frontend/test/**/hologram*` framework tests (~part of 40).
  - Routing: `module_routes.dart` — drop `strategy` route + `WorkspaceModule.{strategy,okrs,twelveWy,projectRoadmap,projectFunding,templateLibrary}` enum entries + their index/planned-route maps (or leave as `_plannedRoute`). `app_pages.dart` — drop `project_setup_view`/`project_setup_controller` imports.
  - Stage-roster cross-plane: `services/company` `task.service.listStageRosterService` + `task.handler.getStageRoster` + `apps/cosa/api/workforce_routes.py` + `workforce_schemas.py` `WorkforceStageRoster*` + `project_operating_setups` stage columns.
  - Localization: `frontend/lib/core/localization/locales/{vi,en}/*_strategy.dart` — strip BSC/PESTEL/SWOT/TOWS/maturity/stage-gate keys; `app_translations.dart` `L10nKey` constants + list entries; `app_toast.dart` line 236 `'Đã thêm định hướng TOWS'`. Add `modules/projects` lifecycle-header keys.
  - NEW per corrected plan Task 5: `frontend/lib/modules/projects/services/project_lifecycle_service.dart` + `views/widgets/lifecycle_header.dart` (uses `PATCH /operations/projects/:id/lifecycle` + `GET .../lifecycle/events` from commit `ee0445e3`).
  - Green: `cd frontend && flutter analyze && flutter test`.
- **Phase D — Contracts + inventories + removal test.**
  - Add the 4 lifecycle endpoints from `ee0445e3` (`PATCH /identity/workspaces/:workspaceId/lifecycle`, `GET .../lifecycle/events`, `PATCH /operations/projects/:projectId/lifecycle`, `GET .../lifecycle/events`) to `shared/contracts/mvp-surface.json`.
  - `tests/quality/test_removed_startup_core_surfaces.py`: FORBIDDEN tokens should be `("bsc", "pestel", "swot", "tows", "porter", "maturity-assessment", "pmf-scoreboard", "realtime_agent", "academy", "automation")` — use the hyphenated `maturity-assessment`/`pmf-scoreboard`, NOT bare `maturity`/`pmf` (false-positive on `frontend/lib/modules/skills/services/tech_radar_service.dart` `maturity` field, `automation` substring in `auth_service`/session). Add the doc'd exemption that `lifecycle_stage`/lifecycle transition/lifecycle event references are retained.
  - `make mvp-contracts-gen route-inventory` → regenerate TS/Py/Dart.
  - Green: `pytest tests/quality/test_removed_startup_core_surfaces.py` + `make mvp-contracts-check route-inventory-check frontend-api-contract-check`.
- **Phase E — Task 10 docs + clean-baseline E2E.**
  - Rewrite `README.md` / `CLAUDE.md` / `DEPLOYMENT.md` / `services/README.md` / `frontend/README.md` — describe Startup Core loop + Workspace/Project lifecycle + retained companion domains.
  - `git rm -r docs/academy/` (525) + `docs/archive/` + framework docs under `docs/{implementation,features,integrations,recipes}/` + `docs/superpowers/specs/2026-09-09-founder-trial-mvp-reset-baseline-design.md` + `.../plans/2026-09-09-founder-trial-mvp-reset-baseline.md` (rewrite inbound links first).
  - Fix the 23 broken links `make check-docs` reports (all in `docs/architecture/overview/09-implementation-audit-2026-09-06.md` etc. → deleted `stage-lifecycle.service.ts` / `project-stage-lifecycle.service.ts` / `project-kickoff-materialize.service.ts` / `gate-evaluation.service.ts`).
  - Mark `docs/superpowers/specs/2026-09-10-cosa-startup-core-clean-slate-design.md` `ACCEPTED` after gates pass.
  - Create `tests/e2e/test_startup_core_clean_baseline.py`.
  - Green: `make check-docs verify` + `make e2e-cross-plane-smoke`.
