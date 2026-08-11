# mCOSA V12 — Project & Portfolio Operating System Roadmap

## Status: implemented, all known gaps closed (audited 2026-08-11, closed same day)

`mCOSA_V12_Project_Portfolio_Operating_System_Implementation_Spec.md` (repo root) describes an
"operating layer" on top of V10 Hybrid Workforce: Project Intelligence, 12 Week Year,
Portfolio Intelligence, Next Best Action, and model routing (Terra / DeepSeek / Claude Code).

This document originally planned Sprint 1–10 as unimplemented future work. That premise turned
out to be stale: a 2026-08-11 audit found Sprints 1–9 already fully implemented on the backend
and mostly wired into Flutter, with Sprint 10 partially done (one broken endpoint, no
frontend). A follow-up pass the same day closed every item found by that audit: fixed the
broken endpoint, wired and seeded the 8 previously-dead feature flags, implemented the R1/R2
next-action ranking rounds, sharpened the Living PESTEL category matcher, built the Sprint 10
Flutter UI, wired `hologram_hub` to the CEO Next Actions endpoint, and updated `DEPLOYMENT.md`.
All 10 sprints are now DONE. See **Resolved items** below for what changed and **Remaining
items** for the few things deliberately left as product/architecture decisions rather than
code fixes.

This document is kept as: (1) the mapping table, a reference for where each V12 concept lives,
(2) a per-sprint **status** report, (3) the actual **API surface** and **feature flag** state,
and (4) a log of what was fixed and what's deliberately still open.

This is the sequel to the work tracked in `docs/architecture/MCOSA_UPDATE_ROADMAP.md`
(gap analysis against `mCOSA_Technology_Implementation_Blueprint_V10_Hybrid_Workforce.md`,
Phases 1–8).

---

## Organizing principles (as implemented)

These were the design constraints before Sprint 1; confirmed followed:

- **No new top-level modules** `app/projects/`, `app/cycles/`, `app/portfolios/`,
  `app/next_actions/` as drawn in spec §53. Everything lives in
  `backend/app/modules/strategy/`, split by file (`router.py`, `execution_router.py`,
  `portfolio_router.py`, `next_action_router.py`, `living_pestel_router.py`,
  `methodology_router.py` — all mounted under `/api/v1/strategy` in `main.py`). No
  `backend/app/modules/portfolios/` or `backend/app/modules/ceo/` directory exists.
  Exception followed as planned: **Model Gateway** logical routing lives in
  `backend/app/modules/chat/model_profiles.py` (`resolve_profile`, `list_profile_mappings` for
  `STRATEGIC_ANALYZER`/`CONVERSATION_ROUTER`/`DEVELOPER_WORKER`) — no separate `model_gateway/`
  package. This file has **no HTTP endpoint** of its own; the Sprint 10 `/model-profiles` admin
  routes in `living_pestel_router.py` are a separate, workspace-scoped admin-override layer on
  top of it (`ModelProfileOverride` table, see below) — not a duplicate of the routing logic.
- **No duplicate-concept tables.** Portfolio SWOT/TOWS/PESTEL reuse
  `swot_items`/`tows_options`/`pestel_items` via a nullable `portfolio_id` column rather than
  new tables, exactly as planned.
- **Feature flags**: implemented at `backend/app/core/feature_flags.py`
  (`is_enabled(db, key, workspace_id=None)`, `require_flag`, `set_feature_flag`,
  `list_feature_flags`) backed by table `feature_flags` (model `FeatureFlag` in
  `backend/app/modules/platform/models.py`, not in `strategy/`). One table, one function, no
  LaunchDarkly/GrowthBook — as planned. All 14 defined flag keys are now seeded and enforced
  (see flag table below).
- **Planning Compiler (spec §52)**: no new `WorkItem` entity.
  `planning_compiler_service.py::PlanningCompilerService.compile_cycle(cycle_id)` generates
  `Task` rows from `WeeklyCommitment` and skeleton `Outcome` rows from
  `Milestone.required_artifacts`, and enforces "no `Task` before cycle activation" (HTTP 422 if
  `cycle.status != "active"`) — the load-bearing invariant from spec §11, covered by
  `test_planning_compiler.py`.
- **Tenancy**: every new table carries `workspace_id`; portfolio ACL is enforced and covered by
  `test_portfolio_service.py::test_portfolio_acl_zero_trust_cross_tenant` (spec §57, §62.8).

---

## Mapping: V12 spec concept → backend reality (current)

| Spec (§51 suggested entities) | Status | Location |
|---|---|---|
| `project` classification fields | **Implemented** | `strategy.Project` + `project_type`/`strategic_priority`/`founder_attention_budget`/`portfolio_id` columns (`v12_001`) |
| `project_classifications` | **Implemented** | `strategy.ProjectClassification`, `project_classifier_service.py` |
| `methodology_plans` | **Implemented** | `strategy.MethodologyPlan`, `methodology_router.py` (`MethodologyRouterService` — no HTTP routes of its own, consumed by `router.py`) |
| `strategic_analysis_versions` | **Implemented** (reused, as planned) | `StrategyAnalysis` + `StrategyRevision`, unchanged |
| `evidence_items` | **Implemented** (reused, as planned) | `EvidenceItem`, unchanged |
| `strategy_links` | **Implemented** (reused, as planned) | `OkrLink` (polymorphic `from/to_entity_type/id`) |
| `cycles` (12WY) | **Implemented** | `TwelveWeekCycle` + `cycle_contract_id` |
| `cycle_contracts` | **Implemented** | `strategy.CycleContract` |
| `cycle_stages` | **Implemented** | `strategy.CycleStage`; `WeeklyPlan.stage_id`; CRUD + `/generate-standard` in `execution_router.py` |
| `milestones`, `milestone_evidence` | **Implemented** | `strategy.Milestone` (incl. `required_artifacts`), `strategy.MilestoneEvidence` |
| `gate_decisions` | **Implemented** | `strategy.GateDecision`, CRUD in `execution_router.py` |
| `weekly_missions` | **Implemented** | `WeeklyPlan.mission`/`success_criteria`; `WeeklyCommitment.commitment_owner_type`/`execution_mode` |
| `weekly_reviews`, `weekly_scores` | **Implemented** | `WeeklyPlan.outcome_score`; `strategy.WeeklyReview`, `review_service.py` |
| `cycle_reviews`, `celebration_records` | **Implemented** | `strategy.CycleReview`, `strategy.CelebrationRecord`; Week 13 endpoints in `execution_router.py` |
| `portfolios`, `portfolio_projects` | **Implemented** | `strategy.Portfolio`, `strategy.PortfolioProject`; `portfolio_router.py`, `portfolio_service.py` |
| `portfolio_analysis_versions`, `portfolio_pestel_signals`, `project_pestel_impacts`, `portfolio_swot_items`, `portfolio_tows_items` | **Implemented** (reused, as planned) | nullable `portfolio_id` on `strategy_analyses`/`pestel_items`/`swot_items`/`tows_options`; `strategy.ProjectPestelImpact` |
| `portfolio_synergies`, `portfolio_dependencies` | **Implemented** | `strategy.PortfolioSynergy`, `strategy.PortfolioDependency`, `portfolio_advanced_service.py` |
| `portfolio_options` | **Implemented** | `strategy.PortfolioOption` |
| `capacity_allocations`, `founder_attention_allocations` | **Implemented** | `strategy.CapacityAllocation`, `strategy.FounderAttentionAllocation` |
| `portfolio_cycles`, `portfolio_weekly_reviews` | **Implemented** (portfolio_cycles only) | `strategy.PortfolioCycle`, `portfolio_cycle_service.py`; no separate `portfolio_weekly_reviews` table was needed |
| `founder_profiles` | **Implemented** | `strategy.FounderProfile`; `max_active_strategic_projects` enforced at cycle activation (spec §31 WIP limit) |
| `next_action_candidates`, `next_action_rankings` | **Implemented** | `strategy.NextActionCandidate`, `strategy.NextActionRanking`; `next_best_action_service.py` — full R0→R1→R2 pipeline (spec §37) |
| `model_profiles`, `model_runs`, `analysis_imports` | **Implemented** | `chat/model_profiles.py` (logical routing, no HTTP) + `strategy.ModelProfileOverride` (workspace admin override, backs `PUT /model-profiles/{id}`); `strategy.ModelRunAudit`; `strategy.AnalysisImport`, `assisted_analyzer.py` |
| Outcome/WorkItem/Worker/Run/Artifact (V10 runtime) | **Unchanged, as planned** | `outcomes` module + `tasks.Task`; Planning Compiler generates rows, no new entity |

---

## Status by sprint

All 10 sprints are DONE. Sprints 6–10 required a same-day follow-up fix (flag enforcement,
broken endpoint, R1/R2 ranking, frontend) noted per sprint below.

### Sprint 1 — Domain contracts + migrations (V12.0): DONE
Feature flag mechanism; migration `v12_001_sprint1_domain_schema.py` creates
`project_classifications`, `methodology_plans`, `cycle_contracts`, `cycle_stages`,
`milestones`, `milestone_evidence`, `gate_decisions`, `feature_flags`, plus columns on
`projects`/`twelve_week_cycles`/`weekly_plans`. Flags `project_classifier_v12`,
`cycle_13week_v12`, `milestones_gates_v12` — seeded **true**, enforced.

### Sprint 2 — Single Project Journey (V12.1): DONE
`POST /api/v1/strategy/projects/{id}/classify`, `GET/POST .../methodology`,
`POST /api/v1/strategy/analysis/export`, `POST .../analysis/import` (writes
`analysis_imports`, creates a `StrategyRevision`) — all in `router.py`. Flags
`methodology_router_v12`, `assisted_terra_v12` — seeded **true**, enforced.

### Sprint 3 — 12WY + Milestone + Weekly Mission (V12.1 continued): DONE
`cycle_stages`/`milestones`/`gate_decisions` CRUD in `execution_router.py`; `weekly_plans`
mission/success_criteria; `commitment_owner_type` on `weekly_commitments`. Flag
`weekly_missions_v12` — seeded **true**, enforced.

### Sprint 4 — Planning Compiler → V10 runtime (V12.2): DONE
`planning_compiler_service.py::compile_cycle(cycle_id)`; idempotent `Task` creation from
`WeeklyCommitment`; skeleton `Outcome` from `Milestone.required_artifacts`; activation gate
enforced and tested (`test_planning_compiler.py`, 5/5 passing). No flag — gated by
`cycle.status`, as designed.

### Sprint 5 — Weekly Review + Week 13 (V12.3): DONE
`weekly_reviews`, `cycle_reviews`, `celebration_records` tables; `review_service.py`;
`POST /execution/twelve-week-cycles/{id}/weekly-reviews`,
`POST .../week13/finalize` (+ `/week13/review`, `/week13/celebration`, `/week13/readiness`).
Unlike Sprints 1–3, no `require_flag` gates these endpoints — they are always on (unchanged,
not treated as a gap: Week 13 is meant to be mandatory per spec §62.10).

### Sprint 6 — Portfolio Intelligence: Detector + Shared PESTEL + Impact Matrix (V12.4): DONE
`portfolios`, `portfolio_projects` tables; rule-based `PortfolioDetectorService.detect()`
(triggers at ≥2 active strategic projects); nullable `portfolio_id` reused on
`strategy_analyses`/`pestel_items`; `project_pestel_impacts`. ACL test passing
(`test_portfolio_acl_zero_trust_cross_tenant`). **Fixed 2026-08-11**: `portfolio_v12` and
`shared_pestel_v12` are now seeded true (migration `v12_011_flags2`) and every endpoint in
`portfolio_router.py`'s detector/CRUD/pestel/impact-matrix sections calls `require_flag`.

### Sprint 7 — Portfolio SWOT/TOWS + Options + Capacity (V12.5 part 1): DONE
`portfolio_synergies`, `portfolio_dependencies`, `portfolio_options`; `portfolio_id` reused on
`swot_items`/`tows_options`; `portfolio_advanced_service.py`. **Fixed 2026-08-11**:
`portfolio_swot_tows_v12` seeded true and enforced on all SWOT/TOWS/synergies/dependencies/
options endpoints.

### Sprint 8 — Portfolio 12WY + WIP + Founder Attention (V12.5 part 2): DONE
`capacity_allocations`, `founder_attention_allocations`, `founder_profiles`,
`portfolio_cycles`; WIP limit (`max_active_strategic_projects`, default 3) enforced at
`portfolio_cycle_service.py::activate_portfolio_cycle`, citing "§31 WIP Limit" on rejection.
**Fixed 2026-08-11**: `capacity_planner_v12`, `founder_attention_v12`, `portfolio_cycle_v12`
seeded true and enforced on founder-profile/cycles/allocations endpoints.

### Sprint 9 — Next Best Action (V12.6): DONE
`next_action_candidates`, `next_action_rankings`; `next_best_action_service.py`. Endpoint
`GET /api/v1/strategy/ceo/next-actions` (real path — differs from the original spec draft's
`/api/v1/ceo/next-actions`). **Fixed 2026-08-11**: full R0→R1→R2 pipeline now implemented
(`evaluate_and_rank`):
- **R0** — unchanged deterministic weighted formula.
- **R1** (`_apply_r1_rules`) — transparent rule bonuses on top of R0: +0.05 for candidates
  whose project unblocks a `PortfolioDependency` successor ("Dependency Unlock", spec §37),
  +0.03 for `STAGE_GATE_REVIEW`/`GOVERNANCE_DECISION` category. Fully deterministic, no AI.
- **R2** (`_maybe_ai_rerank` / `_call_ai_rerank`) — best-effort AI rerank of the top-5
  shortlist via the `STRATEGIC_ANALYZER` logical profile (spec §40). Skips cleanly if the
  provider isn't configured; on any provider error or malformed JSON response it falls back to
  the R1 order — R2 can only reorder the R1 shortlist, never produce a worse or broken result.
  Each call is logged to `ModelRunAudit`. Covered by 5 new tests including a fake
  `ChatProvider` exercising success, malformed-output, and provider-failure paths.
`next_best_action_v12` flag seeded true and enforced.

### Sprint 10 — Hologram/Mobile CEO surfaces + hardening + Living PESTEL (V12.7): DONE
`pestel_signals`, `model_runs_audit` tables; `living_pestel_service.py::ingest_signal`
implements the material-change flow (spec §48) — HIGH/CRITICAL magnitude signals auto-create a
`NextActionCandidate` "CEO Exception" row. **Fixed 2026-08-11**:
- **Broken endpoint fixed**: `GET /model-profiles` no longer imports the nonexistent
  `app.modules.strategy.model_profile_service`; it now calls
  `LivingPestelService.list_model_profiles()`, which merges `chat/model_profiles.py`'s live
  provider/model resolution with a per-workspace `ModelProfileOverride` row.
- **Stub fixed**: `PUT /model-profiles/{id}` now persists `display_name`/`temperature`/
  `is_active` to the new `model_profile_overrides` table (migration `v12_011_flags2`) via
  `LivingPestelService.update_model_profile()`.
- **Material-change matcher sharpened**: `ingest_signal` now joins `ProjectPestelImpact` to
  `PestelItem` and filters by `PestelItem.factor == pestel_category`, so a signal only creates
  CEO Exceptions for impacts in the same PESTEL category — previously it matched every
  `NEGATIVE` impact in the workspace regardless of category.
- **New flag**: `living_pestel_v12`, seeded true, enforced on all four
  `living_pestel_router.py` endpoints.
- **Frontend built**: "Living PESTEL & AI" dialog in `projects_tab.dart` (ingest signal form,
  PESTEL signal list, model profile list with an edit dialog for display name/temperature/
  active toggle, model run audit list) plus matching `strategy_service.dart` client methods
  and `strategy_controller.dart` state/actions.
- **Hologram wired**: `HologramHubController` now loads `GET /ceo/next-actions` (top 3) on
  init and on its existing 60s refresh timer; a new `NextActionsPanel` widget renders them in
  both the wide and narrow `hologram_hub_view.dart` layouts, with a "MỞ CEO BRIEF ĐẦY ĐỦ" link
  that opens the Strategy tab (`openDashboard(3, 2)`).

---

## Frontend status

Sprint 1–9 UI is bolted onto the existing tabs rather than split into new modules —
`frontend/lib/modules/strategy/views/tabs/projects_tab.dart` has classify/methodology menu
actions, a Gate dropdown, a CEO Next-Actions banner, a Portfolio Intelligence detector banner,
a large `_showPortfoliosDialog` (portfolio CRUD, Shared PESTEL, Impact Matrix, SWOT/TOWS,
Synergies, Dependencies, Options, Founder WIP, Portfolio 12WY Cycles), and now a
`_showLivingPestelDialog` (Sprint 10: PESTEL signals, model profiles, model run audit).
`okrs_tab.dart` has Cycle Stages/Gate Decisions display, a Weekly Mission banner/dialog, a
Weekly Review dialog, and a full Week 13 dialog. `data/services/strategy_service.dart` has Dart
client methods for the entire Sprint 1–10 API surface.

**Module-split decision (architecture decision #4, resolved 2026-08-11)**: the original plan
called for new `modules/portfolios/` and `modules/ceo/` Flutter modules. Decided to keep the
single-tab-dialog pattern instead of refactoring: the existing pattern is functionally
complete, consistently applied through Sprint 10, and a retroactive module split would be a
pure refactor with no behavior change — better done later if/when one of these areas grows
complex enough on its own to justify a dedicated module (e.g. if Portfolio gets its own nav
entry), not preemptively.

`hologram_hub` now shows a Top-3 CEO Next Actions panel (see Sprint 10 above); it does not yet
surface PESTEL signals or model run audits (those remain Strategy-tab-only, consistent with
being founder/admin configuration rather than a CEO Brief glance-item).

---

## API surface (actual, as implemented)

All mounted under `/api/v1/strategy` in `backend/app/main.py`, except `okrs`/`execution` which
keep their own prefixes. This replaces the original draft's incorrect `/api/v1/portfolios` and
`/api/v1/ceo` prefixes — no such routers exist; portfolio and CEO endpoints live under
`/api/v1/strategy/...`.

```
# router.py — prefix /api/v1/strategy
GET/POST  /projects
POST      /projects/{id}/classify
GET/POST  /projects/{id}/methodology
POST      /analysis/export
POST      /analysis/import
GET/POST  /initiatives
PUT/DELETE /initiatives/{id}
  + canvas_router.py: /scorecards, /objectives, /canvases, /revisions/...
  + evidence_router.py: /context-packs, /evidence
  + analysis_router.py: /analyses/pestel|swot|tows, /analyses/prompt-template,
                         /analyses/generate-ai, /decisions

# portfolio_router.py — prefix /api/v1/strategy
GET       /portfolios/detect
GET/POST  /portfolios
GET/PUT/DELETE /portfolios/{id}
GET/POST  /portfolios/{id}/projects
DELETE    /portfolios/{id}/projects/{project_id}
GET/POST  /portfolios/{id}/pestel
GET       /portfolios/{id}/impact-matrix
POST      /projects/{id}/pestel-impacts
GET/POST  /portfolios/{id}/swot
GET/POST  /portfolios/{id}/tows
GET/POST  /portfolios/{id}/synergies
DELETE    /portfolios/{id}/synergies/{id}
GET/POST  /portfolios/{id}/dependencies
DELETE    /portfolios/{id}/dependencies/{id}
GET/POST  /portfolios/{id}/options
PUT       /portfolios/{id}/options/{id}
GET/PUT   /founder-profile
GET/POST  /portfolios/{id}/cycles
POST      /portfolio-cycles/{id}/activate
GET       /portfolio-cycles/{id}/allocations
POST      /portfolio-cycles/{id}/allocations/capacity
POST      /portfolio-cycles/{id}/allocations/founder-attention

# next_action_router.py — prefix /api/v1/strategy
GET       /ceo/next-actions          (full path: /api/v1/strategy/ceo/next-actions)
POST      /ceo/next-actions/evaluate
PUT       /ceo/next-actions/{id}/status

# living_pestel_router.py — prefix /api/v1/strategy
POST/GET  /pestel-signals
GET/POST  /model-runs/audit
GET       /model-profiles            (fixed 2026-08-11 — was broken, now works)
PUT       /model-profiles/{id}       (fixed 2026-08-11 — was a no-op stub, now persists)

# execution_router.py — prefix /api/v1/execution
GET/POST  /twelve-week-cycles
GET/POST  /weekly-plans
PUT       /weekly-plans/{id}
GET/POST  /weekly-commitments
PUT/DELETE /weekly-commitments/{id}
GET/POST  /twelve-week-cycles/{id}/stages
POST      /twelve-week-cycles/{id}/stages/generate-standard
PUT/DELETE /stages/{id}
GET/POST  /milestones
PUT/DELETE /milestones/{id}
POST/DELETE /milestones/{id}/evidence[/{evidence_id}]
GET/POST  /gate-decisions
GET/POST  /twelve-week-cycles/{id}/contract
PUT       /weekly-plans/{id}/mission
POST      /twelve-week-cycles/{id}/compile
POST      /weekly-plans/{id}/compile
GET       /twelve-week-cycles/{id}/compilation-status
POST/GET  /twelve-week-cycles/{id}/weekly-reviews
GET       /weekly-plans/{id}/review
POST      /twelve-week-cycles/{id}/week13/finalize
GET       /twelve-week-cycles/{id}/week13/review
GET       /twelve-week-cycles/{id}/week13/celebration
GET       /twelve-week-cycles/{id}/week13/readiness

# chat/model_profiles.py — no HTTP endpoint (internal provider-resolution library only)
```

---

## Feature flags (actual state)

All 14 flag keys are seeded globally true and enforced via `require_flag` on their endpoints.

| Flag key | Seeded | Enforced | Migration |
|---|---|---|---|
| `project_classifier_v12` | true | yes | `v12_010_flags` |
| `cycle_13week_v12` | true | yes | `v12_010_flags` |
| `milestones_gates_v12` | true | yes | `v12_010_flags` |
| `methodology_router_v12` | true | yes | `v12_010_flags` |
| `assisted_terra_v12` | true | yes | `v12_010_flags` |
| `weekly_missions_v12` | true | yes | `v12_010_flags` |
| `portfolio_v12` | true | yes | `v12_011_flags2` |
| `shared_pestel_v12` | true | yes | `v12_011_flags2` |
| `portfolio_swot_tows_v12` | true | yes | `v12_011_flags2` |
| `capacity_planner_v12` | true | yes | `v12_011_flags2` |
| `founder_attention_v12` | true | yes | `v12_011_flags2` |
| `portfolio_cycle_v12` | true | yes | `v12_011_flags2` |
| `next_best_action_v12` | true | yes | `v12_011_flags2` |
| `living_pestel_v12` | true | yes | `v12_011_flags2` |

No admin HTTP endpoint exposes `list_feature_flags`/`set_feature_flag` — flags are only
managed via migration seed rows or direct DB access (`app.core.feature_flags.set_feature_flag`
from a script/shell, e.g. to disable a flag for one workspace without affecting the global
default). This was a deliberate minimalism call, not an oversight — see Remaining items.

---

## Resolved items (fixed 2026-08-11, same day as the audit)

1. ~~Fix broken `GET /model-profiles` endpoint~~ — fixed; now backed by
   `LivingPestelService.list_model_profiles()`.
2. ~~Implement the `PUT /model-profiles/{id}` stub~~ — fixed; persists to
   `model_profile_overrides` (new table, migration `v12_011_flags2`).
3. ~~Decide on the 7 unenforced flags~~ — decided: wired `require_flag` into all affected
   endpoints and seeded them true (migration `v12_011_flags2`), matching the Sprint 1–3
   pattern, rather than deleting the constants. Endpoints keep working exactly as before for
   existing deployments (flags default enabled); the flags now do real gating work if anyone
   chooses to disable one per-workspace going forward.
4. ~~Implement R1 (rules) and R2 (AI/Terra rerank) next-action ranking~~ — implemented; see
   Sprint 9 status above.
5. ~~Add a feature flag for Sprint 10~~ — added `living_pestel_v12`, seeded true, enforced.
6. ~~Build Sprint 10 frontend~~ — built; see Frontend status above.
7. ~~Wire `hologram_hub` to `GET /ceo/next-actions`~~ — wired; see Sprint 10 status above.
8. ~~Sharpen the Living PESTEL material-change matcher~~ — fixed; now filters by PESTEL
   category via a join to `PestelItem`.
9. ~~Frontend module-split decision~~ — decided: keep the existing single-tab-dialog pattern
   (see Frontend status above for rationale).
10. ~~Add test coverage for `GET`/`PUT /model-profiles`~~ — added as direct router-call unit
    tests (`test_get_model_profiles_endpoint_does_not_import_missing_module`,
    `test_update_model_profile_endpoint_persists` in `test_living_pestel_service.py`), matching
    this repo's established convention of calling router functions directly with a mocked
    `Session` rather than a FastAPI `TestClient` (see `test_strategy_canvas.py`'s documented
    reasoning: no real test-DB infra exists yet for this module). This is what actually would
    have caught the original bug — the gap was that no test called the endpoint function at
    all, not that it needed to go through real HTTP.
11. ~~Update `DEPLOYMENT.md`~~ — added a section documenting the `v12_001`–`v12_011` migration
    chain and the flag-seeding requirement.

---

## Remaining items (deliberate, not bugs)

- **No HTTP admin endpoint for feature flags.** `set_feature_flag`/`list_feature_flags` exist
  in `app.core.feature_flags` but aren't exposed over `/api/v1`. Per this repo's minimalism
  principle ("one table, one function, no LaunchDarkly/GrowthBook"), and because no workspace
  has needed to override a V12 flag yet, this stays script/shell-only until there's an actual
  need. Revisit if a workspace needs a flag disabled without a deploy.
- **`hologram_hub` shows only Next Actions, not PESTEL signals or model run audits.** Judged
  correct: those are founder/admin configuration surfaces, not CEO-Brief-glance material — spec
  §50's mobile CEO surface is about Next Actions/Approvals/Gate Decisions, not raw signal feeds.

---

## Verification

Confirmed working as of 2026-08-11 (run from `backend/`, using the project's `.venv`):

```
.venv/bin/python -m pytest app/tests -q
→ 284 passed, ~7-9s
```

284 = the 276 passing before the 2026-08-11 fixes + 8 new tests (2 model-profiles endpoint
regression tests, 1 PESTEL category-filter test, 5 R1/R2 next-action ranking tests).

`alembic heads` → single head `v12_011_flags2`, no branch conflicts.

Flutter: `flutter analyze` (both scoped to the changed files and the full project) →
**No issues found**. Runtime-boundary check
(`rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib`) →
no matches, boundary holds. No Flutter unit tests exist yet for `strategy`/`hologram_hub`
modules (none existed before this pass either) — `flutter analyze` is the available signal;
manual/visual verification in a running app was not performed as part of this pass.

## Non-goals (per spec §61 and this repo's `CLAUDE.md`)

Do not build: a methodology marketplace, an autonomous CEO, automated
contract-signing/payment, a complex mathematical portfolio optimizer, a graph-DB migration, a
second agent framework, a Claude/ChatGPT credential proxy, automated consumer ChatGPT
sessions, or a task/run system parallel to the existing `outcomes`/`tasks` modules.
