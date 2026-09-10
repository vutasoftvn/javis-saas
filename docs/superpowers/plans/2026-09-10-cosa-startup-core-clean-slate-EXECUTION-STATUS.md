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

Every commit: `npm run typecheck` + `make company-boundary-check` green; retained
operating-loop / integrity tests show only the pre-existing baseline schema-drift
failures (identical count before and after each change), no new regressions.

**Remaining A1:** `strategy.ts` schema table drops + `cycle_reviews.pestel_snapshots`
+ `projects.lifecycle_stage/stage_version` + baseline migration rewrite + fingerprint
regen; stage-roster removal (`task.service.listStageRosterService` +
`apps/cosa` `/agent/workforce/stage-roster` + Flutter `stage_roster_panel`);
`identity/services/permission-catalog.ts`.

## Phased execution (each phase = its own green commit + checkpoint)

- **Phase A — Company backend clean-slate.** Reconcile Drizzle schema ↔ baseline migration to the retained set; strip `tows` / `strategic_objective` / `stage` coupling from `okr` / `initiative` / `twelve-week-year` / `task` services + handlers + tests; delete framework services/handlers/tests (`stage-*`, `gate-evaluation`, `pmf-scoreboard`, `maturity-assessment`, `workspace-strategy-settings`, `strategic-objective`, `strategy-analysis`, `tows-option`, `strategy-copilot`, `venture-*`, `discovery-signal`, `founder-*`, `pilot-run`); fix `permission-catalog` + `autonomy-classifier`. Green: `cd services/company && npm run typecheck && npx vitest run` + `make company-boundary-check` + schema-fingerprint regen + `tests/db_baseline_candidate`.
- **Phase B — apps/cosa + services/cosa.** Remove framework capabilities/specs; fix capability manifest tests. Green: `make agent-test apps-cosa-test services-test-cosa`.
- **Phase C — Flutter clean-slate.** Delete `modules/strategy` framework surfaces + `hologram_hub` lenses + routes + bindings + localization; keep `modules/projects`. Green: `cd frontend && flutter analyze && flutter test`.
- **Phase D — Contracts + inventories + removal test.** `make mvp-contracts-gen route-inventory`; make `test_removed_startup_core_surfaces.py` pass (broaden token list to the plan's `bsc/pestel/swot/tows/porter/maturity/venture_stage/academy/realtime_agent/automation`). Green: `make mvp-contracts-check route-inventory-check frontend-api-contract-check`.
- **Phase E — Task 10 docs + clean-baseline E2E.** Rewrite README / CLAUDE / DEPLOYMENT; delete `docs/academy` + `docs/archive` + framework docs + Founder Trial spec/plan (rewriting inbound links); mark new spec `ACCEPTED`; add `tests/e2e/test_startup_core_clean_baseline.py`. Green: `make check-docs verify` + `make e2e-cross-plane-smoke`.
