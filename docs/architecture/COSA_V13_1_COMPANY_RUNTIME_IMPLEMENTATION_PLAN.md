# COSA V13.1 — Company Runtime Adjustment: Implementation Plan

> **Status: implemented and verified (2026-08-13).** Sprints 1-6 (P0) are built and
> merged into the working tree; Sprints 7-8 (P1) remain deliberately deferred. See
> [Implementation Status](#implementation-status) at the end for what was verified,
> the two deviations found during verification, and the remaining manual gates.

## Context

`COSA_V13_1_Company_Runtime_Adjustment_OpenOPC.md` (repo root) proposes deepening the already-deployed
V13 system with an OpenOPC-inspired "Company Runtime" layer: work intent classification, a `WorkItem`
state machine, dependency DAG, work contracts, review/rework, structured handoffs, blockers, a founder
"Needs You" exception queue, runtime checkpoint/resume, and (as P1) an executor resolver, ephemeral
specialists, and self-growing function skills. The spec is explicit that this must be additive and must
not clone OpenOPC as a dependency or create a second execution engine.

Three parallel codebase surveys (backend domain models, backend Learning/LiveKit/Finance, Flutter
frontend) were run against the real repo before writing this plan. **The single most important finding:
the spec's central assumption is wrong for this repo.** There is no `WorkItem` table anywhere — `grep
"class WorkItem"` across `backend/app` returns nothing. The real execution primitives are `Task`
(`backend/app/modules/tasks/models.py`) and `Outcome`/`OutcomeRun`/`RunStep`/`RunEvent`/`Artifact`
(`backend/app/modules/outcomes/models.py`), exactly as `docs/architecture/MCOSA_V13_IMPLEMENTATION_PLAN.md`
already documented for V13 under the repo rule "never create a second execution engine." Treating the
spec literally would mean building a parallel WorkItem/Run/Approval system next to the one that already
exists — this plan instead remaps every spec concept onto the nearest real entity, following the same
reuse-first discipline the V13 plan itself used, and only creates a genuinely new table where nothing
existing covers the concept.

Two more gifts were found during the survey: `TaskDependency` (`tasks/models.py:47-53`) already exists
as a table but is **completely dead** — never read or written anywhere — and is exactly the Dependency
DAG primitive the spec wants. `Outcome.acceptance_criteria` is already JSONB — most of "Work Contract"
already exists, it's just not linked back to `Task` (`Outcome` has no `task_id` FK today).

The intended outcome of this plan: COSA stops being "a Cycle planner + five AI Function assistants" and
becomes an AI Chief of Staff that decomposes weekly missions, routes blockers, reviews AI output, and
interrupts the founder only for real exceptions — without introducing a second execution engine, a
second approval system, or breaking any existing V13 flow when the new feature flags are off.

---

## Governing Deviations From the Source Spec

1. **No `WorkItem` table.** `Task` (execution unit: status/function/execution_mode) + `Outcome` (result
   contract: desired_result/acceptance_criteria) jointly play the WorkItem role. They are two
   unconnected trees today — pairing them via a new `outcomes.task_id` FK is the single most important
   migration in this plan.
2. **No nested `app/company_runtime/{domain,application,api}` package** (spec §57). New backend code
   lives at `backend/app/modules/company_runtime/` — a flat sibling of `modules/finance/`, matching this
   repo's actual convention (`modules/finance/{models.py,router.py,routers/,domain/}`; confirmed no
   `app/functions/` or `app/work/` parent package exists anywhere).
3. **"Needs You" and the runtime summary belong on `hologram_hub_view.dart` (route `/hub`), not
   `dashboard_view.dart`.** `dashboard_view.dart` is nav chrome only (its "CEO Brief" item just opens
   `ChatView`); the real landing screen after login is the Hub, driven by `HologramHubController` and
   `HubService.getHubSummary()`.
4. **No flags are created for OpenOPC/marketplace/office-animation/agent-free-chat** (spec §44 asks for
   `false`-valued flags for these). The existing V13 plan explicitly rejected "inventing flags with
   nothing to gate" — these stay recorded as out-of-scope, not as disabled flags.

---

## Entity Mapping (spec concept → real entity → additive change)

| Spec concept | Real entity | Additive change |
|---|---|---|
| `WorkItem` | `Task` (execution unit) + `Outcome` (contract/result) | New nullable `outcomes.task_id` FK → `tasks.id`, pairing the two trees. |
| WorkItem state machine | `Task.status` (`String(50)`, no DB enum; today: `todo/in_progress/waiting_approval/blocked/done/cancelled`) | **No DB enum change.** New `TaskStateService` guard validates transitions and audits via the **existing** `core/audit.py::write_audit_log` (which already calls `publish_event()` — satisfies spec's "emit domain event" without a new event table). Spec's 12-state vocabulary is approximated onto the existing 6 values + the new `work_reviews`/`blockers` tables, where the extra nuance actually lives. |
| Dependency DAG | `TaskDependency` (exists, dead) | Add nullable `dependency_type` (BLOCKS/REQUIRES_OUTPUT/REQUIRES_APPROVAL/REQUIRES_DECISION/REQUIRES_DOCUMENT) and `status` (PENDING/SATISFIED/FAILED) columns. No new table. |
| Work Contract | `Outcome` (already has `acceptance_criteria` JSONB) | Add nullable `required_artifacts` JSONB (mirrors `Milestone.required_artifacts` at `strategy/models.py:469`), `reviewer_id` (FK users), `review_type`, `validation_rules` JSONB, `rework_count` (default 0). `linked_kr_ids` reuses the **existing** generic `OkrLink` table (`strategy/models.py:282-291`: `from_entity_type/id → to_entity_type/id, relation_type`) per the precedent already set by `docs/adr/ADR-V13-002-work-kr-traceability.md` — not a new JSONB array. |
| Review / Rework | Does not exist generically | New `work_reviews` table. Kept distinct from the 3 existing domain approval tables (`WorkflowApproval`, `PendingApproval`, `EmailApproval`) — Review answers "is this output good enough," Approval answers "may this risky action proceed." They compose, not merge. |
| Handoff | Does not exist | New `handoffs` table; `from_function`/`to_function` constrained to `core/function_router.py::FUNCTION_KEYWORDS` keys. |
| Blocker / BlockerRouter | Does not exist / `core/function_router.py::route_function()` (deterministic classifier; DeepSeek fallback exists but is dead code) | New `blockers` table; new `blocker_router.py` wraps `route_function()`. |
| Needs You | Does not exist | New **pointer/overlay** table `needs_you_items` (`source_type`, `source_id`, `priority`, `status`, `snooze_until` — no content duplication). Composed at read-time against `Task`/`Blocker`/the 3 approval tables, mirroring the exact read-composition convention `ai_team/service.py::get_function_statuses()` already established. |
| Runtime Checkpoint / Resume | Does not exist | New `runtime_checkpoints` table (genuinely new, no precedent). |
| Work Inspector | UI composition only | No new table — a read endpoint joining `Task`+`Outcome`+`TaskDependency`+`work_reviews`+`handoffs`+`blockers`+`Artifact`+the 3 approval tables+`Lesson`. |
| `CompanyRuntimeManager` | New, thin coordinator | Calls `TaskStateService`/`DependencyService`/`BlockerRouter`/`ReviewService` and the **existing** `devices.create_developer_job()` for Tech work — never executes anything itself (no second execution engine). |
| Work Intent Classifier / Quick Task vs Company Work | New, thin | Same deterministic-scoring shape as `function_router.py`; DeepSeek fallback only wired if proven necessary (don't repeat the existing dead-fallback pattern speculatively). |
| ExecutorResolver, Ephemeral Specialists, Cycle Grants, Contribution Evaluation, Agent Experience, Function Skills | All new | **P1 — deferred.** Flags reserved, `false`. No schema this delivery window. |

---

## Sprint Plan

`modules/company_runtime/` is created once in Sprint 1 and only grows after — never restructured.

### Sprint 1 — State Machine + Work Contract + Review/Rework (recommended first shippable slice)

Buildable entirely on `Task`+`Outcome`; no new orchestration service yet.

**New** (`backend/app/modules/company_runtime/`):
- `models.py` — `WorkReview` (`work_reviews`: `id, workspace_id, outcome_id FK, reviewer_type, reviewer_id nullable FK→users, result, feedback, evidence_refs JSONB, created_at`)
- `state_service.py` — `TaskStateService.transition(db, task, target_status, actor_id, reason)`; legal-transition map over the 6 existing `Task.status` values; calls `write_audit_log(action="task.status.transition", ...)`.
- `contract_service.py` — `set_work_contract(db, outcome, required_artifacts, reviewer_id, review_type, validation_rules, linked_kr_ids)`; writes `OkrLink` rows for `linked_kr_ids`.
- `review_service.py` — `create_review(...)`: `ACCEPTED` → `Outcome.status="completed"` + `Task.status="done"` via `TaskStateService`; `REWORK_REQUIRED` → `Task.status="in_progress"` + `rework_count += 1`, capped at a configurable max (default 3) before requiring `ESCALATED`.
- `router.py` (thin mount, mirrors `finance/router.py`) + `routers/contracts_router.py`, `routers/reviews_router.py`: `POST /api/v1/company-runtime/outcomes/{outcome_id}/contract`, `POST /api/v1/company-runtime/outcomes/{outcome_id}/review`.
- `backend/app/tests/company_runtime/test_state_service.py`, `test_contract_service.py`, `test_review_service.py`.

**Extended**: `outcomes/models.py::Outcome` (+`task_id`, `required_artifacts`, `reviewer_id`, `review_type`, `validation_rules`, `rework_count`); `main.py` (mount new router); `core/feature_flags.py` (Sprint 1 flags). `tasks/router.py::update_task` (currently an unguarded `setattr` loop over `TaskUpdate.dict(exclude_unset=True)` at lines 149-171) starts routing status changes through `TaskStateService` when the flag is on and the task has a linked `Outcome` — this closes a real pre-existing gap (today any status string is accepted with zero validation).

**Deferred**: Dependency DAG, Blocker, Handoff, Needs You, Checkpoint, Intent Classifier, `CompanyRuntimeManager`, Work Inspector, Flutter UI, LiveKit tools.

### Sprint 2 — Dependency Runtime

- `dependency_service.py` — `get_ready_tasks()`, `detect_cycles()` (DFS), `reevaluate_downstream(task_id)`, called from `TaskStateService.transition` on every status change.
- Extend `TaskDependency` (+`dependency_type`, `status`) — its first real reader/writer.
- `test_dependency_service.py` with explicit cycle-detection tests.

### Sprint 3 — Review + Exceptions (Blocker / BlockerRouter / Needs You)

- New `Blocker`, `NeedsYouItem` models; `blocker_router.py` (wraps `route_function()`); `needs_you_service.py` (read-composition, mirrors `get_function_statuses()`).
- **Finance exception wiring** (closes a confirmed gap): `modules/finance/domain/exception_engine.py::detect_exceptions()` is fully coded but has zero write-path callers today. Wire it into `transactions_router.py`'s write path; persist `FinanceException` rows; `severity="ERROR"` creates a `Blocker` (`FINANCE_EXCEPTION`) that `needs_you_service` surfaces. Directly satisfies the spec's Golden Scenario 2.
- `routers/blockers_router.py`, `routers/needs_you_router.py`.

### Sprint 4 — Collaboration (Structured Handoff + Work Inspector)

- New `Handoff` model + `handoff_service.py` + `routers/handoffs_router.py`.
- Work Inspector composition endpoint: `GET /api/v1/company-runtime/tasks/{task_id}/inspector`.
- **Tech gap closure**: add an endpoint to resolve a `DeveloperJob` out of `WAITING_APPROVAL` (`devices/models.py` — confirmed no such endpoint exists today), wired through the Review flow.

### Sprint 5 — Recovery (Runtime Checkpoint / Resume)

- New `RuntimeCheckpoint` model + `checkpoint_service.py` (`checkpoint(reason)` snapshots task/dependency/pending-approval/pending-needs-you state; `resume()` implements the spec's reconciliation steps, marking orphaned in-progress Tasks with an internal `RECOVERY_NEEDED` marker, not a public status).
- Integration test reproducing the spec's Runtime Resume golden scenario.

### Sprint 6 — Runtime Manager (Intent Classifier, Quick Task vs Company Work, decomposition)

- `intent_classifier.py`, `decomposition_service.py` (`decompose_weekly_mission(weekly_plan_id)` creates `Task`+`Outcome` pairs per Function via `function_router.route_function()`, wires `TaskDependency` edges), `runtime_manager.py` (`CompanyRuntimeManager`, thin coordinator only).
- `routers/runtime_router.py`: classify-intent, decompose, status, dag endpoints.
- **This is the sprint where `company_runtime_v13_1` (master flag) first flips to `true`** — only after all 5 golden scenarios from the spec pass against a Developer Workspace.

### Sprint 7-8 — P1 (Learning Upgrade, Workforce Intelligence) — fully deferred

Lesson Candidate/Improvement Candidate tables extend (not replace) the existing `Lesson`
(`modules/learning/`) and `review_service.py::_v13_composition` read path. ExecutorResolver, Ephemeral
Specialists, Cycle Grants, Agent Experience, Function Skills: reserved flag/migration names only, no
schema or code this delivery window (never a P0 prerequisite).

---

## Migrations

Continuing the `v13_00N` chain from head `v13_006_defaults`, all additive-only:

| File | `down_revision` | Content |
|---|---|---|
| `v13_007_runtime_contracts.py` | `v13_006_defaults` | `outcomes.task_id`/`required_artifacts`/`reviewer_id`/`review_type`/`validation_rules`/`rework_count`; `CREATE TABLE work_reviews`. |
| `v13_008_dependency_dag.py` | `v13_007_contracts` | `task_dependencies.dependency_type`, `.status`. |
| `v13_009_blockers_needs_you.py` | `v13_008_dag` | `CREATE TABLE blockers`, `needs_you_items`. |
| `v13_010_handoffs.py` | `v13_009_blockers` | `CREATE TABLE handoffs`. |
| `v13_011_runtime_checkpoints.py` | `v13_010_handoffs` | `CREATE TABLE runtime_checkpoints`. |
| `v13_012_runtime_flags.py` | `v13_011_checkpoints` | INSERT-only: seeds all Sprint 1-8 `*_v13_1` flags at `enabled=false`. Literally insert-only, unlike `v13_006` (learn from that Known Gap). |
| `v13_013_runtime_flag_defaults.py` | `v13_012_runtime_flags` | Scoped `UPDATE` flipping the **P0 subset** to `true` — a deliberate deploy-gate migration run only after Sprint 6's golden scenarios pass, documented in `DEPLOYMENT.md` the same way `v13_006` is. |

All new tables use the inline Snowflake-ID pattern (`mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)`) to match `outcomes/models.py`/`tasks/models.py`. Every migration must be exercised against a fresh dev DB per `DEPLOYMENT.md`'s documented `create_all()`-before-`alembic upgrade head` recovery procedure before being marked done.

---

## Feature Flags

New constants in `backend/app/core/feature_flags.py`, same style as the existing V13 block:

```
FLAG_COMPANY_RUNTIME_V13_1, FLAG_WORKITEM_STATE_MACHINE_V13_1, FLAG_WORK_CONTRACT_V13_1,
FLAG_REVIEW_REWORK_V13_1, FLAG_DEPENDENCY_DAG_V13_1, FLAG_STRUCTURED_BLOCKER_V13_1,
FLAG_NEEDS_YOU_QUEUE_V13_1, FLAG_STRUCTURED_HANDOFF_V13_1, FLAG_WORK_INSPECTOR_V13_1,
FLAG_RUNTIME_CHECKPOINT_V13_1, FLAG_WORK_INTENT_CLASSIFIER_V13_1, FLAG_QUICK_TASK_V13_1,
FLAG_COMPANY_WORK_V13_1
```
all seeded `false` by `v13_012`, flipped `true` (P0 subset only) by `v13_013` post-golden-scenarios.

P1 (reserved, stay `false` indefinitely this cycle): `FLAG_EXECUTOR_RESOLVER_V13_1`,
`FLAG_EPHEMERAL_SPECIALIST_V13_1`, `FLAG_CYCLE_GRANTS_V13_1`, `FLAG_ROLE_ATTRIBUTION_V13_1`,
`FLAG_AGENT_EXPERIENCE_V13_1`, `FLAG_FUNCTION_SKILLS_V13_1`.

---

## Frontend

New `frontend/lib/modules/company_runtime/{controllers,views}` +
`frontend/lib/data/services/company_runtime_service.dart` (extends `V13WorkspaceService`, same
`?workspace_id=` convention). Views: `work_inspector_view.dart`, `blocked_work_view.dart`,
`needs_you_view.dart`.

No `bindings/` directory, unlike `modules/finance/`/`modules/ai_team/`: those are reached through
GetX routes, which is what a `Bindings` class exists to serve. These three views are reached only as
index cases inside `dashboard_view.dart::_buildBodyContent()`, so each view self-registers its
controller with `Get.put(CompanyRuntimeController())` on first build. Adding a Binding with no route
to attach it to would be dead code.

**Needs You surfaces on the real home screen**: add a `NeedsYouPanel` to `hologram_hub_view.dart`'s
right rail (alongside the existing `MemoryCorePanel`/`NextActionsPanel`, fed by
`CompanyRuntimeService.getNeedsYou()`, top 3 items) — not `dashboard_view.dart`, which is pure nav
chrome.

**Nav gating** reuses the exact two-point pattern already in `dashboard_view.dart`: new `_NavItem`s with
`flagKey` added to the existing `Work` `_NavGroup`; `_buildBodyContent()`'s existing
`FeatureNotEnabledView` fallback needs no new logic, just new index cases.

**Voice commands**: add `work_inspector`/`needs_you`/`blocked_work` cases to
`HologramHubController::handleVoiceNavigation` (currently only 4 cases: `tasks`, `vault`, `strategy`,
`next_actions`), plus matching whitelist entries in `services/realtime_agent/tools.py::NAVIGATION_TARGETS`.

**Noted risk, not scheduled**: `finance_view.dart`'s Books/Reports/Settings tabs are still static
placeholders with no backend wiring (pre-existing V13 debt). Sprint 3's Finance exception wiring is
fully consumable through Needs You + LiveKit without touching this, but if a founder needs to *see*
Finance exceptions inside the Finance tab itself, that gap must close first.

---

## LiveKit Tools

New `backend/app/modules/company_runtime/tools.py`, following the exact existing pattern
(`@register(namespace, name, flag_key=)` → wrapper closure in `services/realtime_agent/tools.py::build_tools()`
→ filtered by `available_tools()`):

`runtime.get_status` (Sprint 1), `work.review`/`work.rework` (Sprint 1), `runtime.get_dag` (Sprint 2),
`runtime.get_blockers`/`runtime.resolve_blocker` (Sprint 3), `runtime.get_needs_you` (Sprint 3),
`runtime.create_handoff` (Sprint 4), `work.get_inspector` (Sprint 4), `runtime.get_checkpoint_status`
(Sprint 5, read-only — checkpoint/resume stay system-triggered), `runtime.classify_intent` (Sprint 6,
internal use).

This directly answers the spec's example commands: "What is blocked?" → `runtime.get_blockers`; "What
needs me?" → `runtime.get_needs_you`; "Why is Marketing waiting?" → `runtime.get_dag` +
`runtime.get_status`.

**Test coverage — do not repeat the existing gap.** The 4 pre-existing voice tools
(`get_cycle_status`/`get_weekly_mission`/`get_function_status`/`get_finance_snapshot`) have zero test
coverage today. Every new tool ships with a `test_runtime_tools.py` unit test (mirrors
`test_feature_flags.py`'s `MagicMock` style) and a `services/realtime_agent/tests/test_tools.py` entry in
the same sprint it lands — no deferred test debt this time.

---

## Sprint 1 Acceptance Criteria (first shippable slice)

1. With Sprint 1 flags off, every existing `Task`/`Outcome` flow is byte-for-byte unchanged — full
   existing test suite passes with zero regressions.
2. `TaskStateService.transition` raises on an illegal transition (e.g. `todo → done` directly) and
   writes exactly one audit-log row with `actor_id`/`reason` on every legal transition.
3. Work Contract endpoint sets fields on the existing `Outcome` row (no new row) and creates one
   `OkrLink` row per `linked_kr_id` — verified by `OkrLink` count, not a JSONB array.
4. Review `ACCEPTED` sets `Outcome.status="completed"` and (if linked) `Task.status="done"` via
   `TaskStateService`.
5. Review `REWORK_REQUIRED` increments `rework_count` and sets `Task.status="in_progress"`; a full
   reject→rework→re-review→accept loop is a single integration test.
6. Rework count hitting the configured cap rejects further `REWORK_REQUIRED` with a clear error.
7. No existing response field changes shape when flags are off — only new nullable fields appear.

---

## Explicitly Deferred / Not Built

OpenOPC as a runtime dependency (patterns only, never imported); talent/skill/company-package
marketplaces; office animation / large auto-org-chart (existing `FLAG_ADVANCED_ORG_CHART_V13` already
covers the hide surface); agent free-chat rooms; a generic `Approval`/`PolicyEngine` (existing 3
domain-specific approval tables stay separate by design, composed only at the Needs You read layer);
External Channel Gateway (Telegram/Zalo/Email/Slack — stub only, no flags since nothing exists to gate);
all P1 workforce-intelligence items (ExecutorResolver, Ephemeral Specialists, Cycle Grants, Contribution
Evaluation, Agent Experience, Function Skills, Role Attribution).

---

## ADRs

`ADR-V13-1-001` (Task+Outcome as WorkItem, no new table) · `ADR-V13-1-002` (TaskDependency revived, not
recreated) · `ADR-V13-1-003` (flat `modules/company_runtime/`, not nested) · `ADR-V13-1-004` (Review ≠
Approval, they compose) · `ADR-V13-1-005` (Needs You is a read-time pointer table) · `ADR-V13-1-006`
(`TaskStateService` guards a plain string column, audited via existing `write_audit_log`) ·
`ADR-V13-1-007` (`CompanyRuntimeManager` is a coordinator, not a second execution engine) ·
`ADR-V13-1-008` (no flags for OpenOPC/marketplace/office-animation/agent-free-chat — nothing to gate).

---

## Verification

- **Backend**: `cd backend && pytest app/tests -x -q` after each sprint; new `backend/app/tests/company_runtime/` suite covers state transitions, cycle detection, checkpoint/resume, and the 3 golden-scenario integration tests (Beta-Launch-style decomposition, Finance exception, Marketing rework, Runtime resume, Cross-function blocker — adapted from the spec's own scenarios).
- **Migrations**: `alembic upgrade head` against a fresh dev Postgres after each new migration file, per `DEPLOYMENT.md`'s documented recovery sequence — required before any migration is marked done (this was skipped for several V13 migrations per the existing audit; do not repeat that gap).
- **Feature flags**: manually toggle each `*_v13_1` flag via the existing `/platform/feature-flags` endpoint per sprint; confirm `FeatureNotEnabledView` renders correctly when off and the real view renders when on.
- **Frontend**: `cd frontend && flutter test && flutter analyze` after each sprint; manually launch the app and confirm the Needs You panel appears on the Hub screen and the Work Inspector/Blocked Work nav items are properly flag-gated.
- **LiveKit**: `services/realtime_agent/tests/test_tools.py` extended per new tool; manually exercise at least "What is blocked?" and "What needs me?" against a running voice session before Sprint 6's flag flip.
- **End-to-end**: do not flip `company_runtime_v13_1` to `true` globally until all 5 golden scenarios (Beta Launch decomposition, Finance Exception, Marketing Rework, Runtime Resume, Cross-Function Blocker) pass by hand against one Developer Workspace, per the spec's own rollout strategy.

---

## Implementation Status

Verified 2026-08-13 against the working tree.

### Delivered

| Sprint | Scope | State |
|---|---|---|
| 1 | State machine, Work Contract, Review/Rework | Done — `state_service.py`, `contract_service.py`, `review_service.py`, `work_reviews`, six new `Outcome` columns |
| 2 | Dependency runtime | Done — `dependency_service.py`, `TaskDependency` revived with `dependency_type`/`status` |
| 3 | Blocker, BlockerRouter, Needs You, Finance exception wiring | Done — `blockers`/`needs_you_items`; `detect_exceptions()` now has a real write-path caller in `transactions_router.py` and raises a `FINANCE_EXCEPTION` blocker on `severity="ERROR"` |
| 4 | Structured Handoff, Work Inspector | Done — `handoffs`, inspector composition endpoint, plus `POST /devices/jobs/{job_id}/resolve-approval` closing the `WAITING_APPROVAL` gap |
| 5 | Runtime Checkpoint / Resume | Done — `runtime_checkpoints`, `checkpoint_service.py` |
| 6 | Intent classifier, decomposition, `CompanyRuntimeManager` | Done — code complete; **the `v13_013` flag flip is still pending the manual golden-scenario run** |
| 7-8 | P1 workforce intelligence | Deferred as planned — six reserved flags seeded `false`, no schema, no code |

Migrations `v13_007_contracts` → `v13_013_flag_defaults` exist with an unbroken `down_revision`
chain from `v13_006_defaults`. All eight ADRs are written. `DEPLOYMENT.md` has a V13.1 section
covering the chain, the deliberate `v13_012`/`v13_013` split, and the realtime-agent restart
requirement.

**Automated verification**: backend `427 passed, 3 skipped`; `company_runtime` suite `28 passed`
(including all five golden scenarios); `services/realtime_agent` `44 passed`; Flutter
`163 passed` and `flutter analyze` clean.

### Two deviations found during verification, both fixed

**1. The LiveKit voice layer was only one-third wired.** All eleven tools were registered in
`tool_registry` via `@register`, and the backend unit tests passed — but `build_tools()` in
`services/realtime_agent/tools.py` had no wrapper closures for any of them, and `build_tools`
filters its wrapper dict by qualified name, so a tool with no wrapper is silently dropped rather
than raising. Every headline voice command in the spec ("What is blocked?", "What needs me?") was
therefore uncallable. Separately, `NAVIGATION_TARGETS` was never extended, so the
`needs_you`/`blocked_work`/`work_inspector` cases already present in
`HologramHubController::handleVoiceNavigation` were unreachable — the server rejected those
targets before they could ever be published.

Fixed: ten wrapper closures added (`runtime.classify_intent` stays registry-only by design), the
three navigation targets whitelisted, the `open_navigation` docstring updated, and eleven
delegation tests plus `test_every_registered_tool_has_a_voice_wrapper` added — the last one exists
specifically so this silent-drift failure mode cannot recur.

**2. `PUT /tasks/{id}` routed every status change through `TaskStateService` with no gate.** The
plan specifies routing "when the flag is on and the task has a linked `Outcome`"; the
implementation guarded unconditionally. Because `tasks_view.dart` is a three-column Kanban
(`todo`/`in_progress`/`done`) with free drag-and-drop, and `todo → done` is deliberately illegal in
the transition map, dragging a card straight to Done returned HTTP 400 and silently reverted —
with every V13.1 flag off. That breaks Sprint 1 acceptance criterion 1.

Fixed: extracted `_uses_state_machine()`, which requires both `FLAG_WORKITEM_STATE_MACHINE_V13_1`
and a linked `Outcome`; tasks without a Work Contract keep pre-V13.1 behaviour exactly.
`test_task_router_gating.py` covers all three branches.

### Migration verification — done

The full chain was executed from empty against a throwaway Postgres
(`javis_v131_verify`, created and dropped for the purpose; the shared dev database was never
touched and remains at `v13_006_defaults`). `alembic upgrade head` ran clean end to end, baseline
through `v13_013_flag_defaults`. Post-conditions confirmed by query:

- `work_reviews`, `blockers`, `needs_you_items`, `handoffs`, `runtime_checkpoints` all created
- all six new `outcomes` columns present, both new `task_dependencies` columns present
- `feature_flags` ends at exactly 13 `*_v13_1` rows `true` (P0) and 6 `false` (P1 reserved)

### Remaining gates before `company_runtime_v13_1` goes global

1. Apply the chain to the actual target database. The shared dev DB is deliberately still at
   `v13_006_defaults` — nothing in this delivery has been applied to it.
2. Run the five golden scenarios by hand against one Developer Workspace. They pass as automated
   tests; the spec's rollout strategy additionally requires the manual pass.
3. Only then run `v13_013_flag_defaults` (or flip the P0 flags through `/platform/feature-flags`).
   To stop short of the gate, `alembic upgrade v13_012_runtime_flags`.
4. Restart `services/realtime_agent` after deploying — it is a separate deploy unit and imports
   `app.modules.company_runtime` at process start.
5. Exercise "What is blocked?" and "What needs me?" against a live voice session.

### Known open debt, unchanged by this work

`finance_view.dart`'s Books/Reports/Settings tabs remain static placeholders (pre-existing V13
debt). Finance exceptions are fully consumable through Needs You and the voice tools, so this does
not block V13.1 — but a founder cannot yet see them inside the Finance tab itself.
