# Default Project Context và Startup Team Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hub luôn có ngữ cảnh Project đúng cho founder, hiển thị trực tiếp tuần/công việc của Project và cung cấp catalog đội startup có thể kích hoạt một cách có thẩm quyền, kiểm chứng được.

**Architecture:** Company service là business truth cho Project và `project_agent_assignments`. Flutter chỉ lưu Project đang mở như một tiện ích UX; mọi đọc/ghi nghiệp vụ vẫn kiểm tra membership ở server. Agent Platform nhận bản chiếu/sự cho phép chạy qua API Company có chữ ký, không truy cập database Company. Operating Loop là nguồn độc lập cho Week/Tasks, không suy diễn từ activity timeline.

**Tech Stack:** TypeScript/Encore/Drizzle/PostgreSQL (Company); Python/FastAPI/PostgreSQL (Agent Platform); Flutter/GetX; JSON contract generator; pytest, Vitest và Flutter tests.

**Spec source:** [startup-default-context-and-workforce design](../specs/2026-09-11-startup-default-context-and-workforce-design.md). Kế hoạch này thay thế riêng quy tắc “luôn yêu cầu chọn Project” của kế hoạch Hub cũ; các ràng buộc `project_id`, membership, resume/SSE, outbox và project-scoped activity của kế hoạch đó vẫn giữ nguyên.

## Global constraints

- `active_project_id:<workspace_id>` trong local secure storage không phải quyền truy cập và không được gửi như bằng chứng ủy quyền.
- Khi không có key hợp lệ, chọn Project **cũ nhất** mà người dùng đang được ủy quyền (`createdAt ASC`, sau đó `id ASC`) và persist ngay sau khi server data đã được xác nhận. Không dựa vào thứ tự API hiện tại (`id DESC`).
- Nếu key đã lưu nhưng Project bị xóa, hết quyền hoặc thuộc Workspace khác, xóa key và hiện chọn thủ công. Không âm thầm nhảy sang Project khác.
- Nếu danh sách rỗng hoặc request lỗi, Hub không có Project. Không sinh Project giả, Week giả, Task giả, agent “online” giả hoặc activity giả.
- Week và task đến từ Project Operating Loop của Project đã chọn. Activity timeline chỉ dùng cho activity.
- Danh mục startup là cố định và được version ở source control; trạng thái assignment, người kích hoạt, spec/policy snapshot và event history là dữ liệu durable trong Company.
- Founder/admin mới được kích hoạt hoặc dừng agent. Mọi transition dùng `expectedVersion`, có journal append-only cùng transaction và phát event ở outbox.
- Coding là `DEFERRED_CODING` trong toàn bộ rollout này. Không thêm Coding AgentSpec, adapter Claude/Codex/Gemini/Antigravity, sandbox, CLI, local executor hoặc build pipeline.
- CRM và Sales xuất hiện như catalog template với lý do `PENDING_CRM_FOUNDATION`; chúng không tạo runtime/member cho đến khi kế hoạch CRM/Knowledge hoàn thành. Customer Support chỉ được kích hoạt sau khi Project Knowledge gate của kế hoạch kia có mặt.

## Catalog và interface chung

Catalog source duy nhất là `shared/contracts/startup-team-profiles.json`; generator tạo metadata TypeScript và Python để frontend, Company và Agent Platform không tự duy trì các enum khác nhau.

```json
{
  "schemaVersion": 1,
  "profiles": [
    {"key":"founder_assistant","label":"Co-Founder","defaultMode":"CHAT_READY","runtimeReadiness":"READY"},
    {"key":"research_intelligence","label":"Research & Intelligence","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"strategy","label":"Strategy","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"marketing","label":"Marketing","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"finance","label":"Finance","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"crm","label":"CRM","defaultMode":"TEMPLATE","runtimeReadiness":"PENDING_CRM_FOUNDATION"},
    {"key":"sales","label":"Sales","defaultMode":"TEMPLATE","runtimeReadiness":"PENDING_CRM_FOUNDATION"},
    {"key":"coding","label":"Coding","defaultMode":"TEMPLATE","runtimeReadiness":"DEFERRED_CODING"},
    {"key":"customer_support","label":"Customer Support","defaultMode":"TEMPLATE","runtimeReadiness":"PENDING_PROJECT_KNOWLEDGE"}
  ]
}
```

Company API used by the Hub:

```ts
type AssignmentState = 'TEMPLATE' | 'ACTIVE' | 'PAUSED' | 'RETIRED';
type TeamDisplayState = 'CHAT_READY' | AssignmentState;

interface ProjectStartupTeamMember {
  profileKey: StartupTeamProfileKey;
  label: string;
  displayState: TeamDisplayState;
  runtimeReadiness:
    | 'READY'
    | 'PENDING_CRM_FOUNDATION'
    | 'PENDING_PROJECT_KNOWLEDGE'
    | 'DEFERRED_CODING';
  disabledReason?: string;
  assignmentVersion?: number;
  activatedAt?: string;
  activatedBy?: string;
}

GET  /operations/projects/:projectId/startup-team
POST /operations/projects/:projectId/startup-team/:profileKey/activate { expectedVersion: number }
POST /operations/projects/:projectId/startup-team/:profileKey/pause    { expectedVersion: number }
```

`founder_assistant` is a `CHAT_READY` system capability, not an active workforce assignment. The `activate` endpoint rejects it, every non-ready catalog item, and an unknown profile. A service-to-service read endpoint, not exposed to Flutter, returns only a verified `ACTIVE` assignment and its pinned `specId`, `specVersion`, `specHash`, member reference, policy snapshot and assignment version.

---

## Task 1: Resolve Project context deterministically and surface the real operating week

**Files:**

- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Modify: `frontend/lib/modules/hologram_hub/services/active_project_store.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Create: `frontend/lib/modules/hologram_hub/models/project_context_resolution.dart`
- Create: `frontend/lib/modules/hologram_hub/widgets/project_operating_week_card.dart`
- Modify: `frontend/test/modules/hologram_hub/founder_command_center_controller_test.dart`
- Create: `frontend/test/modules/hologram_hub/widgets/project_operating_week_card_test.dart`

- [ ] **Step 1: Write the failing controller tests.** Replace the present “no stored ID does not auto-select” expectation with the approved behavior. Cover all of the following against mixed `createdAt`/ID values:

  ```text
  no stored Project  -> select min(createdAt, id), call store.write(projectId)
  valid stored id    -> retain stored Project, do not call store.write or store.delete
  stale stored id    -> call store.delete, leave selectedProjectId null
  unauthorized id    -> call store.delete, leave selectedProjectId null
  empty list         -> leave selectedProjectId null, do not persist
  list read failure  -> leave selectedProjectId null, do not persist
  ```

  Assert calls to `ActiveProjectStore.write`/`delete`, exact `selectedProjectId`, and that pulse/operating-loop loading only begins after a resolved Project. Run:

  ```bash
  cd frontend && flutter test test/modules/hologram_hub/founder_command_center_controller_test.dart
  ```

  Expected initially: the first test fails because the current controller leaves `requiresProjectSelection` true.

- [ ] **Step 2: Implement an explicit resolution value, then use it from `loadDashboardData`.** Keep storage parsing in `ActiveProjectStore`; return a typed result so a stale value cannot be confused with a missing key.

  ```dart
  enum ProjectContextResolutionKind { stored, defaulted, missing, stale }

  class ProjectContextResolution {
    const ProjectContextResolution({required this.kind, this.project});
    final ProjectContextResolutionKind kind;
    final Project? project;
  }
  ```

  In the controller, normalize the authorized list with `DateTime.parse(project.createdAt).toUtc()`, sort ascending by time then `project.id`, and choose only when the store returns `null`. For stored-but-unmatched IDs call `delete(workspaceId)` before returning `stale`; never call `projects.first` in that branch. Keep the selected id in `selectedProjectId`, persist only the computed default and preserve the existing explicit-selection `selectProject` behavior.

- [ ] **Step 3: Load Operating Loop separately from pulse/activity data.** Add a nullable observable `currentOperatingLoop` and an independently observable loading/error state. Reuse `ProjectOperatingLoopService.get(projectId)` rather than introducing another `/hub` route. Clear it synchronously whenever Project context changes, then load it only for the current selection token so a late response from the prior Project cannot paint the new Project.

  The card projection must use `activeCycle.weeklyPlans` and `tasks`/commitment tasks. It shows:

  - current cycle and the current Week based on the Project cycle dates;
  - named commitments and their incomplete/total task counts;
  - a truthful empty state when no active cycle or no commitments exists;
  - a retry action only for a real read error.

  Do not derive “Week 1” from project creation date, `Top 3`, or activity timestamps.

- [ ] **Step 4: Render the card and write widget tests.** Put `ProjectOperatingWeekCard` in the Hub main column only when `selectedProjectId` is non-null. It receives a projection/model, not a controller, and must test (a) no active cycle, (b) Week 1 with task counts, (c) empty commitments, and (d) read error/retry callback. Ensure the manual selection empty state remains visible if resolver returns `missing` or `stale`.

- [ ] **Step 5: Run focused green tests and static analysis.**

  ```bash
  cd frontend && flutter test test/modules/hologram_hub/founder_command_center_controller_test.dart test/modules/hologram_hub/widgets/project_operating_week_card_test.dart
  cd frontend && flutter analyze --no-pub lib/modules/hologram_hub
  ```

- [ ] **Step 6: Commit the isolated context/UI change.**

  ```bash
  git add frontend/lib/modules/hologram_hub frontend/test/modules/hologram_hub
  git commit -m "feat(hub): resolve default project context"
  ```

---

## Task 2: Establish a versioned startup-team catalog and durable per-Project assignment rows

**Files:**

- Create: `shared/contracts/startup-team-profiles.json`
- Create: `scripts/gen-startup-team-profiles.mjs`
- Create (generated): `services/company/shared/contracts/startup-team-profiles.generated.ts`
- Create (generated): `apps/cosa/agents/startup_team_profiles_generated.py`
- Modify: `package.json` and the relevant contract-generation check script
- Create: `services/company/operations/migrations/005_project_startup_team.up.sql`
- Create: `services/company/operations/migrations/005_project_startup_team.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/services/project-startup-team.service.ts`
- Modify: `services/company/operations/services/project.service.ts`
- Create: `services/company/operations/tests/project-startup-team.service.test.ts`

- [ ] **Step 1: Add catalog consistency tests before adding the data model.** The generator test must reject duplicate keys, a generated enum drift, and a catalog profile that does not have an explicit readiness state. In Company service tests assert that every catalog profile is returned for an authorized Project and the set equals the source catalog exactly.

  ```ts
  expect(team.map((member) => member.profileKey)).toEqual(startupTeamProfileKeys);
  expect(team.find((m) => m.profileKey === 'coding')).toMatchObject({
    displayState: 'TEMPLATE', runtimeReadiness: 'DEFERRED_CODING',
  });
  ```

  Run the focused tests and generator check; they should fail before the generated catalog and tables exist.

- [ ] **Step 2: Add an additive, reversible migration.** Use the next Operations migration number (`005`) and do not alter or rewrite historical Project rows. Create:

  ```sql
  CREATE TYPE operating.project_agent_assignment_state
    AS ENUM ('TEMPLATE', 'ACTIVE', 'PAUSED', 'RETIRED');

  CREATE TABLE operating.project_agent_assignments (
    id uuid PRIMARY KEY,
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL REFERENCES operations.projects(id),
    profile_key text NOT NULL,
    state operating.project_agent_assignment_state NOT NULL DEFAULT 'TEMPLATE',
    agent_workforce_member_id uuid,
    spec_id text,
    spec_version text,
    spec_hash text,
    activation_policy_snapshot jsonb,
    version integer NOT NULL DEFAULT 1,
    disabled_reason text,
    created_by uuid,
    activated_by uuid,
    paused_by uuid,
    activated_at timestamptz,
    paused_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, project_id, profile_key)
  );

  CREATE TABLE operating.project_agent_assignment_events (
    id uuid PRIMARY KEY,
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    assignment_id uuid NOT NULL REFERENCES operating.project_agent_assignments(id),
    event_type text NOT NULL,
    from_state operating.project_agent_assignment_state,
    to_state operating.project_agent_assignment_state NOT NULL,
    assignment_version integer NOT NULL,
    actor_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    event_payload jsonb NOT NULL DEFAULT '{}'::jsonb
  );
  ```

  Add tenant/project composite foreign-key or service-side invariant so a Project cannot be linked under another Workspace; add indexes on `(workspace_id, project_id)` and `(assignment_id, occurred_at DESC)`. The migration backfills exactly one `TEMPLATE` assignment for every catalog profile and every existing Project using conflict-safe insert. `coding` receives `disabled_reason = 'DEFERRED_CODING'`; CRM/Sales/Support receive their catalog readiness reasons. The down migration removes only the two new tables/type/indexes in dependency order.

- [ ] **Step 3: Generate and consume the catalog rather than duplicate profile literals.** `scripts/gen-startup-team-profiles.mjs` reads the JSON, validates schema and writes the TypeScript/Python files deterministically. Add it to the existing contracts check so a changed JSON with stale generated outputs fails CI. Import the generated TypeScript values in the new service and generated Python values in the later Agent Platform gate.

- [ ] **Step 4: Seed assignments inside the Project creation transaction.** Refactor `createProjectService` so creating the Project, all template assignment rows, their initial `ASSIGNMENT_TEMPLATE_CREATED` events, and the Project journal/outbox record commit atomically. Reuse the same `ensureProjectStartupTeam` idempotent helper for migration/backfill repair, but do not call Agent Platform from the transaction.

  The service interface is deliberately Project-scoped:

  ```ts
  export async function listProjectStartupTeam(input: {
    workspaceId: string; projectId: string; actorId: string;
  }): Promise<ProjectStartupTeamMember[]>;

  async function ensureProjectStartupTeam(tx: DbTx, input: {
    workspaceId: string; projectId: string; actorId: string;
  }): Promise<void>;
  ```

- [ ] **Step 5: Prove migration and creation behavior.** Extend service tests to run against disposable Postgres and prove: newly created Project gets the entire catalog exactly once; re-running repair does not duplicate rows/events; an old Project gets backfilled; catalog key uniqueness is enforced; Project/Workspace mismatch is rejected. Run:

  ```bash
  pnpm --filter @cosa/company test -- project-startup-team.service.test.ts
  pnpm run gen:startup-team-profiles -- --check
  ```

- [ ] **Step 6: Commit schema/catalog work.**

  ```bash
  git add shared/contracts/startup-team-profiles.json scripts/gen-startup-team-profiles.mjs package.json services/company/operations services/company/shared
  git commit -m "feat(operations): persist startup team assignments"
  ```

---

## Task 3: Expose founder-governed team management and an internal run-authority read

**Files:**

- Create: `services/company/operations/handlers/project-startup-team.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/operations/services/project-startup-team.service.ts`
- Create: `services/company/operations/tests/project-startup-team.handler.test.ts`
- Modify: `services/company/operations/services/project-activity.service.ts` or its authoritative event projector
- Modify: `shared/contracts/mvp-surface.json`
- Run/generated modify: `services/company/shared/contracts/mvp-surface.generated.ts`, `apps/cosa/api/mvp_contracts_generated.py`, `frontend/lib/core/network/mvp_endpoints.g.dart`

- [ ] **Step 1: Write handler/service red tests for authority and state transitions.** Cover:

  - member from another Workspace gets indistinguishable `404` for list, activate and pause;
  - Workspace member without founder/admin role gets `403` for activate/pause;
  - founder/admin can list but cannot activate `founder_assistant`, `crm`, `sales`, `coding`, or Support before their readiness gate;
  - activating a ready template pins current `AgentSpec` identity/hash and immutable policy snapshot;
  - stale `expectedVersion` returns conflict without a second event;
  - pause of `ACTIVE` writes one event, increments version and blocks further runs;
  - repeating an idempotency key returns the original resulting view without duplicate history.

- [ ] **Step 2: Implement exact authority and concurrency control.** Add `requireStartupTeamAuthority` that first checks Project membership in the requested Workspace and then accepts only the documented human roles `founder` or `admin`. Do not use local active Project, a Co-Founder chat identity, or a generic agent capability grant as a substitute.

  For a transition, lock/update by `(id, workspace_id, project_id, version = expectedVersion)`, then insert its event and Company outbox/activity projection in the same database transaction. Store a redacted policy snapshot with the rule/version and selected capability set, never raw credentials or prompts. Use a request idempotency record consistent with the existing Company write pattern.

- [ ] **Step 3: Add public Hub endpoints and an internal run-authority endpoint.** Register the three typed public routes listed above. Add a separate service-authenticated route such as:

  ```ts
  GET /internal/operations/projects/:projectId/startup-team/:profileKey/run-authority
  ```

  It validates the Company-to-Agent service signature, requires exact `workspaceId`, and returns `404` unless state is `ACTIVE` and the requested key is presently `READY`. Its response is:

  ```ts
  interface ProjectAgentRunAuthority {
    projectId: string;
    workspaceId: string;
    profileKey: StartupTeamProfileKey;
    assignmentVersion: number;
    agentWorkforceMemberId: string;
    spec: { id: string; version: string; hash: string };
    policySnapshot: Record<string, unknown>;
  }
  ```

  This is the sole bridge used by Agent Platform; it must not return all roster members and must not be browser-exposed.

- [ ] **Step 4: Add contract entries and regenerate from source.** Add each browser endpoint to `shared/contracts/mvp-surface.json` with the Company owner, Workspace and Project requirements, founder/admin write policy and response type. Keep the internal service route out of the browser manifest but test it separately. Generate only through:

  ```bash
  node scripts/gen-mvp-contracts.mjs
  ```

- [ ] **Step 5: Make transitions visible but not misleading.** Emit Project activity labels such as “Marketing agent activated” and “Finance agent paused” only after the transaction succeeds. The event payload contains profile key, version and actor reference; it must not claim a background agent is online or that it has completed work.

- [ ] **Step 6: Run service/contract gates.**

  ```bash
  pnpm --filter @cosa/company test -- project-startup-team.service.test.ts project-startup-team.handler.test.ts
  make mvp-contracts-check
  make mvp-surface-check
  make company-boundary-check
  make encore-handler-boundary-check
  ```

- [ ] **Step 7: Commit the governed API.**

  ```bash
  git add services/company/operations services/company/shared/contracts shared/contracts/mvp-surface.json apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart
  git commit -m "feat(operations): govern project startup team"
  ```

---

## Task 4: Gate Agent Platform execution against the Company assignment

**Files:**

- Modify: `apps/cosa/agents/agent_profile_specs.py`
- Modify: `apps/cosa/agents/specs.py`
- Modify: `apps/cosa/agents/seed.py`
- Create: `apps/cosa/company/project_team_client.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/worker/copilot_run.py`
- Modify: `apps/cosa/worker/tests/test_handlers.py`
- Create: `apps/cosa/worker/tests/test_project_team_authority.py`
- Modify: `services/company/operations/services/ai-member.service.ts`
- Modify: `services/company/operations/strategy/services/workspace-strategy-settings.service.ts`

- [ ] **Step 1: Add failing cross-plane unit tests.** Mock the signed Company client and assert:

  ```text
  unassigned profile                     -> deny before kernel
  paused assignment                      -> deny before kernel
  assignment/spec hash mismatch          -> deny before kernel
  workspace or project mismatch          -> deny before kernel
  active Support without Knowledge gate  -> deny before kernel
  ```

  Capture that no `TurnRunner`, provider call, tool invocation or token accounting is created for a denied request. Also write TypeScript tests that an assignment cannot be activated unless its Company AI workforce member and pinned AgentSpec exist.

- [ ] **Step 2: Add a signed Company client, never a Company DB repository.** `ProjectTeamClient.get_run_authority(workspace_id=workspace_id, project_id=project_id, profile_key=profile_key)` sends the existing service identity/signature and validates the exact response shape. It fails closed on timeouts, malformed response, expired signature, Project/Workspace mismatch or stale pin. Do not cache an allow decision past the request; revocation/pause must be visible to the next run.

- [ ] **Step 3: Perform the run gate before AgentSpec/kernel resolution.** In the worker, require immutable `workspace_id`, `project_id` and `profile_key` on every Project Team request; query Company; resolve the local AgentSpec; compare all of `(key, id, version, hash)`; then create the runtime. Persist `assignment_version` and the spec pin into run metadata/audit trace. Existing legacy, unscoped runs retain their explicit legacy path and cannot impersonate Project Team runs.

- [ ] **Step 4: Register only actually ready existing profiles.** Bring generated catalog keys into `agent_profile_specs.py` and make mapping exhaustive. Ensure `operations`, `research_intelligence`, `strategy`, `marketing`, `finance` and `customer_support` have concrete, tested specs/member records before the Company service can mark them ready. Customer Support must leave its current special bypass path and pass the same Project assignment gate. CRM and Sales have no runnable spec in this task; their generated readiness remains pending until the CRM plan supplies contracts/capabilities. Coding remains denied with `DEFERRED_CODING`.

- [ ] **Step 5: Prove revocation and identity behavior.** Run focused Python and Company tests, including a pause between run requests and a forged old pin. Confirm Agent Platform never has credentials to mutate Company assignment rows.

  ```bash
  make apps-cosa-test TESTS='apps/cosa/worker/tests/test_handlers.py apps/cosa/worker/tests/test_project_team_authority.py'
  pnpm --filter @cosa/company test -- ai-member.service.test.ts
  ```

- [ ] **Step 6: Commit the runtime gate.**

  ```bash
  git add apps/cosa/agents apps/cosa/company apps/cosa/worker services/company/operations
  git commit -m "feat(agents): require project team authority"
  ```

---

## Task 5: Replace the empty workforce panel with the truthful Project startup team

**Files:**

- Create: `frontend/lib/modules/hologram_hub/models/project_startup_team.dart`
- Create: `frontend/lib/modules/hologram_hub/services/project_startup_team_service.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Create: `frontend/lib/modules/hologram_hub/widgets/project_startup_team_sidebar.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Modify or retire after call-site audit: `frontend/lib/modules/hologram_hub/widgets/command_center_workforce_sidebar.dart`
- Create: `frontend/test/modules/hologram_hub/services/project_startup_team_service_test.dart`
- Create: `frontend/test/modules/hologram_hub/widgets/project_startup_team_sidebar_test.dart`

- [ ] **Step 1: Write service and widget tests before changing the view.** Mock only generated `MvpEndpoint` routes. Test serialization of every catalog state, a stale activation conflict, forbidden activation, no selected Project, network error, and Project switch where the old roster response is ignored. Widget tests must verify exact truthful labels:

  - `CHAT_READY`: “Co-Founder chat ready”;
  - `ACTIVE`: “Active”, with activation timestamp/actor when available;
  - `TEMPLATE`, `PAUSED`, pending and deferred states: not shown as online;
  - Coding: “Coming later”; 
  - CRM/Sales/Support readiness message from the API, not a hard-coded false enablement.

- [ ] **Step 2: Implement typed service/model.** `ProjectStartupTeamService` uses `MvpRequestClient` and generated endpoints exclusively. No `http` literals, broad catch-to-empty fallback or client-side role bypass. Parse ISO dates as UTC and preserve server `assignmentVersion` for action requests.

- [ ] **Step 3: Integrate into the controller with request-generation protection.** On a valid selected Project, load team after the Project context resolves. Clear it on manual selection, stale context, workspace switch and logout. On activation/pause, disable only that row, post its stored `expectedVersion`, replace from server response, then refresh activity/pulse; a `409` refreshes roster and explains the state changed elsewhere.

- [ ] **Step 4: Render the new sidebar.** Replace the present panel that always receives no custom agents. Keep the project selector accessible; if no Project exists show no team controls. Founder/admin sees activate/pause only when the server says action is allowed; all other roles receive read-only roster. Do not render a bulk “activate entire team” control.

- [ ] **Step 5: Run Flutter and contract checks.**

  ```bash
  cd frontend && flutter test test/modules/hologram_hub/services/project_startup_team_service_test.dart test/modules/hologram_hub/widgets/project_startup_team_sidebar_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart
  cd frontend && flutter analyze --no-pub lib/modules/hologram_hub
  make frontend-api-contract-check
  ```

- [ ] **Step 6: Commit the Hub roster UI.**

  ```bash
  git add frontend/lib/modules/hologram_hub frontend/test/modules/hologram_hub
  git commit -m "feat(hub): show project startup team"
  ```

---

## Task 6: Verify the end-to-end invariants and release with an observable migration

**Files:**

- Create: `tests/e2e/test_default_project_startup_team.py`
- Modify: the existing disposable-Postgres Company/Agent process fixture only if it lacks Project Team service credentials
- Modify: `docs/runbooks/project-startup-team-rollout.md`

- [ ] **Step 1: Write disposable-process E2E coverage.** Start Company and Agent Platform against isolated Postgres. Seed one user authorized for two Projects with intentionally inverted UUID order and one unauthorized Project. Exercise:

  1. first Hub session defaults to oldest authorized Project and persists its id;
  2. stale saved id is deleted and no other Project is selected;
  3. the selected Project’s Operating Loop contributes Week/Task card independently of empty activity;
  4. founder activates Marketing; Company has one assignment event/outbox record and Agent Platform runs only with the returned pin;
  5. pause invalidates the next attempted run; prior trace remains inspectable;
  6. non-founder and cross-tenant attempts fail without data disclosure;
  7. catalog entries that are pending/deferred cannot run or display “online”.

- [ ] **Step 2: Add migration rollout and rollback runbook.** Require database backup/restore verification in a disposable environment, migration preflight, catalog generator check, row-count comparison (`projects × catalog profiles`), outbox consumer health, and a sampled transition trace. The rollback explicitly stops new activation first; it does not delete event history or silently re-enable paused agents.

- [ ] **Step 3: Execute all required gates.**

  ```bash
  make mvp-contracts-check
  make mvp-surface-check
  make frontend-api-contract-check
  make company-boundary-check
  make encore-handler-boundary-check
  make ts-suppression-check
  make apps-cosa-test
  cd frontend && flutter test test/modules/hologram_hub
  cd frontend && flutter analyze --no-pub
  pytest tests/e2e/test_default_project_startup_team.py -q
  ```

  Record command output, migration version and deployed service revisions in the release evidence. A static UI test or a seeded mock is not evidence for pause/revocation or tenant isolation.

- [ ] **Step 4: Commit the verification/runbook artifacts.**

  ```bash
  git add tests/e2e docs/runbooks
  git commit -m "test: verify project startup team lifecycle"
  ```

## Delivery checkpoints

1. After Task 1, a single authorized Project opens automatically and Week/Tasks are truthful, without changing authorization.
2. After Tasks 2–3, every Project has a durable, auditable catalog and founder-governed assignment state.
3. After Tasks 4–5, only activated and verified agents can be presented/run for that Project.
4. After Task 6, disposable-process evidence proves default selection, cross-tenant denial, activation, and revocation.
