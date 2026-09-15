# Foundation Correctness Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm Workspace/Project lifecycle, OKR, Weekly operating loop, Task và 13 Executive Advisory Board roles đúng contract, kín Project scope, có audit/CAS và đủ bằng chứng release trước khi nối Skill layer mới.

**Architecture:** Giữ `services/company` là business truth. Canonical Project Operating Loop tiếp tục nằm ở `/operations/projects/:projectId/operating-loop/*`; Flutter giải mã chính xác DTO server thay vì backend tạo shape giả cho client. Role/Office thuộc Workspace; Project chỉ dùng `project_agent_deployments` để deploy Workspace Agent/Skill với scope dữ liệu, budget và policy hẹp. Weekly chuyển trạng thái bằng service transaction + CAS, không tự động chuyển lifecycle hay thực hiện business work.

**Tech Stack:** Encore.ts, TypeScript, Drizzle/PostgreSQL, Vitest; Flutter/Dart/GetX, `MvpRequestClient`; Node contract generators; existing Python Agent Platform chỉ dùng để kiểm tra exact pins trong runtime authority.

**Spec:** `docs/superpowers/specs/2026-09-14-foundation-correctness-remediation-design.md`.

## Execution status — 2026-09-15

### Verified in the local disposable/runtime environment

- `make contracts-check` — passed after regenerating the stale Python binding
  for the canonical Executive Role catalog; no generated file was hand-edited.
- `cd services/company && npm run typecheck` — passed.
- Focused Company tests — 5 files, 41 tests passed through Encore's real test
  runtime: Operating Loop, task scope/advance, Executive Role, and deliberation.
- `pytest tests/e2e/test_project_operating_loop_scope_and_authority.py -q` —
  2 tests passed against a real Company process after its fixture applied
  Company migrations. It proves one Workspace/two Project Operating Loop
  isolation, rejected foreign task/cycle mutations, visible weekly CAS, and
  that a Workspace CFO Office without a Project deployment cannot frame.
- `make frontend-api-contract-check` — 11 passed, 2 skipped; Flutter literals
  match enabled MVP contract routes.
- `cd frontend && flutter test test/modules/projects test/modules/hologram_hub`
  — 206 tests passed. Logs for deliberately removed R1 workforce routes are
  test-fixture diagnostics, not successful hidden calls.

### Implemented, but deliberately not represented as release-complete

- Task 8 separates Workspace Office state from Project deployment state,
  rejects malformed deployment DTOs, and never presents global `ACTIVE` as
  a Project-effective role. The Flutter deployment service accepts only an
  exact `workspaceAgentId`; it sends neither a role key nor a client-chosen
  spec/Skill.
- The public contract has no Founder endpoint to create or list a deployable
  `WorkspaceAgent` with that exact ID. A truthful deploy control, and the
  positive E2E assertion "Agent deployed in A cannot authorize B", cannot
  be seeded through public HTTP. The new E2E test does not bypass this via a
  service internal or direct database write.
- The HTTP surface has no list/read endpoint for `cycle_week_events`. Public
  E2E proves a stale CAS cannot advance the visible cycle twice, but cannot
  claim an exact hidden event-row count without an inspectable timeline route.
- `make services-migrate-company` is configuration-blocked in the sandbox
  because `WORKSPACE_MIGRATOR_DATABASE_URL` is absent there. The E2E fixture's
  disposable-runtime migration did succeed. `make verify` was run and reached
  `mypy`, where it remains red with 33 errors in 14 files (including the
  previously identified `apps/cosa/api/project_activity_routes.py` repository
  contract defects). `make e2e-cross-plane-smoke` remains unrun by design:
  a later release gate must not be represented as evidence while its preceding
  aggregate gate is red.

## Global Constraints

- Workspace là tenant boundary; mọi business record/run/write phải có Project rõ ràng. Không suy diễn Project từ active-project local storage, record đầu tiên, prompt hay Workspace.
- `NEW` Project mặc định `P0_DISCOVERY`. `ONBOARD_EXISTING` cho Founder/co-founder chọn baseline P0…P6 kèm rationale và event `PROJECT_INITIALIZED`; sau baseline, chỉ lifecycle CAS được đổi stage. Một bước tiến, rollback có rationale, không auto-transition.
- Handler chỉ parse/authorize/validate rồi gọi service. Không truy cập Drizzle/schema trực tiếp ở handler.
- Public failures dùng `APIError`; stale CAS phải không tạo event, không retry bằng phiên bản mới tự động.
- Migration chỉ expand. Không drop bảng `project_executive_role_activations`, `workspace_executive_role_activations` hay route legacy trong release này; không hồi sinh bảng Project role activation cũ làm authority.
- 13 role chỉ advisory `L1_PROPOSE`, capability-empty. Không cấp quyền tool/side-effect khi thực hiện plan này.
- `shared/contracts/mvp-surface.json` là contract. Sau sửa route, chạy generator; không thêm allowlist để che drift.
- Không hand-edit generated profile. Chuỗi `generate -> format check -> generate --check` phải ổn định.
- Mỗi Task chỉ stage/commit đúng file của Task đó sau khi focused test xanh. Không commit/push nếu Founder chưa yêu cầu.

---

## File Structure

- `scripts/gen-startup-team-profiles.mjs` — sinh Python deterministic, ruff-stable.
- `apps/cosa/agents/startup_team_profiles_generated.py` — output generator, không sửa tay.
- `services/company/operations/services/project.service.ts` — ép stage mặc định khi tạo Project.
- `services/company/operations/services/task.service.ts` — bắt buộc project và khoá mọi mutation theo `(workspace_id, project_id, task_id)`.
- `services/company/operations/services/project-operating-loop.service.ts` — DTO canonical, hierarchy query, task scope và weekly state machine.
- `services/company/operations/handlers/project-operating-loop.handler.ts` — body/route typed cho KR, initiative, task status, week transition.
- `services/company/shared/db/schema/operations.ts` — schema event Weekly; reuse schema `workspace_agents` / `project_agent_deployments` có sẵn cho deployment authority.
- `services/company/operations/migrations/026_project_lifecycle_initialization_event.up.sql` — lifecycle baseline event expand-only.
- `services/company/operations/migrations/026_project_lifecycle_initialization_event.down.sql` — rollback only before initialization data exists.
- `services/company/operations/migrations/027_operating_loop_week_state.up.sql` — event schema Weekly expand-only.
- `services/company/operations/migrations/027_operating_loop_week_state.down.sql` — rollback chỉ dùng khi release chưa có Weekly event mới.
- `services/company/operations/services/{executive-role-activation,workspace-executive-role-activation,executive-deliberation,founder-agent-compatibility}.service.ts` — Workspace office state, Project deployment authority và runtime re-check.
- `shared/contracts/mvp-surface.json` + generated TS/Dart contract artifacts — route surface chính thức.
- `frontend/lib/modules/projects/{models,services,controllers,views}/project_operating_loop*` — DTO typed, actions đúng body, truthful UI.
- `frontend/lib/core/lifecycle/widgets/lifecycle_settings_section.dart` và `frontend/lib/modules/projects/views/project_operating_loop_view.dart` — reload lifecycle sau mutation, không gửi stage version stale.
- `services/company/operations/tests/{project-operating-loop,task,project-lifecycle,workspace-executive-role-activation,executive-role-activation,executive-deliberation}.test.ts` — unit/integration negative cases.
- `frontend/test/modules/projects/{models,services,controllers,views}/` — decoder và UI contract tests mới.
- `tests/e2e/test_project_operating_loop_scope_and_authority.py` — PostgreSQL/process proof hai Project cùng Workspace.

---

### Task 1: Làm generator profile deterministic để contract gate đáng tin

**Files:**
- Modify: `scripts/gen-startup-team-profiles.mjs`
- Modify: `apps/cosa/agents/startup_team_profiles_generated.py` (chỉ bằng generator)
- Test: `scripts/gen-startup-team-profiles.mjs` through `make contracts-check`

**Consumes:** Canonical startup-team profiles input hiện có.

**Produces:** `genPy()` luôn phát đúng bytes mà ruff format check chấp nhận; `--check` phát hiện drift thật, không phát hiện formatter-induced drift.

- [ ] **Step 1: Viết regression assertion cho round trip generator**

Thêm một test Node hoặc Make target hẹp chạy đúng chuỗi sau trên output generator trong working tree:

```text
node scripts/gen-startup-team-profiles.mjs
ruff format --check apps/cosa/agents/startup_team_profiles_generated.py
node scripts/gen-startup-team-profiles.mjs --check
```

Expected before implementation: bước cuối FAIL vì `JSON.stringify()` tạo dict một dòng không trùng output formatter.

- [ ] **Step 2: Chạy regression để xác nhận đỏ**

Run: `make contracts-check`

Expected: only startup-team Python generated-file check reports stale; do not regenerate/commit by hand to hide it.

- [ ] **Step 3: Sửa `genPy()` bằng Python literal renderer ổn định**

Thay JSON one-line bằng helper render đệ quy với quote JSON, indent bốn spaces và trailing commas mà ruff không biến đổi. Shape đầu ra phải giữ nguyên type annotations:

```js
function pyValue(value, indent = 0) {
  if (typeof value === "string") return JSON.stringify(value);
  const pad = " ".repeat(indent);
  return `{\n${Object.entries(value)
    .map(([key, item]) => `${" ".repeat(indent + 4)}${JSON.stringify(key)}: ${pyValue(item, indent + 4)},`)
    .join("\n")}\n${pad}}`;
}
```

Use helper for both list and map entries; do not invoke a formatter from the generator.

- [ ] **Step 4: Regenerate and prove green**

Run:

```bash
node scripts/gen-startup-team-profiles.mjs
make contracts-check
make lint
node scripts/gen-startup-team-profiles.mjs --check
```

Expected: all commands pass and the final check leaves `git diff -- apps/cosa/agents/startup_team_profiles_generated.py` empty.

- [ ] **Step 5: Commit only generator/output/test scope**

```bash
git add scripts/gen-startup-team-profiles.mjs apps/cosa/agents/startup_team_profiles_generated.py
git commit -m "fix(contracts): make startup profile generation deterministic"
```

**Rollback:** revert this single commit. It changes no runtime data/schema.

### Task 2: Tạo Project theo mode onboarding rõ ràng và khóa Task mutations theo Project

**Files:**
- Create: `services/company/operations/migrations/026_project_lifecycle_initialization_event.up.sql`
- Create: `services/company/operations/migrations/026_project_lifecycle_initialization_event.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/company/operations/services/project.service.ts`
- Modify: `services/company/operations/services/task.service.ts`
- Modify: `services/company/operations/services/project-operating-loop.service.ts`
- Modify: `services/company/operations/handlers/project-operating-loop.handler.ts`
- Test: `services/company/operations/tests/project-lifecycle.service.test.ts`
- Test: `services/company/operations/tests/task.service.test.ts`
- Test: `services/company/operations/tests/task-advance.test.ts`
- Test: `services/company/operations/tests/project-operating-loop.service.test.ts`

**Consumes:** Existing composite Project FK and `verifyProjectInWorkspace`.

**Produces:** Founder có thể khai báo baseline P đúng khi onboarding Project sẵn có mà không bịa lịch sử; mọi Task write/advance vẫn bị khoá theo exact Project.

- [ ] **Step 1: Add failing Project creation and onboarding-baseline tests**

Add these cases:

```ts
// NEW ignores no stage; persisted baseline is P0.
await createProjectService(founderCtx, { title: "Greenfield", creationMode: "NEW" });

// Existing company may state its real current stage exactly once.
await createProjectService(founderCtx, {
  title: "Existing business",
  creationMode: "ONBOARD_EXISTING",
  initialLifecycleStage: "P4_GO_TO_MARKET",
  initializationRationale: "Founder attests product is already in market",
});
```

Assert the first Project is P0; the second is P4 with `stageVersion = 1` and
one `PROJECT_INITIALIZED` event with `fromStage = null`. Assert member/admin
without Founder authority, missing rationale, invalid stage, and a second
baseline attempt all fail. Add a normal transition test showing P4→P5 still
requires `expectedStageVersion = 1`.

- [ ] **Step 2: Run Project tests red**

Run: `cd services/company && npx vitest run operations/tests/project-lifecycle.service.test.ts`

Expected: current free-form `lifecycleStage` has no `NEW`/`ONBOARD_EXISTING`
distinction and cannot create an honest initialization event.

- [ ] **Step 3: Replace free-form stage input with a typed initialization command**

Replace public `lifecycleStage?: string` with:

```ts
type ProjectCreationMode = "NEW" | "ONBOARD_EXISTING";
interface CreateProjectRequest {
  title: string;
  creationMode?: ProjectCreationMode;
  initialLifecycleStage?: ProjectLifecycleStage;
  initializationRationale?: string;
}
```

`NEW` inserts `P0_DISCOVERY`. `ONBOARD_EXISTING` is Founder/co-founder only,
requires enum-valid `initialLifecycleStage` and non-empty rationale, then
inserts that stage and append-only `PROJECT_INITIALIZED` event inside the same
transaction. Make `fromStage` nullable only for this event type; do not encode
a false P0→Pn transition. Existing lifecycle transition service remains the
only writer after initialization.

Migration 026 must make this semantic explicit:

```sql
ALTER TABLE strategy.project_lifecycle_events
  ALTER COLUMN from_stage DROP NOT NULL,
  ADD COLUMN event_type varchar(32) NOT NULL DEFAULT 'TRANSITION',
  ADD COLUMN initialization_source varchar(64);
```

The initialization insert uses `event_type = 'PROJECT_INITIALIZED'`,
`from_stage = NULL`, `from_stage_version = 0`, and
`initialization_source = 'FOUNDER_ONBOARDING'`. The down migration refuses to
restore `NOT NULL` while any initialization event exists; it never deletes
audit history to make rollback convenient.

- [ ] **Step 4: Add two-Project task negative tests**

Create Workspace W with Project A/B, a commitment/initiative/task in B, then assert all of these fail through A:

```ts
await expect(createTaskService({ workspaceId: W, projectId: A, weeklyCommitmentId: commitmentB, title: "x" }, auth))
  .rejects.toMatchObject({ code: "invalid_argument" });
await expect(advanceTaskService(ctx, { projectId: A, taskId: taskB, status: "DONE" }))
  .rejects.toMatchObject({ code: "not_found" });
```

Also assert create/proposal without `projectId` fails `PROJECT_CONTEXT_REQUIRED`; it must never select the first Project.

- [ ] **Step 5: Make the service signatures fail closed**

Make `projectId: string` required on `CreateTaskParams` and AI proposal input. Delete first-project fallback. Before insert/update, verify Project in Workspace and verify every supplied commitment/initiative/weekly plan belongs to that Project. Change `advanceTaskService`, schedule and status helpers to accept `projectId` and add `eq(tasks.projectId, pId)` to select/update predicates.

```ts
where(and(
  eq(tasks.id, taskId),
  eq(tasks.workspaceId, wsId),
  eq(tasks.projectId, pId),
  isNull(tasks.deletedAt),
));
```

Route `advanceTaskApi` must pass its `params.projectId` into the service rather than only validating the URL Project beforehand.

- [ ] **Step 6: Run focused green gates**

Run:

```bash
cd services/company && npx vitest run operations/tests/project-lifecycle.service.test.ts operations/tests/task.service.test.ts operations/tests/task-advance.test.ts operations/tests/project-operating-loop.service.test.ts
npm run typecheck
make company-boundary-check
```

Expected: positive same-Project flow passes; all cross-Project and missing-context cases fail before mutation/event.

- [ ] **Step 7: Commit scope integrity only**

```bash
git add services/company/operations/migrations/026_project_lifecycle_initialization_event.* services/company/shared/db/schema/operations.ts services/company/operations/services/project.service.ts services/company/operations/services/project-lifecycle.service.ts services/company/operations/services/task.service.ts services/company/operations/services/project-operating-loop.service.ts services/company/operations/handlers/project.handler.ts services/company/operations/handlers/project-lifecycle.handler.ts services/company/operations/handlers/project-operating-loop.handler.ts services/company/operations/tests
git commit -m "fix(operations): add honest project onboarding baseline and scope task writes"
```

**Rollback:** disable `ONBOARD_EXISTING` for new requests if necessary; retain
already-written initialization events as audit truth. Clients that omit
`projectId` continue to receive explicit failure instead of wrong-Project
writes.

### Task 3: Chốt contract canonical của Project Operating Loop trước UI

**Files:**
- Modify: `services/company/operations/services/project-operating-loop.service.ts`
- Modify: `services/company/operations/handlers/project-operating-loop.handler.ts`
- Modify: `shared/contracts/mvp-surface.json`
- Modify: generated contract artifacts through existing generator
- Test: `services/company/operations/tests/project-operating-loop.handler.test.ts`
- Test: `services/company/operations/tests/project-operating-loop.service.test.ts`

**Consumes:** DTO wrappers already returned by `getProjectOperatingLoop`.

**Produces:** One typed HTTP surface including KR, initiative and task-status writes; no invisible backend route or body-key drift.

- [ ] **Step 1: Write exact response/body fixtures from server DTO**

In handler tests, assert one real response shape:

```ts
expect(loop).toMatchObject({
  project: { id: projectId, lifecycleStage: baselineStage, stageVersion: 1 },
  objectives: [{ objective: { id: objectiveId }, keyResults: [{ keyResult: { id: keyResultId }, initiatives: [{ id: initiativeId }] }] }],
  activeCycle: { id: cycleId, currentWeek: 1 },
  currentWeek: { weekNo: 1 },
  commitments: [{ weeklyPlanId: weekId }],
  tasks: [{ projectId }],
});
```

Add negative body tests: Objective accepts `why`, commitment accepts `plannedEffort`; old client-only keys `description` and `targetConfidence` are rejected or ignored only after documented compatibility decision.

- [ ] **Step 2: Run handler tests red**

Run: `cd services/company && npx vitest run operations/tests/project-operating-loop.handler.test.ts`

Expected: current `mvp-surface` lacks separate key-result/initiative/task-status entries and client-body fixture exposes drift.

- [ ] **Step 3: Register every live canonical endpoint**

Add explicit contract entries and generated enum bindings for:

```text
POST /operations/projects/:projectId/operating-loop/key-results
POST /operations/projects/:projectId/operating-loop/initiatives
PATCH /operations/projects/:projectId/operating-loop/tasks/:taskId/status
```

Keep route names equal to handler paths. Do not substitute generic `/operations/key-results/:id` calls in the Project loop because it loses Project-path enforcement.

- [ ] **Step 4: Tighten read model without changing its JSON shape**

Filter KRs in SQL by objective IDs rather than selecting all Workspace KRs and filtering in memory. Extend `TaskDto` only with fields actually surfaced from its table (`weeklyPlanId`, `keyResultId` when present) and test nullable values. Do not add evidence/decision fields to pretend they exist in this endpoint.

- [ ] **Step 5: Regenerate and pass contract tests**

Run:

```bash
node scripts/gen-mvp-contracts.mjs
make frontend-api-contract-check
cd services/company && npx vitest run operations/tests/project-operating-loop.handler.test.ts operations/tests/project-operating-loop.service.test.ts
```

Expected: generated Dart/TS names and route inventory contain every call made by the Project loop.

- [ ] **Step 6: Commit contract slice**

```bash
git add services/company/operations/services/project-operating-loop.service.ts services/company/operations/handlers/project-operating-loop.handler.ts shared/contracts docs/architecture/generated frontend/lib/core/network/mvp_endpoints.g.dart
git commit -m "fix(contracts): align project operating loop surface"
```

**Rollback:** revert the contract slice as one commit; callers have not moved until Task 4 lands.

### Task 4: Làm Flutter Project Operating Loop giải mã và hiển thị dữ liệu thật

**Files:**
- Modify: `frontend/lib/modules/projects/models/project_operating_loop.dart`
- Modify: `frontend/lib/modules/projects/services/project_operating_loop_service.dart`
- Modify: `frontend/lib/modules/projects/controllers/project_operating_loop_controller.dart`
- Modify: `frontend/lib/modules/projects/views/project_operating_loop_view.dart`
- Modify: `frontend/lib/modules/projects/views/widgets/{okr_section,cycle_week_section,commitment_task_section,evidence_decision_section}.dart`
- Create: `frontend/test/modules/projects/models/project_operating_loop_test.dart`
- Create: `frontend/test/modules/projects/services/project_operating_loop_service_test.dart`
- Test: `frontend/test/modules/projects/controllers/project_operating_loop_controller_test.dart`

**Consumes:** Task 3 generated endpoint names and fixture JSON.

**Produces:** UI is a typed projection of the server’s exact response, refreshes after every mutation, and makes unavailable data explicit.

- [ ] **Step 1: Write a failing decoder fixture copied from Task 3**

Assert that decoding produces non-empty `objective.id`, key-result IDs, initiatives, root `currentWeek`, root commitments and root tasks. Assert `ProjectSummary` retains `lifecycleStage`, `stageVersion`, and `stageEnteredAt`.

- [ ] **Step 2: Run decoder test red**

Run: `cd frontend && flutter test test/modules/projects/models/project_operating_loop_test.dart`

Expected: current model drops wrapper fields, current Week/commitments, and lifecycle fields.

- [ ] **Step 3: Replace fantasy model with exact nested DTO types**

Use explicit types instead of dynamic maps:

```dart
class LoopObjectiveTree {
  final LoopObjective objective;
  final List<LoopKeyResultTree> keyResults;
}

class ProjectOperatingLoop {
  final ProjectSummary project;
  final List<LoopObjectiveTree> objectives;
  final LoopActiveCycle? activeCycle;
  final LoopWeek? currentWeek;
  final List<LoopCommitment> commitments;
  final List<LoopTask> tasks;
}
```

Decode server keys exactly. Remove `evidence`/`decisions` from this model and replace its tab with a clear link to the separately scoped Project Activity surface, or omit the tab; never render an empty list as if it were confirmed backend data.

- [ ] **Step 4: Align all client request bodies and expose missing actions**

Change Objective `description` to `why`; Commitment `targetConfidence` to `plannedEffort`. Add typed client/controller methods for Key Result, Initiative and task-status update using Task 3 endpoints. Each successful mutation calls `loadLoop()`; conflict reloads then preserves an error message.

- [ ] **Step 5: Make lifecycle section refresh rather than retain stale state**

Pass an `onTransitioned` callback that awaits `controller.loadLoop()` and reloads lifecycle state from the endpoint. Do not reuse a cached `stageVersion` after PATCH succeeds.

- [ ] **Step 6: Run Flutter green tests**

Run:

```bash
cd frontend && flutter test test/modules/projects/models/project_operating_loop_test.dart test/modules/projects/services/project_operating_loop_service_test.dart test/modules/projects/controllers/project_operating_loop_controller_test.dart
flutter analyze --no-pub
```

Expected: fixture backed by actual server DTO renders all three operating areas and body-key tests use only registered fields.

- [ ] **Step 7: Commit truthful UI only**

```bash
git add frontend/lib/modules/projects frontend/test/modules/projects frontend/lib/core/network/mvp_endpoints.g.dart
git commit -m "fix(frontend): render canonical project operating loop"
```

**Rollback:** revert after Task 3 if required. The prior UI is known untruthful; rollback must be paired with hiding the page, not restoring mock-shaped content.

### Task 5: Hoàn thiện Weekly state machine có CAS và timeline

**Files:**
- Create: `services/company/operations/migrations/027_operating_loop_week_state.up.sql`
- Create: `services/company/operations/migrations/027_operating_loop_week_state.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/company/operations/services/project-operating-loop.service.ts`
- Modify: `services/company/operations/handlers/project-operating-loop.handler.ts`
- Modify: `shared/contracts/mvp-surface.json`
- Test: `services/company/operations/tests/project-operating-loop.service.test.ts`
- Test: `services/company/operations/tests/mvp-okr-twelve-week.test.ts`

**Consumes:** `twelve_week_cycles.current_week`, existing `weekly_plans` reflection/scores, Task 3 contract pattern.

**Produces:** A founder-driven Weekly close/advance flow that is atomic, replay-safe and visible in a durable timeline.

- [ ] **Step 1: Add red tests for weekly transition invariants**

Cover: cycle creation produces weeks `1..durationWeeks`; close week 1 with expected `1` moves once to 2 and emits one event; a second command with expected `1` fails without event; a Project B cycle cannot advance through Project A; closing N marks cycle `COMPLETED` and does not change Project lifecycle.

- [ ] **Step 2: Run Weekly tests red**

Run: `cd services/company && npx vitest run operations/tests/project-operating-loop.service.test.ts operations/tests/mvp-okr-twelve-week.test.ts`

Expected: no public advance command/event storage exists.

- [ ] **Step 3: Add append-only weekly event schema**

Create `operating.cycle_week_events` with `id`, `workspace_id`, `project_id`, `cycle_id`, `week_no`, `event_type`, `actor_id`, `expected_current_week`, `payload jsonb`, `occurred_at`. Add composite Project/Cycle FK or equivalent service guard and an index `(workspace_id, project_id, cycle_id, occurred_at)`. Add Drizzle table; do not alter/delete old plan rows.

- [ ] **Step 4: Centralize deterministic cycle materialization**

Make `createCycleAuthorized` transactionally create cycle plus all empty `weekly_plans` 1..N. Update `generateCycleFromObjective` to call that same service with `sourceObjectiveId`, eliminating its duplicate week-creation loop. Leave commitments/tasks empty.

- [ ] **Step 5: Implement `advanceCycleWeekAuthorized` transactionally**

Add route and typed body:

```ts
PATCH /operations/projects/:projectId/operating-loop/cycles/:cycleId/week
{ expectedCurrentWeek: number, reflection: string, executionScore?: number, outcomeScore?: number }
```

Within one transaction: verify `(workspace, project, cycle)`, `status=ACTIVE`, and `currentWeek===expectedCurrentWeek`; update only the current plan’s review fields; append `WEEK_CLOSED`; either update `currentWeek + 1` and append `WEEK_ADVANCED`, or set cycle `COMPLETED` and append `CYCLE_COMPLETED`. A failed compare must roll back all writes.

- [ ] **Step 6: Regenerate contract and prove green**

Run:

```bash
node scripts/gen-mvp-contracts.mjs
cd services/company && npx vitest run operations/tests/project-operating-loop.service.test.ts operations/tests/mvp-okr-twelve-week.test.ts
make frontend-api-contract-check
```

Expected: no `/execution/*` client or legacy resize route is introduced/reopened.

- [ ] **Step 7: Commit migration/state-machine slice**

```bash
git add services/company/operations/migrations/027_operating_loop_week_state.* services/company/shared/db/schema/operations.ts services/company/operations/services/project-operating-loop.service.ts services/company/operations/handlers/project-operating-loop.handler.ts services/company/operations/tests shared/contracts
git commit -m "feat(operations): add auditable weekly cycle transitions"
```

**Rollback:** before production data is written, run paired down migration then revert. After data exists, disable route and use a forward corrective migration; never drop events.

### Task 6: Đưa Weekly actions vào Flutter mà không tự động hóa business decision

**Files:**
- Modify: `frontend/lib/modules/projects/services/project_operating_loop_service.dart`
- Modify: `frontend/lib/modules/projects/controllers/project_operating_loop_controller.dart`
- Modify: `frontend/lib/modules/projects/views/widgets/cycle_week_section.dart`
- Test: `frontend/test/modules/projects/services/project_operating_loop_service_test.dart`
- Test: `frontend/test/modules/projects/controllers/project_operating_loop_controller_test.dart`
- Create: `frontend/test/modules/projects/views/cycle_week_section_test.dart`

**Consumes:** Task 5 endpoint and exact loop DTO.

**Produces:** Founder may close the displayed current week after an explicit review; stale/failed result is visible, no week advances silently.

- [ ] **Step 1: Write widget tests for review confirmation**

Assert “Close week” opens a form requiring non-empty reflection, sends exact `expectedCurrentWeek`, disables duplicate submission, and on success shows next week only after reload. Assert a conflict shows server error and reloads current state.

- [ ] **Step 2: Run Flutter test red**

Run: `cd frontend && flutter test test/modules/projects/views/cycle_week_section_test.dart`

Expected: current UI lacks transition action/state handling.

- [ ] **Step 3: Add typed service/controller method**

```dart
Future<ApiResult<void>> closeCurrentWeek(
  String projectId,
  String cycleId, {
  required int expectedCurrentWeek,
  required String reflection,
  double? executionScore,
  double? outcomeScore,
});
```

Use generated `MvpEndpoint`; do not call raw route strings. Controller awaits response then `loadLoop()` on success or conflict.

- [ ] **Step 4: Build explicit review dialog and state display**

Show cycle number/duration, current week and completion state. The action is unavailable for a completed cycle. Do not add a timer, scheduled advance, or task/commitment auto-generation.

- [ ] **Step 5: Run green frontend checks**

Run:

```bash
cd frontend && flutter test test/modules/projects/services/project_operating_loop_service_test.dart test/modules/projects/controllers/project_operating_loop_controller_test.dart test/modules/projects/views/cycle_week_section_test.dart
flutter analyze --no-pub
```

- [ ] **Step 6: Commit Weekly UI**

```bash
git add frontend/lib/modules/projects frontend/test/modules/projects frontend/lib/core/network/mvp_endpoints.g.dart
git commit -m "feat(frontend): add explicit weekly review transition"
```

**Rollback:** hide the close action while retaining backend events/data; do not synthesize an inverse transition.

### Task 7: Giữ Executive Role ở Workspace, dùng Project Agent deployment cho phạm vi Project

**Files:**
- Modify: `services/company/operations/services/executive-role-activation.service.ts`
- Modify: `services/company/operations/services/workspace-executive-role-activation.service.ts`
- Modify: `services/company/operations/services/executive-deliberation.service.ts`
- Modify: `services/company/operations/services/founder-agent-compatibility.service.ts`
- Modify: `services/company/operations/services/founder-asset-deployment.service.ts`
- Modify: `services/company/operations/handlers/executive-role-activation.handler.ts`
- Modify: `services/company/operations/handlers/founder-asset-deployment.handler.ts`
- Modify: `shared/contracts/mvp-surface.json`
- Test: `services/company/operations/tests/executive-role-activation.service.test.ts`
- Test: `services/company/operations/tests/workspace-executive-role-activation.service.test.ts`
- Test: `services/company/operations/tests/executive-deliberation.service.test.ts`
- Test: `services/company/operations/tests/executive-role-activation.handler.test.ts`

**Consumes:** Workspace office rows, `workspace_agents`, existing
`project_agent_deployments`, `resolveProjectAgentAuthorityV2`, canonical role
catalog and stage presets.

**Produces:** CFO/CMO/… vẫn là Workspace Role. Project không có Role record
riêng; Project chỉ deploy Workspace Agent tương ứng với scope/policy riêng.
Role chỉ có thể tư vấn Project khi office, deployment và stage đều hợp lệ.

- [ ] **Step 1: Write red two-Project office/deployment tests**

Set Workspace CFO office ACTIVE and deploy the CFO Workspace Agent only to
Project A. Assert Project A is `EFFECTIVE`; Project B reports office ACTIVE
but `PROJECT_DEPLOYMENT_INACTIVE`, and frame deliberation for B fails
`EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE`. Deploy a non-persistent role to
a Project at a disallowed stage and assert frame fails
`EXECUTIVE_ROLE_STAGE_FORBIDDEN`. Send stale Workspace office version twice
and assert its activation event count remains one.

- [ ] **Step 2: Run role tests red**

Run:

```bash
cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts operations/tests/workspace-executive-role-activation.service.test.ts operations/tests/executive-deliberation.service.test.ts operations/tests/executive-role-activation.handler.test.ts
```

Expected: current Workspace ACTIVE state is projected as active everywhere and
deliberation still reads legacy `project_agent_assignments` directly.

- [ ] **Step 3: Define an effective Project advisory read model without a Project Role table**

Do not write `project_executive_role_activations`. Make
`getProjectExecutiveRoleStates` compose these fields from existing records:

```ts
interface ProjectExecutiveRoleView {
  roleKey: ExecutiveRoleKey;
  officeState: "ACTIVE" | "DISABLED" | "UNAVAILABLE";
  projectDeploymentState: "ACTIVE" | "INACTIVE" | "PAUSED" | "RETIRED";
  stageEligibility: "ALLOWED" | "NOT_SUGGESTED";
  effectiveState: "EFFECTIVE" | "OFFICE_DISABLED" | "DEPLOYMENT_INACTIVE" | "STAGE_FORBIDDEN";
  workspaceOfficeVersion: number;
  projectAgentDeploymentId?: string;
}
```

Resolve the Project side through `resolveProjectAgentAuthorityV2`; in SHADOW
mode retain its existing comparison telemetry, but do not make the old
`project_agent_assignments` the long-term authority.

- [ ] **Step 4: Add a public Founder-only Project Agent deployment command, not a Role bind command**

Expose the existing `deployAgentToProject` service through a public endpoint:

```text
POST /operations/projects/:projectId/agent-deployments
{ workspaceAgentId, capabilityOverrides?, idempotencyKey? }
```

It must require human Founder authority, validate the Workspace Agent belongs
to the caller Workspace, and use the existing deployment service transaction
and founder-asset event. Do not expose `/executive-roles/:roleKey/bind` or
create a Project Role mutation. Project deployment constrains the already
Workspace-owned agent; it does not create/activate a role.

- [ ] **Step 5: Make deliberation and worker authority resolve the deployment path**

Replace direct legacy assignment lookup in `frameDeliberation` and
`getDeliberationAuthority` with `resolveProjectAgentAuthorityV2` for the
current Project. Require: Workspace office ACTIVE; Project deployment ACTIVE;
stage policy allowed; returned agent asset/spec ID/version/hash equals the
catalog requirement; existing required Skill pins resolve exactly. Return
`EXECUTIVE_ROLE_OFFICE_DISABLED`,
`EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE`,
`EXECUTIVE_ROLE_STAGE_FORBIDDEN`, or `EXECUTIVE_ROLE_PIN_DRIFT`; never fall
back to another role/profile/spec.

- [ ] **Step 6: Make stage suggestion describe two separate Founder actions**

Return `workspaceOfficeToEnable`, `projectAgentsToDeploy`, and
`stageEligibleRoles`. A Project transition may suggest these actions but never
performs either. Existing Workspace activate/disable endpoints keep CAS and
make it explicit that office state affects the whole Workspace.

- [ ] **Step 7: Regenerate contracts and prove green**

Run:

```bash
node scripts/gen-mvp-contracts.mjs
cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts operations/tests/workspace-executive-role-activation.service.test.ts operations/tests/executive-deliberation.service.test.ts operations/tests/executive-role-activation.handler.test.ts
npm run typecheck
make frontend-api-contract-check
```

- [ ] **Step 8: Commit Workspace role/Project deployment authority slice**

```bash
git add services/company/operations/services/executive-role-activation.service.ts services/company/operations/services/workspace-executive-role-activation.service.ts services/company/operations/services/executive-deliberation.service.ts services/company/operations/services/founder-agent-compatibility.service.ts services/company/operations/services/founder-asset-deployment.service.ts services/company/operations/handlers/executive-role-activation.handler.ts services/company/operations/handlers/founder-asset-deployment.handler.ts services/company/operations/tests shared/contracts
git commit -m "fix(executive-board): scope workspace roles through project deployments"
```

**Rollback:** disable only the new public deployment route, keep existing
Workspace office state and deployment/event records, and do not reintroduce
Project Role activation as authority.

### Task 8: Sửa Flutter Executive Board thành Workspace Office + Project Deployment minh bạch

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/services/executive_advisory_board_service.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/executive_advisory_board_controller.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/executive_advisory_board_view.dart`
- Modify: `frontend/lib/modules/projects/services/executive_board_stage_suggestion_service.dart`
- Create: `frontend/lib/modules/projects/services/project_agent_deployment_service.dart`
- Modify: `frontend/lib/modules/projects/views/project_operating_loop_view.dart`
- Test: `frontend/test/modules/hologram_hub/services/executive_advisory_board_service_test.dart`
- Test: `frontend/test/modules/hologram_hub/controllers/executive_advisory_board_controller_reload_test.dart`
- Test: `frontend/test/modules/hologram_hub/views/executive_advisory_board_view_test.dart`
- Test: `frontend/test/modules/projects/services/executive_board_stage_suggestion_service_test.dart`
- Create: `frontend/test/modules/projects/services/project_agent_deployment_service_test.dart`

**Consumes:** Task 7 generated endpoint contract and effective-state DTO.

**Produces:** User thấy rõ Role thuộc Workspace, Agent được deploy theo Project,
và stage chỉ gợi ý/cho phép; mọi Workspace office mutation mang CAS version.

- [ ] **Step 1: Write failing UI/service cases**

Use one fixture with office ACTIVE + Project deployment absent and assert copy
says “Role đã bật ở Workspace — cần deploy Agent vào Project”, not “Role active
trong Project”. Use a second fixture with stale Workspace office version and
assert refresh/error. Verify Project stage suggestion does not call raw
`ApiClient` and never omits `expectedVersion` on a Workspace mutation.

- [ ] **Step 2: Run tests red**

Run:

```bash
cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart test/modules/hologram_hub/controllers/executive_advisory_board_controller_reload_test.dart test/modules/hologram_hub/views/executive_advisory_board_view_test.dart test/modules/projects/services/executive_board_stage_suggestion_service_test.dart
```

- [ ] **Step 3: Use generated endpoints and exact DTO**

Replace raw API calls with `MvpRequestClient`. Model separate fields
`officeState`, `projectDeploymentState`, `stageEligibility`, `effectiveState`,
`workspaceOfficeVersion`, `projectAgentDeploymentId`, and `disabledReason`;
do not collapse errors into an empty list. Workspace office operations send its
CAS version. The only Project mutation is `deployAgentToProject` with an exact
`workspaceAgentId`; no Flutter client calls a Project Role bind/unbind route.

`ProjectAgentDeploymentService.deploy` must use the Task 7 generated endpoint:

```dart
Future<ApiResult<ProjectAgentDeployment>> deploy(
  String projectId, {
  required String workspaceAgentId,
  String? idempotencyKey,
});
```

It sends no `roleKey`, no client-supplied spec hash and no arbitrary Skill
definition. Server resolves the Workspace Agent and its pinned configuration.

- [ ] **Step 4: Refresh both scopes after a mutation**

After Workspace office change reload Workspace Board and current Project
deployment state. After Project Agent deployment reload only that Project plus
its stage suggestion. A lifecycle transition reloads Project loop/lifecycle
then retrieves fresh suggestion; it cannot auto-enable an office or deploy an
agent.

- [ ] **Step 5: Run Flutter green checks**

Run the four focused tests above and `flutter analyze --no-pub`.

- [ ] **Step 6: Commit role UI slice**

```bash
git add frontend/lib/modules/hologram_hub frontend/lib/modules/projects frontend/test/modules/hologram_hub frontend/test/modules/projects frontend/lib/core/network/mvp_endpoints.g.dart
git commit -m "fix(frontend): distinguish workspace role and project deployment"
```

**Rollback:** make deployment controls unavailable while still showing truthful
office/deployment failure states; do not display global ACTIVE as Project
EFFECTIVE.

### Task 9: Chứng minh migration, tenancy và release — không mở Skill layer

**Files:**
- Create: `tests/e2e/test_project_operating_loop_scope_and_authority.py`
- Modify: relevant contract/route inventory generated artifacts only
- Modify: `docs/superpowers/plans/2026-09-14-foundation-correctness-remediation.md` — tick evidence links/status after verified commands

**Consumes:** Tasks 1–8, disposable PostgreSQL and real Company/COSA/Agent processes.

**Produces:** Reproducible proof that cross-Project isolation, weekly CAS,
Workspace Role plus Project Agent deployment authority, and generated contracts
hold outside fixtures.

- [ ] **Step 1: Create process E2E fixture with one Workspace and two Projects**

The test must seed founder membership, Project A/B, Objective/KR/Initiative/Cycle/Week/Commitment/Task for each, then call public HTTP endpoints with ordinary authorization headers. Do not call service internals or share IDs accidentally.

- [ ] **Step 2: Add E2E negative assertions**

Prove over HTTP:

```text
GET A operating loop never returns B records
PATCH A/taskB/status returns not-found or forbidden and taskB stays unchanged
PATCH A/cycleB/week returns not-found or forbidden and no event is appended
workspace CFO ACTIVE + no A deployment cannot frame A deliberation
an ACTIVE Agent deployment in A cannot authorize B deliberation
```

Also send stale weekly/binding versions twice and assert event counts remain one.

- [ ] **Step 3: Run focused tests and migration preflight**

Run:

```bash
make services-migrate-company
cd services/company && npx vitest run operations/tests/project-operating-loop.service.test.ts operations/tests/task.service.test.ts operations/tests/task-advance.test.ts operations/tests/executive-role-activation.service.test.ts operations/tests/executive-deliberation.service.test.ts
cd frontend && flutter test test/modules/projects test/modules/hologram_hub
make contracts-check
make frontend-api-contract-check
```

Expected: all focused checks green before broad gates; if local migration database is unavailable, record it as blocked rather than calling the work complete.

- [ ] **Step 4: Run broad release gates in order**

Run:

```bash
make verify
make e2e-cross-plane-smoke
pytest tests/e2e/test_project_operating_loop_scope_and_authority.py -q
```

Expected: capture command output, migration version and commit SHA. A unit/static pass alone is not acceptance.

- [ ] **Step 5: Publish verification status and commit only evidence document**

After every command is green, record exact command/date/commit in the plan’s execution status section, then:

```bash
git add docs/superpowers/plans/2026-09-14-foundation-correctness-remediation.md tests/e2e/test_project_operating_loop_scope_and_authority.py
git commit -m "test(operations): prove project operating loop isolation"
```

**Rollback:** do not roll back verified migrations destructively. Disable new routes via deploy rollback, retain events/bindings, and create a forward migration only after diagnosing data impact.

## Dependency and Release Order

```text
Task 1 generator gate
  -> Task 2 Project/task scope
  -> Task 3 canonical HTTP contract
  -> Task 4 truthful loop UI
  -> Task 5 weekly state machine
  -> Task 6 Weekly UI
  -> Task 7 Workspace role + Project Agent deployment authority
  -> Task 8 role/deployment UI
  -> Task 9 process E2E/release proof

Task 2 owns migration 026 and Task 5 owns migration 027; each migration lands
with its own service slice in a separate reviewable commit. Task 7 must land
before Task 8. No Skill/tool integration may begin before Task 9 is green.
```

## Acceptance Matrix

| Requirement | Acceptance evidence |
| --- | --- |
| Lifecycle is truthful | NEW starts P0; ONBOARD_EXISTING writes Founder-attested baseline P0–P6 exactly once; later CAS change stale writes no event. |
| Project scope is authoritative | Two-Project negative service + HTTP tests for Task, commitment, cycle and role. |
| UI is truthful | Flutter DTO fixture is copied from server handler response; no phantom evidence/decisions. |
| Weekly is operational | Materialized weeks, review-required close, CAS, append-only events, explicit completion. |
| Role is Workspace-owned and stage-aware | Workspace office plus ACTIVE Project Agent deployment, stage enforcement, exact pins and runtime re-check. |
| Skills remain deferred | No new Skill runtime/action; existing pins only resolve as a fail-closed prerequisite. |
| Release is evidenced | contracts check, focused tests, `make verify`, cross-plane smoke and two-Project process E2E all green. |

## Plan Self-Review

- **Scope coverage:** covers all five requested foundations and all 13 roles through one catalog plus stage policy; it intentionally excludes new skills/tools/workflows.
- **No hidden migration:** migrations 026/027 are expand-only; old Project
  role rows remain deprecated, Project authority reuses agent deployments, and
  no initial stage is guessed without Founder onboarding input.
- **No false runtime claim:** Tasks 1–8 only create code-level evidence; Task 9 is the required disposable-Postgres/process proof.
- **Founder direction recorded:** Role/Office belongs Workspace; Project only
  deploys the existing Workspace Agent/Skill scope. The plan contains no
  Project-owned Role authority.
