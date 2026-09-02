# Founder Project Kickoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Sau khi Founder tạo project, đưa họ vào luồng thiết lập 3 bước có persistence, rồi hiển thị Guided Hub theo project mà không tạo KPI, mission hoặc Top 3 giả.

**Architecture:** services/company là source of truth cho record project_operating_setups theo project. Flutter tạo project ở P0_DISCOVERY, lưu và resume setup qua API typed, rồi activate thực hiện transition P0→P1 khi Founder xác nhận evidence. Transition, setup, audit và outbox nằm chung một transaction. Dashboard chỉ giữ target điều hướng ngắn hạn; Guided Hub render từ persisted setup, còn Command Center hiện có chỉ dùng cho project đã vận hành.

**Tech Stack:** Flutter/Dart + GetX + flutter_test; Encore.ts + Drizzle/PostgreSQL + Vitest.

**Spec:** docs/superpowers/specs/2026-09-01-founder-project-kickoff-design.md

## Global Constraints

- Basic create chỉ nhận tên và mô tả ngắn; backend luôn tạo P0_DISCOVERY. Không gửi phase, project_stage, stage legacy, roadmap, goal, mission hay 12-week cycle.
- Basic Kickoff chỉ cho P0_DISCOVERY hoặc P1_PROBLEM_VALIDATION. P1 đòi FIVE_PLUS_INTERVIEWS hoặc PROTOTYPE_OR_REVENUE và phải đi qua lifecycle service.
- stageDurationWeeks là timebox của vòng, không dùng projects.endDate và không tự chuyển stage. P0: 1–2 tuần; P1: 2–4 tuần.
- Save và activate không tự tạo task, mission, approval, decision, agent dispatch, calendar event, Top 3 hoặc 12-week cycle.
- activeMissions không được suy ra từ Next Best Actions. Không có endpoint mission thật thì value là null và UI không render.
- Chỉ P-stage hiển thị cho project; không lẫn workspace W0…W5. Không sửa enums.generated.dart.
- Migration 34 chỉ mở rộng schema, có cả up/down. Endpoint gọi requireWorkspaceAccess và mọi query bind workspaceId.
- Trước mỗi commit chạy git status --short và chỉ stage files của task; giữ nguyên mọi thay đổi cục bộ khác.
- Tại thời điểm viết plan, frontend/test/modules/strategy/services/project_service_test.dart đang có thay đổi cục bộ. Executor phải đọc diff, giữ test của người dùng, rồi thêm assertion createBasicProject vào cùng file thay vì ghi đè file.

## File map

| Vùng | File | Trách nhiệm |
|---|---|---|
| Persistence | services/company/operations/migrations/34_project_operating_setups.*.sql; services/company/shared/db/schema/strategy.ts | Setup 1–1, action JSON, check và composite FK. |
| Domain/API | services/company/operations/strategy/services/project-operating-setup.service.ts; services/company/operations/strategy/handlers/project-operating-setup.handler.ts | GET, save draft, atomic activate, validation, event. |
| Lifecycle | services/company/operations/strategy/services/project-stage-lifecycle.service.ts | Transaction-aware transition helper. |
| Flutter data | frontend/lib/data/models/project_operating_setup_model.dart; frontend/lib/modules/strategy/services/project_operating_setup_service.dart | Typed data and HTTP contract. |
| Kickoff | frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart; frontend/lib/modules/strategy/views/project_kickoff_view.dart | 3 steps/resume/activate. |
| Roadmap | frontend/lib/modules/strategy/views/project_roadmap_advanced_view.dart | Current roadmap/AI UI placed behind advanced action. |
| Navigation/hub | DashboardController, ProjectRoadmapTab, FounderCommandCenter, Hologram Hub | Redirect exact ID, Guided Hub and truthful metrics. |

---

### Task 1: Persist one operating setup per project

**Files:**
- Create: services/company/operations/migrations/34_project_operating_setups.up.sql
- Create: services/company/operations/migrations/34_project_operating_setups.down.sql
- Modify: services/company/shared/db/schema/strategy.ts
- Test: services/company/operations/tests/project-operating-setup.test.ts

**Interfaces:**
- Produces Drizzle table projectOperatingSetups.
- Produces statuses NOT_STARTED, IN_PROGRESS, ACTIVE and four evidence levels.

- [ ] **Step 1: Write the failing database contract test.**

~~~ts
it("stores one operating setup scoped to its project and workspace", async () => {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, title: "Discovery",
  });
  await db.insert(schema.projectOperatingSetups).values({
    projectId: BigInt(project.id), workspaceId: BigInt(ws.workspaceId), status: "IN_PROGRESS",
    evidenceLevel: "NONE", selectedStage: "P0_DISCOVERY", stageDurationWeeks: 2,
    firstWeekActions: [],
  });
  const rows = await db.select().from(schema.projectOperatingSetups);
  expect(rows).toHaveLength(1);
  expect(rows[0]?.projectId.toString()).toBe(project.id);
});
~~~

Add an insert of a second row with the same project ID and assert PostgreSQL rejects it, proving the 1–1 key.

- [ ] **Step 2: Run it to verify it fails.**

Run:

~~~bash
cd services/company && npm test -- project-operating-setup.test.ts
~~~

Expected: projectOperatingSetups export does not exist.

- [ ] **Step 3: Add migration 34.**

Create the forward migration:

~~~sql
CREATE TABLE strategy.project_operating_setups (
  project_id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'NOT_STARTED'
    CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'ACTIVE')),
  target_customer TEXT NULL,
  problem_statement TEXT NULL,
  evidence_level TEXT NULL
    CHECK (evidence_level IN ('NONE', 'ONE_TO_FOUR_INTERVIEWS', 'FIVE_PLUS_INTERVIEWS', 'PROTOTYPE_OR_REVENUE')),
  recommended_stage TEXT NULL
    CHECK (recommended_stage IN ('P0_DISCOVERY', 'P1_PROBLEM_VALIDATION')),
  selected_stage TEXT NULL
    CHECK (selected_stage IN ('P0_DISCOVERY', 'P1_PROBLEM_VALIDATION')),
  stage_duration_weeks INTEGER NULL CHECK (stage_duration_weeks BETWEEN 1 AND 4),
  stage_target_date TIMESTAMPTZ NULL,
  weekly_review_weekday SMALLINT NULL CHECK (weekly_review_weekday BETWEEN 1 AND 7),
  weekly_review_time TEXT NULL CHECK (weekly_review_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'),
  first_week_outcome TEXT NULL,
  first_week_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_project_operating_setups_workspace_status
  ON strategy.project_operating_setups(workspace_id, status, updated_at DESC);
~~~

The down migration contains exactly:

~~~sql
DROP TABLE IF EXISTS strategy.project_operating_setups;
~~~

- [ ] **Step 4: Mirror the table in Drizzle.**

Add this export after projectStageTransitions:

~~~ts
export const projectOperatingSetups = strategySchema.table("project_operating_setups", {
  projectId: bigint("project_id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  status: varchar("status", { length: 20 }).default("NOT_STARTED").notNull(),
  targetCustomer: text("target_customer"),
  problemStatement: text("problem_statement"),
  evidenceLevel: varchar("evidence_level", { length: 40 }),
  recommendedStage: varchar("recommended_stage", { length: 50 }),
  selectedStage: varchar("selected_stage", { length: 50 }),
  stageDurationWeeks: integer("stage_duration_weeks"),
  stageTargetDate: timestamp("stage_target_date", { withTimezone: true }),
  weeklyReviewWeekday: integer("weekly_review_weekday"),
  weeklyReviewTime: varchar("weekly_review_time", { length: 5 }),
  firstWeekOutcome: text("first_week_outcome"),
  firstWeekActions: jsonb("first_week_actions").default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
~~~

- [ ] **Step 5: Apply migration and run test.**

Run:

~~~bash
cd services/company && npm run migrate && npm test -- project-operating-setup.test.ts
~~~

Expected: migration and the direct persistence contract test pass.

- [ ] **Step 6: Commit.**

~~~bash
git add services/company/operations/migrations/34_project_operating_setups.up.sql \
  services/company/operations/migrations/34_project_operating_setups.down.sql \
  services/company/shared/db/schema/strategy.ts
git commit -m "feat(strategy): persist project operating setup"
~~~

### Task 2: Implement tenant-bound setup API with atomic activation

**Files:**
- Create: services/company/operations/strategy/services/project-operating-setup.service.ts
- Create: services/company/operations/strategy/handlers/project-operating-setup.handler.ts
- Modify: services/company/operations/strategy/services/project-stage-lifecycle.service.ts
- Modify: services/company/operations/services/project.service.ts
- Modify: services/company/shared/events.ts
- Modify: services/company/operations/tests/project-operating-setup.test.ts
- Modify: services/company/operations/tests/project.test.ts

**Interfaces:**
- Produces GET, PUT, POST /operations/projects/:id/operating-setup and POST /operations/projects/:id/operating-setup/activate.
- Produces ProjectOperatingSetupView, saveProjectOperatingSetup, activateProjectOperatingSetup, and transitionProjectStageInTransaction.
- Extends Project response with stageEnteredAt so Guided Hub calculates the current week from lifecycle truth.

- [ ] **Step 1: Write failing behavior tests.**

~~~ts
it("returns NOT_STARTED without inserting, then resumes a saved draft", async () => {
  const initial = await getProjectOperatingSetupEndpoint({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, id: project.id,
  });
  expect(initial.status).toBe("NOT_STARTED");

  await putProjectOperatingSetupEndpoint({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, id: project.id,
    targetCustomer: "Finance teams", problemStatement: "Month-end takes days",
    evidenceLevel: "ONE_TO_FOUR_INTERVIEWS", selectedStage: "P0_DISCOVERY", stageDurationWeeks: 2,
  });

  const resumed = await getProjectOperatingSetupEndpoint({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, id: project.id,
  });
  expect(resumed.status).toBe("IN_PROGRESS");
  expect(resumed.targetCustomer).toBe("Finance teams");
});

it("activates P1 via lifecycle journal and persists commitment", async () => {
  const result = await activateProjectOperatingSetupEndpoint({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, id: project.id,
    targetCustomer: "B2B finance leads", problemStatement: "Reconciliation is slow",
    evidenceLevel: "FIVE_PLUS_INTERVIEWS", selectedStage: "P1_PROBLEM_VALIDATION",
    stageDurationWeeks: 4, weeklyReviewWeekday: 5, weeklyReviewTime: "16:00",
    firstWeekOutcome: "Complete five interviews",
    firstWeekActions: [{ title: "List ten prospects" }],
  });
  expect(result.setup.status).toBe("ACTIVE");
  expect(result.project.lifecycleStage).toBe("P1_PROBLEM_VALIDATION");
  expect((await listProjectStageTransitions(BigInt(ws.workspaceId), BigInt(project.id)))
    .map((row) => row.toStage)).toContain("P1_PROBLEM_VALIDATION");
});
~~~

Add an authenticated second-workspace GET/PUT test that rejects with code not_found. Also reject P1 with NONE, P0 duration 3, four actions, and malformed review time. After every rejected activation assert setup is NOT_STARTED, lifecycle is P0, and outbox count is unchanged.

- [ ] **Step 2: Run test to verify it fails.**

Run:

~~~bash
cd services/company && npm test -- project-operating-setup.test.ts
~~~

Expected: endpoint imports do not resolve.

- [ ] **Step 3: Implement pure policy and service types.**

~~~ts
export type OperatingSetupStatus = "NOT_STARTED" | "IN_PROGRESS" | "ACTIVE";
export type EvidenceLevel =
  | "NONE" | "ONE_TO_FOUR_INTERVIEWS" | "FIVE_PLUS_INTERVIEWS" | "PROTOTYPE_OR_REVENUE";
export type BasicKickoffStage = "P0_DISCOVERY" | "P1_PROBLEM_VALIDATION";
export interface FirstWeekAction { id: string; title: string; }
export interface ProjectOperatingSetupView {
  projectId: string; workspaceId: string; status: OperatingSetupStatus;
  targetCustomer: string | null; problemStatement: string | null; evidenceLevel: EvidenceLevel | null;
  recommendedStage: BasicKickoffStage | null; selectedStage: BasicKickoffStage | null;
  stageDurationWeeks: number | null; stageTargetDate: string | null;
  weeklyReviewWeekday: number | null; weeklyReviewTime: string | null;
  firstWeekOutcome: string | null; firstWeekActions: FirstWeekAction[]; updatedAt: string | null;
}
export function recommendKickoffStage(level: EvidenceLevel | null): BasicKickoffStage {
  return level === "FIVE_PLUS_INTERVIEWS" || level === "PROTOTYPE_OR_REVENUE"
    ? "P1_PROBLEM_VALIDATION" : "P0_DISCOVERY";
}
~~~

GET first verifies strategy.projects by project plus workspace. If no setup row it returns an in-memory NOT_STARTED view and does not insert. PUT upserts IN_PROGRESS only, rejects changes after ACTIVE, normalizes non-empty action titles, caps at three, and uses server time plus duration times seven days for target date.

Use these validations exactly:

~~~ts
const durationLimits: Record<BasicKickoffStage, readonly [number, number]> = {
  P0_DISCOVERY: [1, 2], P1_PROBLEM_VALIDATION: [2, 4],
};
if (!/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(weeklyReviewTime)) {
  throw APIError.invalidArgument("weeklyReviewTime must use HH:mm");
}
if (selectedStage === "P1_PROBLEM_VALIDATION" &&
  !["FIVE_PLUS_INTERVIEWS", "PROTOTYPE_OR_REVENUE"].includes(evidenceLevel)) {
  throw APIError.invalidArgument("P1 requires founder-confirmed qualifying evidence");
}
~~~

- [ ] **Step 4: Refactor lifecycle transaction boundary and activate atomically.**

Move the current project select, policy read, optimistic update, journal and outbox writes into this exported helper:

~~~ts
export async function transitionProjectStageInTransaction(
  tx: Parameters<Parameters<typeof db.transaction>[0]>[0],
  params: ProjectTransitionParams,
): Promise<ProjectTransitionResult>;
~~~

Keep the existing public entry point as:

~~~ts
export async function transitionProjectStage(params: ProjectTransitionParams) {
  return db.transaction((tx) => transitionProjectStageInTransaction(tx, params));
}
~~~

Activate validates the complete request before db.transaction. Inside transaction, invoke transition helper only for P1, upsert ACTIVE, and append exactly one project.operating_setup.activated.v1 event. Add:

~~~ts
export const PROJECT_OPERATING_SETUP_ACTIVATED = "project.operating_setup.activated.v1";
~~~

Event payload only contains project/workspace IDs, selected stage, duration, action count, review weekday, and activation time. It excludes customer/problem free text and must not insert tasks, next_best_actions, cycles, missions, approvals, or calendar records.

- [ ] **Step 5: Return project stage entry time.**

Add nullable `stageEnteredAt: string | null` to the existing Project interface and `toProject` in services/company/operations/services/project.service.ts. It serializes `row.stageEnteredAt?.toISOString() ?? null`. In services/company/operations/tests/project.test.ts, assert that a newly created P0 project returns a non-null stageEnteredAt. This is read-only metadata; do not add a second stage timestamp to operating setup.

- [ ] **Step 6: Add Encore handlers.**

Every handler has authorization, X-Workspace-Id header and id path param, calls requireWorkspaceAccess, and passes only context workspace ID to service. Expose:

~~~ts
api({ method: "GET", path: "/operations/projects/:id/operating-setup", expose: true }, handler);
api({ method: "PUT", path: "/operations/projects/:id/operating-setup", expose: true }, handler);
api({ method: "POST", path: "/operations/projects/:id/operating-setup/activate", expose: true }, handler);
~~~

PUT accepts partial step 1/2 fields. Activate requires customer, problem, evidence, P0/P1, duration, review weekday/time, outcome and one to three action titles.

- [ ] **Step 7: Run regression and commit.**

Run:

~~~bash
cd services/company && npm test -- project-operating-setup.test.ts project-stage-lifecycle.test.ts project.test.ts event-outbox.test.ts
cd services/company && npm run typecheck
~~~

Expected: pass including legacy lifecycle tests, P1 journal/outbox, validation rollback and tenant isolation.

~~~bash
git add services/company/shared/events.ts \
  services/company/operations/strategy/services/project-operating-setup.service.ts \
  services/company/operations/strategy/handlers/project-operating-setup.handler.ts \
  services/company/operations/strategy/services/project-stage-lifecycle.service.ts \
  services/company/operations/services/project.service.ts \
  services/company/operations/tests/project-operating-setup.test.ts \
  services/company/operations/tests/project.test.ts
git commit -m "feat(strategy): activate founder operating setup atomically"
~~~

### Task 3: Add Flutter typed client and P0-only basic creation

**Files:**
- Create: frontend/lib/data/models/project_operating_setup_model.dart
- Create: frontend/lib/modules/strategy/services/project_operating_setup_service.dart
- Modify: frontend/lib/modules/strategy/services/project_service.dart
- Modify: frontend/test/modules/strategy/services/project_service_test.dart
- Test: frontend/test/modules/strategy/services/project_operating_setup_service_test.dart

**Interfaces:**
- Produces ProjectOperatingSetup, ProjectOperatingSetupDraft, FirstWeekActionDraft, KickoffEvidenceLevel, KickoffStagePolicy.
- Produces ProjectService.createBasicProject.

- [ ] **Step 1: Write failing request and parse tests.**

~~~dart
test('createBasicProject posts only the P0 basic contract', () async {
  ApiClient.client = MockClient((request) async {
    final body = jsonDecode(request.body) as Map<String, dynamic>;
    expect(body, {
      'title': 'Invoice assistant',
      'description': 'Reduce reconciliation time',
      'lifecycleStage': 'P0_DISCOVERY',
    });
    return http.Response(jsonEncode({'id': 'p-1', 'lifecycleStage': 'P0_DISCOVERY'}), 200);
  });
  expect((await ProjectService().createBasicProject(
    title: 'Invoice assistant', description: 'Reduce reconciliation time',
  ))['id'], 'p-1');
});

test('activate posts founder actions and no inferred mission', () async {
  ApiClient.client = MockClient((request) async {
    expect(request.url.path, '/operations/projects/p-1/operating-setup/activate');
    final body = jsonDecode(request.body) as Map<String, dynamic>;
    expect(body['firstWeekActions'], [{'title': 'Recruit five interviewees'}]);
    expect(body.containsKey('mission'), isFalse);
    return http.Response(jsonEncode({'setup': activeSetupJson}), 200);
  });
  await ProjectOperatingSetupService().activate('p-1', completeP0Draft);
});
~~~

Add a 422 response test that returns StrategyApiException instead of an empty setup model.

- [ ] **Step 2: Run tests to verify they fail.**

Run:

~~~bash
cd frontend && flutter test test/modules/strategy/services/project_operating_setup_service_test.dart test/modules/strategy/services/project_service_test.dart -r compact
~~~

Expected: missing model/service/basic create.

- [ ] **Step 3: Implement immutable model and display policy.**

Use generated ProjectLifecycleStage for wire values, never a second free-string stage enum.

~~~dart
enum KickoffEvidenceLevel { none, oneToFourInterviews, fivePlusInterviews, prototypeOrRevenue }

class FirstWeekActionDraft {
  const FirstWeekActionDraft({this.id, required this.title});
  final String? id;
  final String title;
  Map<String, dynamic> toJson() => {'title': title.trim()};
}

class KickoffStagePolicy {
  static const p0DefaultWeeks = 2;
  static const p1DefaultWeeks = 4;
  static bool allows(ProjectLifecycleStage stage, int weeks) =>
      stage == ProjectLifecycleStage.p0Discovery ? weeks >= 1 && weeks <= 2 : weeks >= 2 && weeks <= 4;
}
~~~

Model isInitialLoop is true only for active P0/P1 setup. Parser preserves nullable unavailable fields.

- [ ] **Step 4: Implement service and minimal creation call.**

Provide:

~~~dart
Future<ProjectOperatingSetup> get(String projectId);
Future<ProjectOperatingSetup> saveDraft(String projectId, ProjectOperatingSetupDraft draft);
Future<ProjectOperatingSetup> activate(String projectId, ProjectOperatingSetupDraft draft);
~~~

Use ApiClient and existing StrategyServiceBase decode exception behavior. Add:

~~~dart
Future<Map<String, dynamic>> createBasicProject({required String title, String? description}) async {
  final workspaceId = await requireWorkspaceId();
  final response = await ApiClient.post(
    '/operations/projects?workspace_id=$workspaceId',
    body: {'title': title, 'description': ?description, 'lifecycleStage': 'P0_DISCOVERY'},
  );
  return decode(response);
}
~~~

No phase, goal, status, dates, legacy stage, mission or cycle field enters this method.

- [ ] **Step 5: Format and run tests.**

Run:

~~~bash
cd frontend && dart format lib/data/models/project_operating_setup_model.dart lib/modules/strategy/services/project_operating_setup_service.dart lib/modules/strategy/services/project_service.dart test/modules/strategy/services/project_operating_setup_service_test.dart test/modules/strategy/services/project_service_test.dart
cd frontend && flutter test test/modules/strategy/services/project_operating_setup_service_test.dart test/modules/strategy/services/project_service_test.dart -r compact
~~~

Expected: PASS.

- [ ] **Step 6: Commit.**

~~~bash
git add frontend/lib/data/models/project_operating_setup_model.dart \
  frontend/lib/modules/strategy/services/project_operating_setup_service.dart \
  frontend/lib/modules/strategy/services/project_service.dart \
  frontend/test/modules/strategy/services/project_operating_setup_service_test.dart \
  frontend/test/modules/strategy/services/project_service_test.dart
git commit -m "feat(frontend): add typed founder operating setup client"
~~~

### Task 4: Replace default kickoff with three simple persisted steps

**Files:**
- Create: frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart
- Create: frontend/lib/modules/strategy/views/project_roadmap_advanced_view.dart
- Modify: frontend/lib/modules/strategy/views/project_kickoff_view.dart
- Modify: frontend/test/project_kickoff_view_test.dart
- Test: frontend/test/modules/strategy/controllers/project_kickoff_controller_test.dart

**Interfaces:**
- Produces ProjectKickoffController.load, saveCurrentStep and activate.
- Produces ProjectKickoffView(projectId, onBack, onActivated, onOpenAdvancedRoadmap).
- Preserves current roadmap editor inside ProjectRoadmapAdvancedView.

- [ ] **Step 1: Write failing controller and widget tests.**

~~~dart
test('resume selects the first incomplete step', () async {
  final controller = ProjectKickoffController(
    service: FakeSetupService(inProgressSetup(problemStatement: 'Slow reporting')),
  );
  await controller.load('p-1');
  expect(controller.currentStep.value, 1);
});

testWidgets('P0 proposes two weeks and does not show 12-Week Year', (tester) async {
  await tester.pumpWidget(kickoffHarness(setup: draftP0Setup));
  expect(find.text('COSA đề xuất: Khám phá (P0) trong 2 tuần'), findsOneWidget);
  expect(find.textContaining('12-Week Year'), findsNothing);
});

testWidgets('activate navigates only after success', (tester) async {
  final activated = <String>[];
  await tester.pumpWidget(kickoffHarness(
    setup: completeP0Draft, onActivated: (id) => activated.add(id),
  ));
  await tester.tap(find.text('Xác nhận vòng đầu'));
  await tester.pump();
  expect(activated, ['p-1']);
});
~~~

The same test file contains five explicit invalid cases: empty target customer, empty problem statement, empty first-week outcome, an action list with zero or four entries, and P1 selected with NONE evidence. Each case expects the activate button disabled before submit; the P1 case also expects the explanatory evidence message.

- [ ] **Step 2: Run tests to verify they fail.**

Run:

~~~bash
cd frontend && flutter test test/modules/strategy/controllers/project_kickoff_controller_test.dart test/project_kickoff_view_test.dart -r compact
~~~

Expected: current roadmap view lacks simple controller/copy/callback.

- [ ] **Step 3: Extract advanced roadmap mechanically.**

Move existing ProjectKickoffView roadmap, AI, draft, dialog and stage-workspace implementation to ProjectRoadmapAdvancedView. Preserve all ProjectOrchestrationController calls. Change title to Lộ trình nâng cao and subtitle to Tùy chọn sau khi bạn đã hoàn tất vòng thiết lập cơ bản.

- [ ] **Step 4: Implement persisted controller.**

Controller stores setup, currentStep, loading/saving/error and editable field state.

~~~dart
Future<void> load(String projectId);
Future<bool> saveCurrentStep();
void selectEvidence(KickoffEvidenceLevel level);
bool get canActivate;
Future<bool> activate();
~~~

Use step 0 if customer/problem/evidence missing; step 1 if stage/duration missing; otherwise step 2. Evidence recomputes recommendation. Non-qualifying evidence forces P0/2 weeks. Qualifying evidence may use P1/4 weeks. Defaults review to weekday 5 and 16:00 in memory. saveCurrentStep uses PUT and never activates.

- [ ] **Step 5: Implement focused UI.**

Render progress and these primary strings:

~~~text
Ai đang gặp vấn đề này?
Vấn đề gây ảnh hưởng gì?
Bạn đã có gì để chứng minh?
COSA đề xuất: Khám phá (P0) trong 2 tuần
Kết quả của tuần 1
Ngày review tuần: Thứ Sáu · 16:00
Xác nhận vòng đầu
Lộ trình nâng cao
~~~

Step 1 has exactly three inputs. Step 2 only offers P0/P1 and valid duration chips. Step 3 edits one outcome and one to three actions. P0/P1 has no 12-week wording. Successful activation calls onActivated(projectId) once and creates no roadmap, task, mission, approval, calendar item or agent run.

- [ ] **Step 6: Run tests and commit.**

Run:

~~~bash
cd frontend && dart format lib/modules/strategy/controllers/project_kickoff_controller.dart lib/modules/strategy/views/project_kickoff_view.dart lib/modules/strategy/views/project_roadmap_advanced_view.dart test/project_kickoff_view_test.dart test/modules/strategy/controllers/project_kickoff_controller_test.dart
cd frontend && flutter test test/modules/strategy/controllers/project_kickoff_controller_test.dart test/project_kickoff_view_test.dart -r compact
~~~

Expected: PASS; roadmap controls appear only after Lộ trình nâng cao.

~~~bash
git add frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart \
  frontend/lib/modules/strategy/views/project_kickoff_view.dart \
  frontend/lib/modules/strategy/views/project_roadmap_advanced_view.dart \
  frontend/test/project_kickoff_view_test.dart \
  frontend/test/modules/strategy/controllers/project_kickoff_controller_test.dart
git commit -m "feat(frontend): guide founders through project kickoff"
~~~

### Task 5: Redirect all basic project creation to Kickoff

**Files:**
- Modify: frontend/lib/modules/dashboard/controllers/dashboard_controller.dart
- Modify: frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Modify: frontend/lib/modules/strategy/controllers/strategy_controller.dart
- Modify: frontend/lib/modules/strategy/views/tabs/project_roadmap_tab.dart
- Test: frontend/test/modules/hologram_hub/founder_command_center_controller_test.dart

**Interfaces:**
- Produces DashboardController.openProjectKickoff(String) and openGuidedProjectHub(String).
- Produces Future<String?> createFirstProject and StrategyController.createBasicProject.

- [ ] **Step 1: Write failing redirect and no-auto-work tests.**

~~~dart
test('first project returns P0 id without loading Command Center', () async {
  final controller = FounderCommandCenterController(
    strategyService: FakeStrategyService(createdProject: {'id': 'p-1', 'lifecycleStage': 'P0_DISCOVERY'}),
  );
  expect(await controller.createFirstProject(title: 'B2B SaaS', description: 'Reconcile invoices'), 'p-1');
  expect(controller.loadDashboardCallCount, 0);
});

testWidgets('basic create dialog has no stage selector', (tester) async {
  await tester.pumpWidget(hologramHarness());
  await tester.tap(find.text('Khởi tạo dự án ngay'));
  await tester.pumpAndSettle();
  expect(find.text('Tên dự án *'), findsOneWidget);
  expect(find.textContaining('P1:'), findsNothing);
  expect(find.textContaining('P2:'), findsNothing);
});
~~~

Add ProjectRoadmapTab tests: created project never calls generateRoadmap; IN_PROGRESS opens Kickoff; ACTIVE P0/P1 routes to Guided Hub.

- [ ] **Step 2: Run test to verify current P1/reload/AI behavior fails.**

Run:

~~~bash
cd frontend && flutter test test/modules/hologram_hub/founder_command_center_controller_test.dart test/project_kickoff_view_test.dart -r compact
~~~

Expected: current flow defaults P1, refreshes hub, has dropdown and auto-generates roadmap.

- [ ] **Step 3: Add one-shot dashboard targets.**

~~~dart
final pendingKickoffProjectId = RxnString();
final pendingGuidedHubProjectId = RxnString();
void openProjectKickoff(String id) { pendingKickoffProjectId.value = id; changePage(29, 1); }
void openGuidedProjectHub(String id) { pendingGuidedHubProjectId.value = id; changePage(0, 0); }
String? takeKickoffProjectId() {
  final id = pendingKickoffProjectId.value;
  pendingKickoffProjectId.value = null;
  return id;
}
String? takeGuidedHubProjectId() {
  final id = pendingGuidedHubProjectId.value;
  pendingGuidedHubProjectId.value = null;
  return id;
}
~~~

Page 29 is Dự án; group 1 is Chu kỳ & Chiến lược. IDs are navigation state only.

- [ ] **Step 4: Normalize every simple creation entry.**

FounderCommandCenterController.createFirstProject calls createBasicProject, returns ID, and removes stage, stageGoal, status, start date and loadDashboardData. Hologram dialog collects only title/description then invokes openProjectKickoff(id).

ProjectRoadmapTab replaces createProjectAndAutoDraftRoadmap with createBasicProjectAndOpenKickoff, never calls ProjectOrchestrationController.generateRoadmap, and consumes kickoff target in initState. Project list gets setup status: NOT_STARTED/IN_PROGRESS opens Kickoff; ACTIVE P0/P1 opens Guided Hub; remaining existing projects retain advanced roadmap access.

Do not modify HubStageMixin.completeCompanyActivation in this release: it has no caller in the current product surface. A future feature that wires it into the UI must use createBasicProject and openProjectKickoff rather than its present direct-stage/Next-Best-Action behavior.

- [ ] **Step 5: Consume Guided Hub target exactly once.**

Change loadDashboardData to receive optional project ID and select it rather than projects.first. HologramHubView consumes takeGuidedHubProjectId in post-frame callback then calls loadDashboardData(projectId: id), so existing GetX controller state cannot select the wrong project.

- [ ] **Step 6: Run tests and commit.**

Run:

~~~bash
cd frontend && flutter test test/modules/hologram_hub/founder_command_center_controller_test.dart test/project_kickoff_view_test.dart -r compact
~~~

Expected: create → Dự án → Kickoff receives exact ID; no P1 default and no auto roadmap.

~~~bash
git add frontend/lib/modules/dashboard/controllers/dashboard_controller.dart \
  frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart \
  frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart \
  frontend/lib/modules/strategy/controllers/strategy_controller.dart \
  frontend/lib/modules/strategy/views/tabs/project_roadmap_tab.dart \
  frontend/test/modules/hologram_hub/founder_command_center_controller_test.dart
git commit -m "feat(navigation): open new projects in founder kickoff"
~~~

### Task 6: Render truthful Guided Hub and suppress inferred metrics

**Files:**
- Create: frontend/lib/modules/hologram_hub/widgets/guided_project_hub_widget.dart
- Modify: frontend/lib/data/models/company_pulse_model.dart
- Modify: frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart
- Modify: frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/cofounder_card_widget.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart
- Test: frontend/test/modules/hologram_hub/guided_project_hub_widget_test.dart

**Interfaces:**
- Produces GuidedProjectHubWidget(project, setup, onAskCosa, onAdjustCycle).
- Makes unavailable pulse counts nullable; null values are never rendered.

- [ ] **Step 1: Write failing Guided Hub and truthfulness tests.**

~~~dart
testWidgets('P0 active setup shows cycle facts and founder actions, not generic KPIs', (tester) async {
  await tester.pumpWidget(guidedHubHarness(activeP0Setup(actions: ['Recruit 10 prospects'])));
  expect(find.text('Bạn đang ở: Khám phá (P0) · Tuần 1/2'), findsOneWidget);
  expect(find.text('Recruit 10 prospects'), findsOneWidget);
  expect(find.text('Missions đang chạy'), findsNothing);
  expect(find.textContaining('12-Week Year'), findsNothing);
});

test('pulse never infers missions from next best actions', () async {
  final pulse = await CoFounderApiService.getCompanyPulse(workspaceId: 'w-1', projectId: 'p-1');
  expect(pulse.activeMissions, isNull);
});
~~~

Add tests that empty Top 3 does not build Top3FocusWidget and nullable metrics never format as 0/0.

- [ ] **Step 2: Run tests to verify current Hub fails.**

Run:

~~~bash
cd frontend && flutter test test/modules/hologram_hub/guided_project_hub_widget_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart -r compact
~~~

Expected: widget missing and current pulse uses Top 3 length as mission count.

- [ ] **Step 3: Represent unavailable data honestly.**

Make all CompanyPulseModel counts nullable and rename companyStage to projectStage. CoFounderApiService only sets task/decision counts when authoritative responses contain entities; it sets activeMissions null, removes Top-3 fetch from pulse, and removes P1 fallback focus copy.

CoFounderCardWidget renders a stat only with non-null data; it omits divider/stat area if no stat exists. Top3FocusWidget has no empty-state card and no 12-Week Year Focus label; parent only builds it for persisted actions using title Ưu tiên vận hành hôm nay.

- [ ] **Step 4: Implement concise Guided Project Hub.**

Controller loads typed setup for selected project. For setup.isInitialLoop, Hologram renders this widget instead of Co-Founder card, Top 3 and Waiting-for-You:

~~~text
Project: <project title>
Bạn đang ở: <Khám phá (P0)|Xác thực vấn đề (P1)> · Tuần <n>/<duration>
Kết quả vòng này: <firstWeekOutcome>
Tiếp theo: <first action title>
[Cập nhật tiến độ] [Trao đổi với COSA] [Điều chỉnh vòng này]
~~~

Compute current week from project stageEnteredAt, clamped 1 through duration. Cập nhật tiến độ is disabled with tooltip Theo dõi tiến độ chi tiết sẽ được bổ sung ở vòng tiếp theo and does not mutate. Chat uses existing callback. Adjust routes same project back to Kickoff. Project without active initial setup preserves Command Center but now gets only real metrics.

- [ ] **Step 5: Run focused tests and analyzer.**

Run:

~~~bash
cd frontend && dart format lib/data/models/company_pulse_model.dart lib/modules/hologram_hub/services/cofounder_api_service.dart lib/modules/hologram_hub/controllers/founder_command_center_controller.dart lib/modules/hologram_hub/views/hologram_hub_view.dart lib/modules/hologram_hub/widgets/guided_project_hub_widget.dart lib/modules/hologram_hub/widgets/cofounder_card_widget.dart lib/modules/hologram_hub/widgets/top3_focus_widget.dart test/modules/hologram_hub/guided_project_hub_widget_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart
cd frontend && flutter test test/modules/hologram_hub/guided_project_hub_widget_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart -r compact
cd frontend && flutter analyze
~~~

Expected: PASS; Guided P0/P1 has no 12-week, mission count or zero KPI card.

- [ ] **Step 6: Commit.**

~~~bash
git add frontend/lib/data/models/company_pulse_model.dart \
  frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart \
  frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart \
  frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart \
  frontend/lib/modules/hologram_hub/widgets/guided_project_hub_widget.dart \
  frontend/lib/modules/hologram_hub/widgets/cofounder_card_widget.dart \
  frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart \
  frontend/test/modules/hologram_hub/guided_project_hub_widget_test.dart \
  frontend/test/modules/hologram_hub/founder_command_center_controller_test.dart
git commit -m "feat(hub): show truthful guided project startup"
~~~

### Task 7: Verify acceptance and record evidence

**Files:**
- Modify: docs/superpowers/specs/2026-09-01-founder-project-kickoff-design.md (status/evidence only)
- Modify: this plan (checkboxes only after pass)
- Test: all Task 2–6 suites

**Interfaces:**
- Produces evidence for all eight spec acceptance criteria without expanding to calendar, external message, agent dispatch, mission automation, 12-week automation, or operating-project import.

- [ ] **Step 1: Add final negative assertions.**

After successful activation assert zero new records for the project in operating.tasks, strategy.next_best_actions, and operating.twelve_week_cycles. Assert basic creation request contains none of P2_SOLUTION_FIT, P3_MVP_BUILD, P4_PMF_GROWTH, P5_SCALE_OPERATE.

- [ ] **Step 2: Run backend acceptance suite.**

Run:

~~~bash
cd services/company && npm test -- project-operating-setup.test.ts project-stage-lifecycle.test.ts project.test.ts event-outbox.test.ts
cd services/company && npm run typecheck
~~~

Expected: pass P0 default, resume, P0→P1 journal, tenant isolation, invalid duration and no side effects.

- [ ] **Step 3: Run frontend acceptance suite.**

Run:

~~~bash
cd frontend && flutter test \
  test/modules/strategy/services/project_operating_setup_service_test.dart \
  test/modules/strategy/services/project_service_test.dart \
  test/modules/strategy/controllers/project_kickoff_controller_test.dart \
  test/project_kickoff_view_test.dart \
  test/modules/hologram_hub/founder_command_center_controller_test.dart \
  test/modules/hologram_hub/guided_project_hub_widget_test.dart -r compact
cd frontend && flutter analyze
~~~

Expected: pass create redirect, P0/P1 copy, resume and no inferred UI.

- [ ] **Step 4: Run repository integrity checks.**

Run:

~~~bash
make contract-freeze-check
git diff --check
git status --short
~~~

Expected: no whitespace error; contract gate passes; unrelated dirty files remain unstaged.

- [ ] **Step 5: Record evidence only after gates pass.**

Change spec status to Implemented — verified YYYY-MM-DD only if Steps 2–4 pass. Under acceptance list add exact test files for criteria 1–8. If any gate fails, retain Proposed and leave failed checkboxes unchecked.

- [ ] **Step 6: Commit evidence.**

~~~bash
git add docs/superpowers/specs/2026-09-01-founder-project-kickoff-design.md docs/superpowers/plans/2026-09-01-founder-project-kickoff.md
git commit -m "docs: record founder kickoff acceptance evidence"
~~~

## Spec coverage self-review

| Spec requirement | Tasks |
|---|---|
| Create redirects to Project Kickoff and starts P0 | 3, 5 |
| Three-step setup and resume | 2, 4 |
| Timebox, target date, review and outcome persist | 1, 2, 3, 4 |
| P0→P1 uses canonical transition/audit | 2, 7 |
| 12-Week Year is optional, never P0/P1 prerequisite | 4, 5, 6, 7 |
| Guided Hub reads persisted first-week data | 5, 6 |
| No inferred metrics/missions/Top 3 | 6, 7 |
| Tenant binding, validation and reload survival | 1, 2, 3, 7 |
| Advanced roadmap remains available but secondary | 4, 5 |

No spec requirement is omitted. Calendar, external message, automatic agent/mission, full multi-stage roadmap and operating-project import remain out of scope.
