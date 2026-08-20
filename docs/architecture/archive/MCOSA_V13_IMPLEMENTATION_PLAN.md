# mCOSA V13 — Focused Company Cycle OS: Migration Plan

> Source spec: `mCOSA_V13_Focused_Company_Cycle_OS_Claude_Code_Implementation.md` (repo root).
> This plan was produced by auditing the actual codebase against that spec on 2026-08-13
> and is the authoritative execution plan for V13 work — track phase completion here the
> same way `MCOSA_V12_ROADMAP.md` tracks V12 sprints.
>
> **Post-implementation audit (2026-08-13):** a second, independent pass re-read the shipped
> code for every phase and re-ran the test suites. No separate "V13 handoff" document exists
> anywhere in the repo — that phrase in the original Phase Tracking table was aspirational,
> not a real artifact. This file now *is* that record: see the corrected **Phase Tracking**
> table and the **Known Gaps** section at the bottom for what actually shipped vs. what this
> plan originally promised.

## Context

`mCOSA_V13_Focused_Company_Cycle_OS_Claude_Code_Implementation.md` (repo root) is a
~2270-line product-scope specification that re-focuses the product around one loop:
**Cycle → OKRs → 12 Week Year → Weekly Mission → Execution (5 AI Functions) → Weekly
Review → Learning → Week 13 → Next Cycle**, while explicitly requiring V12 advanced
modules to be *hidden, not deleted* (feature flags, not destructive cleanup), and adding
a brand-new Finance/accounting Function for Vietnamese micro-enterprises under Circular
58/2026/TT-BTC (TT58).

Before writing this plan, three parallel codebase surveys (backend, frontend, docs/ADRs)
and a grounded design pass were run against the actual repo. The single most important
finding: **this spec is not a greenfield build.** Roughly 80% of the Cycle/OKR/12WY/Weekly
Mission/Weekly Review/Week13 domain the spec describes already exists in
`backend/app/modules/strategy/` and `frontend/lib/modules/strategy/views/tabs/okrs_tab.dart`
under different names, and the V10 Hybrid Workforce execution engine
(`modules/outcomes/`, `modules/tasks/`, `modules/organization/`, and — critically —
`modules/devices/DeveloperJob`, which is *already* the "Tech WorkItem → Claude Code
Worker → worktree → tests → artifact → approval" pipeline spec §19 asks for) is fully
built. Treating this as a rebuild would violate the repo's own CLAUDE.md rule ("never
create a second execution engine") and waste the majority of the effort.

The real gaps are: no generic cross-Function `Lesson` entity, only the Marketing AI
Function exists (Legal/Sales/Tech/Finance don't), the entire Finance/TT58 accounting
domain is greenfield, there's no formalized AI tool registry, no Flutter-side feature-flag
consumption, and the frontend's `OutcomesService` (Outcome/Run/Artifact data layer) is
built but never wired into any view — so there is currently no "AI Team" UI at all despite
the backend supporting it.

This plan therefore reframes the spec's "build" language as **reuse + additive schema +
flag-gated hide + four new thin Function modules + one genuinely new Finance domain**,
in that order of effort, so the founder gets the flag/nav/hide payoff early and the
Finance/TT58 build (the biggest, riskiest piece) is properly deterministic and
test-gated before being marked production-ready.

Full V13 scope is in play (all phases below, not just flags), including writing the 14
required ADRs (ADR-V13-001..006, ADR-FIN-001..008).

---

## Domain Mapping — What Already Exists vs What's New

Confirmed directly by reading `backend/app/modules/strategy/models.py` (verified: `OkrCycle`,
`OkrObjective`, `KeyResult`, `OkrLink`, `Initiative`, `InitiativeKeyResultLink`,
`TwelveWeekCycle`, `WeeklyPlan`, `WeeklyCommitment`, `CycleContract`, `CycleStage`,
`Milestone`, `MilestoneEvidence`, `GateDecision`, `WeeklyReview`, `CycleReview`,
`CelebrationRecord`, plus Portfolio/PESTEL/SWOT/TOWS/Capacity/FounderAttention entities
all present exactly as listed):

| V13 spec concept | Existing model | Verdict |
|---|---|---|
| `cycle` (founder-facing) | `TwelveWeekCycle` joined 1:1 with `CycleContract` | Reuse as a **read-composed view**, not a new table. `OkrCycle` stays the underlying OKR-period container `TwelveWeekCycle.okr_cycle_id` points to. |
| `objective` | `OkrObjective` | Reuse. Add nullable `why` (Text); compute `progress` at read-time from KRs (don't store a second source of truth). |
| `key_result` | `KeyResult` | Reuse. Add nullable `metric_type` (String), `evidence_refs` (JSONB). |
| `12WY Plan` | `TwelveWeekCycle` | No gap. |
| `weekly_mission` | `WeeklyPlan` (+ `WeeklyCommitment` for founder/AI work split via existing `commitment_owner_type` enum) | Reuse. `linked_kr_ids[]` reuses the existing generic `OkrLink` table (`from_entity_type/id → to_entity_type/id`) instead of a new JSONB array. |
| `WorkItems` | `Task` (execution_mode, assignee/owner) + `Outcome`/`OutcomeRun`/`RunStep`/`RunEvent`/`Artifact` | Reuse (CLAUDE.md: no second execution engine). Add nullable `Task.function`, `Outcome.function`, `Outcome.cycle_id`. KR traceability already exists via `Task.weekly_commitment_id → WeeklyCommitment.initiative_id → Initiative → InitiativeKeyResultLink → KeyResult` — do not re-add FK columns for this chain. |
| `weekly_review` | `WeeklyReview` | No schema change. "Function Results"/"Finance Status" sections are computed at read-time by joining `Task.function`/`Outcome.function` + the new Finance snapshot table. |
| `week13` | `CycleReview` + `CelebrationRecord` | No schema change. Week 13 Finance Review section computed at read-time, same principle. |
| `lesson` | **Does not exist** (only `MarketingLearning`) | New — see Phase 2. |
| 5 AI Functions | Only Marketing fully built | New Legal/Sales/Tech/Finance — see Phases 3 & 5. Tech's executor (`DeveloperJob` in `modules/devices/models.py`, confirmed: `required_capabilities` incl. `claude_code`/`git`, `worktree_path`, `diff_summary`, `test_results`, status flow QUEUED→CLAIMED→RUNNING→WAITING_APPROVAL→SUCCEEDED) **already implements spec §19 end-to-end** — Tech Function work is a thin status/routing layer only, not a new pipeline. |
| `function_status` | Does not exist | Compute on read (join Task/Outcome/Artifact/Lesson by `function`); don't build a physical table for MVP. |

Feature flags already exist as real infra: `backend/app/core/feature_flags.py` (confirmed:
`is_enabled`/`require_flag`/`set_feature_flag`/`list_feature_flags`, DB-backed via
`FeatureFlag` in `modules/platform/models.py`, workspace-override + global-fallback) with
V12 constants already covering most of what spec §5 wants hidden: `FLAG_PORTFOLIO_V12`,
`FLAG_SHARED_PESTEL_V12`, `FLAG_PORTFOLIO_SWOT_TOWS_V12`, `FLAG_CAPACITY_PLANNER_V12`,
`FLAG_FOUNDER_ATTENTION_V12`, `FLAG_PORTFOLIO_CYCLE_V12`, `FLAG_AGENT_MEMORY_V12_3`. Spec
items with **no corresponding screen to hide** (BSC is just a string in a hardcoded stage
list, not a real UI; Agent Marketplace, Telephony/SIP, Realtime Video don't exist at all)
get no flag-gating work — inventing flags with nothing to gate is scope waste.

---

## Phase 1 — Feature Flags + Hide (fast, high leverage)

**Backend** (`backend/app/core/feature_flags.py`): add new V13 constants alongside the
existing V12 block — `FLAG_LEGAL_FUNCTION_V13`, `FLAG_MARKETING_FUNCTION_V13` (marketing
router currently has **zero** flag gating — confirmed via grep), `FLAG_SALES_FUNCTION_V13`,
`FLAG_TECH_FUNCTION_V13`, `FLAG_FINANCE_FUNCTION_V13`, `FLAG_LEARNING_V13`,
`FLAG_CEO_BRIEF_V13`, `FLAG_ADVANCED_ORG_CHART_V13`. Do **not** create parallel
`cycle_v13`/`okr_v13`/`weekly_mission_v13`/etc. flags for surfaces already covered by
`FLAG_CYCLE_13WEEK_V12`/`FLAG_WEEKLY_MISSIONS_V12`/`FLAG_MILESTONES_GATES_V12` — two flags
controlling one feature is exactly the trap the spec's "centralized" principle warns against.
New additive migration seeds these + re-seeds `portfolio_v12`/`capacity_planner_v12`/
`founder_attention_v12`/`portfolio_cycle_v12`/`portfolio_swot_tows_v12` to `enabled=false`
as the **new-workspace default** (insert rows only — never flip existing workspaces'
flag rows silently, per spec §69's non-destructive rule applied to config, not just schema).
Also gate `okrs_router.py` (currently has zero `require_flag` calls, confirmed via grep,
unlike `execution_router.py` which already gates every stage/milestone endpoint) and
`modules/marketing/router.py` with their respective flags. Add a small additive read
endpoint `GET /api/v1/platform/feature-flags?workspace_id=...` in
`modules/platform/router.py` backed by the existing `list_feature_flags()`.

**Frontend**: new `frontend/lib/data/services/feature_flags_service.dart` (same style as
`OutcomesService`/`MarketingService`) + new `frontend/lib/core/services/feature_flags_controller.dart`
(GetX `Rx<Map<String,bool>>`, loaded once at dashboard boot). In
`frontend/lib/modules/dashboard/views/dashboard_view.dart`, extend the existing `_NavItem`
class with an optional `flagKey`, convert the currently-`static const` `_navGroups` into a
getter that filters through the controller (reusing the exact `.where(...)` pattern already
used for `desktopOnly` at the confirmed lines 124-134 — this is additive, not a rewrite of
the 20-case index switch). Add a new tiny `FeatureNotEnabledView` widget shown when a
deep-linked/flag-gated case is hit while its flag is off (spec §6).

---

## Phase 2 — Additive Schema: Work Traceability + Lesson

New additive-only migration: `tasks.function` (String(20), null), `outcomes.function`
(String(20), null), `outcomes.cycle_id` (BIGINT null, FK `twelve_week_cycles.id` — `Outcome`
has no cycle trace today since it's compiled from `Milestone`, not `WeeklyCommitment`;
confirmed by reading `planning_compiler_service.py`), `okr_objectives.why` (Text, null),
`key_results.metric_type` (String, null), `key_results.evidence_refs` (JSONB, null).

New module `backend/app/modules/learning/` (flat sibling of `modules/organization/`, not
folded into the already-866-line `strategy/models.py`):
```
backend/app/modules/learning/
  __init__.py
  models.py   # Lesson: id, workspace_id, cycle_id?, week_no?, function?, project_id?,
              # observation, evidence_refs (JSONB), interpretation?, recommendation?,
              # confidence, status (DRAFT/CONFIRMED/REJECTED/APPLIED/SUPERSEDED),
              # created_by?, created_at
  service.py  # create_lesson, list_lessons, status transitions
  router.py   # mounted /api/v1/learning
```
`MarketingLearning` (`modules/marketing/models.py`) stays untouched — its richer
observation/hypothesis/action/result loop is preserved. Instead, Marketing's learning
creation service call also writes a bridging `Lesson` row (`function="MARKETING"`,
`evidence_refs={"marketing_learning_id": ...}`). Legal/Sales/Tech/Finance (no prior
learning table) write directly to `Lesson`. `WeeklyReview`/`CycleReview` API responses pull
`Lesson` rows by `cycle_id`/`week_no` at read-time — no schema change to either.

---

## Phase 3 — Function Shells: Legal, Sales, Tech (thin), Marketing (flag only)

**Convention decision**: new Function modules stay flat siblings under `backend/app/modules/`
(`modules/legal/`, `modules/sales/`, `modules/tech/`), matching this repo's actual pattern
(confirmed via `main.py` imports — everything is a flat module, no `app/functions/` parent
package exists anywhere). The spec's §65 nested-package suggestion is aspirational
greenfield advice; introducing a second convention alongside existing `modules/marketing/`
for the same conceptual category buys nothing. This becomes ADR-V13-003.

- `modules/legal/`: new `LegalChecklistItem` (readiness checklist), `LegalObligation`
  (tracking) tables. Generated documents (contract analysis, terms drafting) become
  `Artifact` rows (`type="document"`) via the **existing** `modules/outcomes` `Artifact`
  table — not a new artifact-shaped table.
- `modules/sales/`: new `SalesLead` table (`key_result_id` nullable FK, ties leads to KRs
  per spec §31's Finance-and-Cycle pattern applied to Sales too).
- `modules/tech/`: **no new execution model.** `DeveloperJob` already is the pipeline.
  This module is a thin routing/status layer: `service.py` tags `DeveloperJob`/`Task`/
  `Outcome` with `function="TECH"` at creation and aggregates status for the AI Team card;
  `router.py` exposes `/api/v1/tech/status`.
- Marketing: add `FLAG_MARKETING_FUNCTION_V13` gating (Phase 1) + the Lesson bridge
  (Phase 2) + tag its compiled `Task`/`Outcome` rows `function="MARKETING"`. No rebuild.
- New `backend/app/core/function_router.py`: deterministic keyword routing rule from
  spec §53 (`legal/compliance/contract → LEGAL`, etc.), with ambiguous cases falling back
  to DeepSeek classification (existing `integrations/deepseek_client.py`).

New additive migration for the Legal/Sales tables.

---

## Phase 4 — Tool Registry Formalization + LiveKit Wiring

Two existing "tool" layers were confirmed and must stay distinct: `modules/integrations/mcp/
mcp_hub.py`+`mcp_catalog.py` (external MCP connectors, permission tiers) vs.
`modules/realtime/tools.py` (plain Python functions individually flag-gated inline,
1:1-wrapped by `@function_tool` closures in `services/realtime_agent/tools.py::build_tools()`
— this is the actual domain-tool layer LiveKit voice uses).

New `backend/app/core/tool_registry.py`: a small `@register(namespace, name, flag_key=None)`
decorator populating a dict of `ToolSpec`, plus `available_tools(db, workspace_id)` filtering
by flag. Apply it in-place to existing functions in `modules/realtime/tools.py`
(`@register("approval", "approve")` on `approve_action`, etc. — additive decoration, not a
rewrite) and add new ones: `get_cycle_status`, `get_weekly_mission`, `get_function_status`,
`get_finance_snapshot` (read-only; voice must never mutate money per rule 21).
`services/realtime_agent/tools.py::build_tools()` iterates `available_tools()` instead of
hand-listing every tool, so new tools become flag-gated automatically. Extend the existing
`NAVIGATION_TARGETS` whitelist (confirmed hardcoded in `services/realtime_agent/tools.py`)
to the new nav destinations from Phase 7b. No changes to `session_guards.py`,
`transport_resolver.py`, or the local/cloud LiveKit split — already scope-correct.

---

## Phase 5 — Finance Core (biggest greenfield piece)

Zero existing Finance/accounting/tax code (confirmed repo-wide). New module:

```
backend/app/modules/finance/
  models.py                 # 11 tables, see below
  router.py                 # thin mount (mirrors marketing/router.py shim pattern)
  routers/{profile,overview,transactions,books,reports,periods,exceptions}_router.py
  domain/                   # DETERMINISTIC ONLY — no LLM imports allowed
    accounting_profile_service.py
    period_service.py       # OPEN/REVIEW/CLOSED/LOCKED transitions
    management_metrics_service.py   # cash/burn/runway/budget-vs-actual arithmetic
    exception_engine.py     # rule-based detection of the 12 exception types (spec §32)
  regulations/tt58_2026/
    registry.py              # loads YAML metadata, get_book_templates(mode)
    modes.py                 # TT58_MODE_1..4 enum; only Mode 1 has real template data at ship
    templates/ validations/
  agent/
    finance_agent_service.py # the ONLY file allowed to call an LLM — narrates numbers
                              # already computed by domain/, never computes them itself
```
Regulation content lives in data files, not code: new top-level
`backend/regulations/vn/tt58_2026/{metadata.yaml,modes.yaml,books/,statements/,validations/}`,
loaded at runtime — keeps forms out of both Python and Dart (spec §26/§66).

**Data model** (new additive migration, all 11 tables from spec §68's list):
`AccountingProfile` (workspace-unique; `status` DRAFT→PENDING_CONFIRMATION→ACTIVE, requires
human `confirmed_by` — never auto-classify eligibility), `AccountingRegulation`,
`AccountingRegulationVersion`, `AccountingBookTemplate` (`mode`, `code` e.g. `S1-DNSN`,
`columns_schema` JSONB, `status` DRAFT/REVIEW/PRODUCTION_READY), `FinancialStatementTemplate`,
`AccountingDocument` (attachment reuses the existing MinIO/Artifact mechanism, no new blob
store), `FinancialTransaction` (`project_id`/`cycle_id`/`work_item_id` nullable FKs into
existing tables), `AccountingRecord`, `AccountingPeriod` (`status` OPEN/REVIEW/CLOSED/LOCKED),
`FinanceException` (12 types from spec §32), `FinanceManagementSnapshot` (cash/burn/runway/
revenue/... snapshotted for CEO Brief/Week13 read performance).

Audit trail (spec §59-60) reuses the **existing** `core/audit.py::write_audit_log` — no new
Finance-specific audit table.

**Deterministic-calculation enforcement** (CLAUDE.md rule 13-14, spec §54/§76): add
`backend/app/tests/finance/test_finance_domain_no_llm_import.py` — a static-import-check
test asserting no file under `modules/finance/domain/` or `modules/finance/regulations/`
imports `app.modules.chat` or any LLM provider client. This makes ADR-FIN-004 enforced, not
just documented.

**TT58 Mode 1 first** (spec §25): `modes.py` declares all 4 modes so Mode 2-4 profile
activation can be explicitly rejected with a clear error (not silent mis-behavior), but only
`S1-DNSN` gets real template data at ship time.

---

## Phase 6 — Finance Books/Templates/Period Close + Golden Tests

Implement `AccountingRecord` generation for `S1-DNSN` against `management_metrics_service.py`,
`AccountingPeriod` close/reopen (explicit authorization required to reopen a `LOCKED`
period), and `backend/app/tests/finance/` golden-fixture tests (spec §76): known documents →
known transactions → known book rows → known totals, asserted byte-for-byte, no LLM anywhere
in the test path (mirrors the existing `MagicMock`/`patch` discipline in `test_realtime_tools.py`).
`AccountingBookTemplate.status` only reaches `PRODUCTION_READY` once its golden test passes
(ADR-FIN-007).

---

## Phase 7 — Frontend: AI Team UI + Function Modules + Finance UI

**7a. Wire up the orphaned `OutcomesService`.** Confirmed: `frontend/lib/data/services/
outcomes_service.dart` (getOutcomes/createOutcome/triggerRun/getRunDetails/getRunEvents/
getArtifacts) has no caller anywhere in the app today. New `frontend/lib/modules/ai_team/`
(bindings/controllers/views, sized like `modules/organization/`): `AiTeamView` renders 5
Function cards (current work / status / latest result / needs founder? / key metric per
spec §63), backed by a new `FunctionStatusService` hitting a new small backend read endpoint
that joins `Task.function`/`Outcome.function`/`Artifact`/`Lesson`.

**7b. Navigation restructure** — additive to `dashboard_view.dart`'s existing `_NavGroup`/
`_NavItem` classes (not a GetX route rewrite): new groups for Home (CEO Brief, wraps the
existing `platform/hub_service.py::get_hub_summary_data`), Cycle (re-labeled existing
`StrategyView`), Work (existing `TasksView`), AI Team (new, 7a), Finance (new, flag-gated),
Knowledge (existing `VaultView`), Settings. V12 items not in the default V13 nav
(Marketing OS as standalone, Workflows, Connections, Plugins, Channels, Usage, Audit,
Organization, etc.) are **not removed from the 20-case switch** — they move under a new
"Developer Mode → Experimental Features" group (spec §70), gated by a local device-only
toggle, not a backend flag.

**7c. New module shells**: `frontend/lib/modules/{legal,sales,tech,finance}/{bindings,
controllers,views}/`, mirroring Marketing's structure. Tech's view is mostly a thin wrapper
over the existing Developer/devices view.

**7d. Finance UI**: `finance_view.dart` with tabs Overview/Transactions/Documents/Books/
Reports/Periods/Exceptions/Settings (spec §64), each `views/tabs/*_tab.dart` — same proven
split already used in `modules/strategy/views/tabs/`.

---

## Phase 8 — Week 13 / Weekly Review Read-Time Composition

Enrich `review_service.py`'s API responses (Weekly Review, Week 13/`CycleReview`,
`CelebrationRecord`) with Function-results and Finance-status sections by joining the new
`Lesson`, `Task.function`/`Outcome.function`, and `FinanceManagementSnapshot` data — no
further schema changes; this is pure composition on top of Phases 2, 3, 5.

---

## Phase 9 — Security, Tests, ADRs, DEPLOYMENT.md

**Backend tests** (`backend/app/tests/`, matching existing `test_realtime_tools.py`/
`test_core_product_flow.py` style): `test_lesson_service.py`, `test_tech_devices_function_tagging.py`,
`test_tool_registry.py`, `test_feature_flags_v13.py` (extends existing
`test_feature_flags.py`), full `backend/app/tests/finance/` suite (profile activation gating,
TT58 golden fixtures, mode-conflict rejection, period locking, no-LLM-import check, exception
engine), extended `test_realtime_tools.py` for the new voice tools, extended
`test_iam_auth.py`/`test_governance.py`-style 403 checks for disabled Finance/Legal routes.

**Flutter tests** (`frontend/test/`): `feature_flags_service_test.dart`,
`finance_service_test.dart`, `legal_service_test.dart`, `sales_service_test.dart`,
`ai_team_service_test.dart` (finally exercises `OutcomesService` through a real controller),
`function_status_service_test.dart`, widget test for `FeatureNotEnabledView`.

**14 ADRs** in `docs/adr/` (format matches confirmed `ADR-MEM-001-agent-memory-gateway-
boundary.md`: Status/Context/Decision/Consequences, citing real file paths):

- ADR-V13-001 — Cycle is a read-composed view over `TwelveWeekCycle`+`CycleContract`, not a
  new table or a rename of `OkrCycle`.
- ADR-V13-002 — Work→KR traceability reuses the existing `Initiative`/
  `InitiativeKeyResultLink`/`WeeklyCommitment` chain; only `Task.function`/`Outcome.function`
  are additive.
- ADR-V13-003 — New Function modules stay flat siblings of `modules/marketing`, not nested
  under a new `app/functions/` package.
- ADR-V13-004 — V13 hide-work reuses existing V12 flags; new flags are added only where no
  V12 flag or gated surface exists today.
- ADR-V13-005 — V13 LiveKit work is additive tool registration only; existing session/
  barge-in/navigation-whitelist infra is unmodified.
- ADR-V13-006 — Generic `Lesson` lives in new `modules/learning/`; `MarketingLearning` is
  preserved and bridges via a service-level write-through, not a schema merge.
- ADR-FIN-001 — `modules/finance/` splits `domain/` (deterministic) from `agent/`
  (LLM-assisted) at the package level, enforced by an import-boundary test.
- ADR-FIN-002 — Regulation content lives in `backend/regulations/vn/tt58_2026/*.yaml`,
  never hard-coded in Python or Dart.
- ADR-FIN-003 — No `TaxEngine`/tax-determination code in V13; the Accounting/Tax boundary
  is enforced structurally by omission.
- ADR-FIN-004 — All authoritative figures computed in `modules/finance/domain/`; the LLM
  layer may only narrate, enforced by a static-import CI check.
- ADR-FIN-005 — `AccountingProfile` requires human `confirmed_by` before `ACTIVE`; no
  auto-promotion of eligibility.
- ADR-FIN-006 — All 4 TT58 modes are declared; only Mode 1 (S1-DNSN) ships with real
  templates; Modes 2-4 reject activation with a clear error.
- ADR-FIN-007 — Templates carry DRAFT/REVIEW status until a passing golden-fixture test
  promotes them to PRODUCTION_READY.
- ADR-FIN-008 — Period close/reopen and financial mutations route through the existing
  `core/audit.py::write_audit_log`; `LOCKED` periods block writes at the service layer.

**DEPLOYMENT.md**: additive section documenting the new modules/migrations (following the
existing per-revision paragraph style already used for `e8f1a7c3d5b9` etc.), and an explicit
callout of the known pre-existing `Base.metadata.create_all()`-before-`alembic upgrade head`
hazard (already documented as a troubleshooting entry) so each new V13 migration
(`lessons`, Finance's 11 tables, Legal/Sales tables) is exercised against a fresh dev DB
using the documented recovery sequence before being called done.

---

## Non-Destructive Migration Discipline

Current Alembic head confirmed: `cce0693a148d` (`add_agent_memory_mem0_tables.py`). All V13
migrations chain off this head, additive only:

1. `v13_001_flags` — INSERT new `feature_flags` rows only.
2. `v13_002_okr_work_additive` — 6 nullable `ADD COLUMN`s (Phase 2), zero risk to existing rows.
3. `v13_003_lessons` — `CREATE TABLE lessons`.
4. `v13_004_legal_sales_tables` — `CREATE TABLE legal_checklist_items`, `sales_leads` (+ `legal_obligations`).
5. `v13_005_finance_core` — `CREATE TABLE` for all 11 Finance tables (Phase 5).

No migration drops, renames, or destructively alters any V12 table.
`Department.capability_domain` gaining a `"sales"` value needs **zero migration** — it's a
plain `String(50)` with no DB-level enum/CHECK constraint (confirmed by reading
`modules/organization/models.py`).

---

## Verification

Status below reflects commands actually executed during the 2026-08-13 post-implementation
audit, not aspirational checklist items.

- Backend: `cd backend && pytest app/tests -x -q --collect-only` → **402 tests collected,
  zero import errors.** `pytest app/tests/finance -q` → **9 passed** (pure unit tests, no DB
  required — the "golden" fixtures are pre-parsed transaction dicts, not raw documents, so
  this is thinner than the full pipeline the plan describes; see Known Gaps). Full non-finance
  suite was not executed end-to-end against a live Postgres in this audit pass — still open.
- Migrations: **not executed** against a fresh dev Postgres in this audit pass. The 6 V13
  migration files exist and chain correctly off `cce0693a148d` (confirmed by reading them),
  but the `alembic upgrade head` fresh-DB run called for below is still an open action item.
- Feature flags: `GET /api/v1/platform/feature-flags` endpoint confirmed real and
  tenancy-checked by code reading (`modules/platform/feature_flags_router.py`); the manual
  toggle-and-observe-`FeatureNotEnabledView` click-through was **not** performed live in this
  audit — code path is wired (confirmed by reading `dashboard_view.dart`) but not manually
  exercised.
- Frontend: `cd frontend && flutter test` → **153 passed.** `flutter analyze` → **No issues
  found.** App was not manually launched in this audit pass; nav rendering and AI Team card
  population were confirmed by reading `dashboard_view.dart` and `ai_team_controller.dart`,
  not by driving the running app.
- End-to-end: spec §72's founder vertical slice was **not run by hand** in this audit. Given
  the Known Gaps below (Finance Books/Reports/Settings tabs are static placeholders with no
  backend call), the Finance half of that slice ("Mode-1 setup wizard completes and produces
  a S1-DNSN book preview") would currently fail at the UI layer even though the backend
  supports it — do not mark this scenario done until Phase 7d's gaps are closed.
- `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib`
  → **empty**, re-confirmed 2026-08-13. Clean, as required.

---

## Phase Tracking

Verified 2026-08-13 by reading the shipped code and running the test suites (see
Verification above). "Implemented" = matches the plan's substance, not just its file names.
"Partially implemented" = real, tenancy-checked, wired to a real backend — but narrower than
what this plan or its own cross-references (e.g. "mirrors Marketing's structure") claim.

| Phase | Status | Notes |
|---|---|---|
| 1 — Feature flags + hide | Implemented | All 8 flags, `okrs_router.py`/`marketing/router.py` gating, insert-only seed migration, and the Flutter consumption stack (service/controller/`FeatureNotEnabledView`) all confirmed real. One wording correction: `v13_006_core_flag_defaults.py` does one scoped `UPDATE` on global-default rows (`workspace_id IS NULL`) — see Known Gaps #1. |
| 2 — Additive schema + Lesson | Implemented | `Lesson` model, status machine, and Marketing's write-through bridge (`function="MARKETING"`, `evidence_refs={"marketing_learning_id": ...}`) all match the plan exactly. |
| 3 — Legal/Sales/Tech shells | Partially implemented | Legal/Sales CRUD shells and Tech's thin status layer are real and tenancy-checked. Two claims don't hold: the DeepSeek classification fallback in `function_router.py` is never called by anything in production (dead code), and Marketing's `Task`/`Outcome` rows are never tagged `function="MARKETING"` (only the `Lesson` bridge is) — see Known Gaps #2-3. |
| 4 — Tool registry + LiveKit wiring | Implemented | `tool_registry.py`, all 4 new read-only tools, and `build_tools()` filtering via `available_tools()` all confirmed real. Gap: no dedicated test exercises the 4 new tools — see Known Gaps #4. |
| 5 — Finance core | Implemented | All 11 tables, `AccountingProfile` human-confirmation gate, and the deterministic/LLM package split (enforced by a real AST-based import scanner) all confirmed real. Gap: `backend/regulations/vn/tt58_2026/` has no `books/`/`statements/`/`validations/` subdirectories and `registry.py` never reads `metadata.yaml` — see Known Gaps #5. |
| 6 — Finance books/period close/golden tests | Implemented | `AccountingPeriod` LOCKED-state write-blocking is real at both the transition layer and the transaction-write layer. The golden test does a genuine byte-for-byte dict comparison, but starts from pre-parsed transaction dicts rather than the full "known documents → known transactions" chain the plan describes — thinner than promised, not fake. |
| 7 — Frontend AI Team + Function UIs | Partially implemented | Nav restructure (7b) and feature-flag gating are fully real. AI Team (7a) is real but shallow (`controller.outcomes` is fetched and never rendered). Legal/Sales UIs (7c) are 2-3 line raw `ListTile` dumps with no create/edit flows despite the backend already exposing `POST` endpoints for both — this contradicts the plan's own "mirrors Marketing's structure" language. Finance UI (7d) is the largest gap: 3 of 8 tabs (Books, Reports, Settings) are static placeholders with no backend call at all, and `FinanceService` has no `getBooks()`/`getReports()`/`getProfile()` methods — see Known Gaps #6-8. |
| 8 — Week13/Weekly Review composition | Implemented | `review_service.py`'s `_v13_composition` genuinely joins `Lesson`, `FinanceManagementSnapshot`, and function-status data at read time. |
| 9 — Security/tests/ADRs/DEPLOYMENT.md | Implemented | All 14 ADRs exist with real (if terse) Status/Context/Decision/Consequences content matching the actual code. `DEPLOYMENT.md` has the correct V13 migration list and the `create_all()`-before-`alembic upgrade head` hazard callout. Snowflake IDs and server-side `workspace_id` tenancy checks confirmed present on every new model/router. Gaps: no voice-tool tests (Known Gaps #4); no test drives `AiTeamController` specifically, so the plan's claim that a test "finally exercises `OutcomesService` through a real controller" isn't satisfied — see Known Gaps #9. |

### Known Gaps (from the 2026-08-13 audit — not blocking, but plan overstated these)

1. **Migration wording.** Phase 1 / Non-Destructive Migration Discipline both say flag-seed
   migrations are "insert rows only." `v13_006_core_flag_defaults.py` also runs one `UPDATE`
   — scoped to global-default rows (`workspace_id IS NULL`) so it cannot silently flip an
   existing workspace's override, but it isn't literally insert-only. Reword or split it.
2. **DeepSeek routing fallback is dead code.** `backend/app/core/function_router.py`'s
   classifier-fallback path has zero production callers; nothing wires it to
   `integrations/deepseek_client.py`. Either call it from somewhere real or drop the claim.
3. **Marketing's `Task`/`Outcome` aren't tagged `function="MARKETING"`.** Only the `Lesson`
   bridge sets `function`. `grep -rn 'function="MARKETING"' backend/app/modules/` has exactly
   one hit. Needed for Phase 8's Function Results composition to include Marketing work items.
4. **No test coverage for the 4 new realtime voice tools** (`get_cycle_status`,
   `get_weekly_mission`, `get_function_status`, `get_finance_snapshot`) in either
   `test_realtime_tools.py` or `services/realtime_agent/tests/test_tools.py`.
5. **TT58 regulation data files are incomplete.** `backend/regulations/vn/tt58_2026/` has
   only `metadata.yaml` and `modes.yaml`; the planned `books/`, `statements/`, `validations/`
   subdirectories don't exist, and `regulations/tt58_2026/registry.py` never reads
   `metadata.yaml` at all — only `modes.yaml`.
6. **`AiTeamView` fetches `Outcome` data it never renders.** `AiTeamController` calls
   `OutcomesService.getOutcomes()` but `ai_team_view.dart` only displays the 5 function-status
   cards.
7. **Legal/Sales frontend UIs are read-only stubs.** `legal_controller.dart`/`legal_view.dart`
   and their Sales equivalents are 2-3 line raw key-value dumps with no create/edit flow, even
   though the backend already exposes `POST /legal/checklist`, `POST /legal/obligations`,
   `POST /sales/leads`. `LegalBinding`/`SalesBinding`/`TechBinding`/`FinanceBinding` classes
   also exist but are never referenced anywhere in `frontend/lib` (dead scaffolding — the app
   uses manual `Get.put()` instead).
8. **Finance UI: 3 of 8 tabs are non-functional placeholders.** Books, Reports, and Settings
   tabs in `finance_view.dart` render `FinancePlaceholderTab` (a static centered label) with
   no backend call. `FinanceService` (frontend) has no `getBooks()`/`getReports()`/
   `getProfile()` methods even though `books_router.py`/`reports_router.py`/`profile_router.py`
   exist server-side. This is the reason the founder vertical-slice E2E check above is marked
   not-yet-passable.
9. **No test drives `AiTeamController`.** `outcomes_service_test.dart` tests the service
   layer directly, same as before this V13 work — the plan's claim that this "finally
   exercises `OutcomesService` through a real controller" isn't met.
