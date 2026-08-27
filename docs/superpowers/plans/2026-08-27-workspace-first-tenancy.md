# Workspace-First Tenancy and Multi-Project Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa Workspace thành tenant duy nhất trong toàn bộ product contract; giữ platform company ID chỉ ở integration đồng bộ nội bộ; đồng thời hỗ trợ Task và OKR Objective liên kết không bắt buộc với nhiều Project cùng Workspace.

**Architecture:** Identity là authority của local Workspace projection và membership. Mọi business endpoint lấy Workspace từ bearer token cộng X-Workspace-Id, sau đó query bằng id + workspace_id ngay tại database. Project chỉ là thực thể tổ chức công việc trong Workspace. COSA, Agent Core và frontend dùng workspace_id duy nhất; một adapter private trong Identity giữ mapping platform_company_id khi đồng bộ hoặc lấy policy từ Platform.

**Tech Stack:** TypeScript strict, Encore, Drizzle ORM, PostgreSQL 16, Python 3.11, FastAPI, Pydantic, SQLAlchemy/asyncpg, pytest, Vitest/Encore test, Flutter và GitHub Actions.

**Spec:** docs/superpowers/specs/2026-08-27-workspace-first-tenancy-design.md

## Global Constraints

- Workspace là khóa tenant duy nhất trong mọi product API, DTO, header, response, Agent Core model, repository và UI. Project không được dùng như tenant.
- Không sửa immutable migration đã phát hành. Các thay đổi database mới đi vào migration số tiếp theo; migration phải fail trước khi xóa dữ liệu nếu phát hiện row không có workspace_id hoặc quan hệ chéo Workspace.
- companyId và company_id không đi qua browser, public API, TenantContext hay run payload. Chỉ private Platform integration tại Identity mới được đọc core.workspaces.platform_company_id.
- Mọi create lấy workspace từ server-authoritative TenantContext, không từ request body, query hoặc path. Mọi get/update/delete tenant-owned có điều kiện SQL id + workspace_id và trả 404 khi không thuộc scope.
- Không dùng fallback từ company sang workspace trên public resolver. Projection hoặc membership chưa đồng bộ phải fail closed, không chấp nhận workspace do client tự chọn.
- Không xóa hoặc hoàn nguyên các thay đổi ngoài phạm vi trong working tree. Đặc biệt, các chỉnh sửa hiện có dưới skillpacks/ không thuộc plan này.
- Giữ packages/agent_core độc lập với services/ và apps/; mapping Platform phải được thực hiện ở Identity/COSA composition boundary, không từ Agent Core.
- Hoàn thành Task 1–8 và tenant-isolation suite trước khi mở Phase B runtime activation từ kế hoạch Skillpacks.

---

## File map

| File | Trách nhiệm sau điều chỉnh |
| --- | --- |
| services/company/shared/types/tenant_context.ts | TenantContext chỉ chứa workspace, principal, membership, permissions và correlation. |
| services/company/identity/services/tenant-context.service.ts | Resolve membership cho đúng Workspace, không còn fallback company/workspace hoặc workforce lookup không scope. |
| services/company/identity/services/sync.service.ts | Đồng bộ Workspace projection theo Platform bên trong server; company ID không trả về browser. |
| services/company/identity/services/platform.client.ts | Liệt kê và xác minh private Platform memberships cho sync, không đưa company ID vào product DTO. |
| services/company/shared/services/workspace-resolver.service.ts | Chỉ resolve Workspace ID public; private mapping Platform tách sang Identity integration service. |
| services/company/operations/migrations/12_workspace_project_integrity_and_links.up.sql | Kiểm tra orphan, bổ sung unique/FK composite và hai bảng link Task/Objective–Project. |
| services/company/operations/migrations/13_backfill_task_project_links.up.sql | Backfill chỉ Task → Initiative → Project hợp lệ và có cùng Workspace. |
| services/company/shared/db/schema/operations.ts | Khai báo link tables và composite-relation fields dùng bởi services. |
| services/company/operations/services/{project,task,okr}.service.ts | Service API workspace-scoped cho Project/Portfolio và các project links. |
| services/company/operations/handlers/{project,task,okr}.handler.ts | Public endpoint lấy X-Workspace-Id + Authorization; không nhận workspace trong body. |
| services/company/operations/strategy/handlers/*.ts | Mười Strategy handler dùng cùng membership guard và scoped lookup/list/write. |
| apps/cosa/auth/{dependency,company_client,cosa_client}.py | Thay bằng identity workspace-only; bỏ header/company membership cross-check công khai. |
| apps/cosa/{api,worker,policies,capabilities}/ | Không tạo, lưu hoặc truyền company_id; policy/connector lookup keyed by Workspace. |
| packages/agent_core/{contracts,runs,conversations,artifacts,memory,migrations}/ | Bỏ company_id và tenant_id dư thừa, giữ workspace_id là tenant key duy nhất. |
| services/cosa/{storage,handlers,services,migrations}/ | Chuyển connector, schedule và policy product scope từ company + workspace sang workspace. |
| frontend/lib/{core,modules}/ | Chỉ lưu workspace_id, gửi X-Workspace-Id, đổi Company Picker/Runtime product wording sang Workspace. |
| tests/agent_core, tests/apps/cosa, services/company/**/tests, frontend/test | Bảo vệ multi-workspace membership, 404 cross-scope, link integrity, API/header và UI storage contract. |

---

### Task 1: Chốt TenantContext workspace-only và đóng các fallback Identity

**Files:**

- Modify: services/company/shared/types/tenant_context.ts
- Modify: services/company/identity/services/tenant-context.service.ts
- Modify: services/company/identity/handlers/tenant-context.handler.ts
- Modify: services/company/shared/auth/workspace-access.ts
- Modify: services/company/shared/services/workspace-resolver.service.ts
- Create: services/company/identity/services/platform-workspace-mapping.service.ts
- Modify: services/company/identity/tests/tenant-context.test.ts
- Modify: services/company/identity/tests/tenant-context-endpoint.test.ts
- Modify: services/company/shared/tests/workspace-resolver.test.ts

**Interfaces:**

- Produces TenantContext with workspaceId, userId, optional workforceMemberId, membershipRole, permissions and correlationId only.
- Changes POST /identity/tenant-context/resolve to accept { workspaceId } plus Authorization and return no companyId.
- Produces resolveProductWorkspaceId({ workspaceId }) with no company fallback, while private resolveWorkspaceForPlatformCompany(platformCompanyId) is callable only by identity sync/policy integration.

- [ ] **Step 1: Add failing resolver and endpoint tests**

Add one test where a valid user has memberships in ws_a and ws_b, then resolves ws_a successfully and cannot resolve ws_b after membership removal. Add a second test where the server has no local projection for a platform membership and assert that a supplied workspace ID is denied instead of accepted. Add an endpoint assertion that companyId is absent:

~~~ts
expect(response).toMatchObject({ workspaceId: workspaceA, userId: userId });
expect(response).not.toHaveProperty("companyId");
~~~

- [ ] **Step 2: Verify the failing behavior**

Run:

~~~bash
cd services/company && encore test
~~~

Expected: new tests expose the companyId request/response contract and the resolver's company-to-workspace fallback; the suite is red before behavior changes.

- [ ] **Step 3: Make membership the only product-scope authority**

Replace the public input shape with:

~~~ts
export interface ResolveTenantContextParams {
  authorization?: string;
  workspaceId: string | number;
}

export interface TenantContext {
  readonly workspaceId: string;
  readonly userId: string;
  readonly workforceMemberId?: string;
  readonly membershipRole: string;
  readonly permissions: readonly string[];
  readonly correlationId: string;
}
~~~

Resolve core.workspace_memberships by both user and workspace. Scope any workforce member lookup to the same workspace. Move the platform_company_id lookup into the new private service and make it unavailable to Encore public handlers. Keep requireWorkspaceAccess as a thin call to the new resolver.

- [ ] **Step 4: Make the resolver fail closed**

For a missing membership, deleted workspace or unmapped projection, return the existing unauthenticated/permission error; do not substitute a client workspace ID, company ID or default workspace. Product endpoints may pass the header's Workspace ID only to requireWorkspaceAccess, never to a company mapping helper.

- [ ] **Step 5: Run focused Identity regression tests**

Run:

~~~bash
cd services/company && encore test
~~~

Expected: a user can select either legitimate Workspace; a non-member and an unresolved sync projection both fail closed; product resolver tests contain no companyId input.

- [ ] **Step 6: Commit**

~~~bash
git add services/company/shared/types/tenant_context.ts services/company/identity/services/tenant-context.service.ts services/company/identity/handlers/tenant-context.handler.ts services/company/shared/auth/workspace-access.ts services/company/shared/services/workspace-resolver.service.ts services/company/identity/services/platform-workspace-mapping.service.ts services/company/identity/tests/tenant-context.test.ts services/company/identity/tests/tenant-context-endpoint.test.ts services/company/shared/tests/workspace-resolver.test.ts
git commit -m "refactor: resolve product tenancy by workspace membership"
~~~

### Task 2: Enforce Workspace/Project integrity in the database before exposing links

**Files:**

- Create: services/company/operations/migrations/12_workspace_project_integrity_and_links.up.sql
- Modify: services/company/shared/db/schema/operations.ts
- Modify: services/company/operations/tests/project.test.ts
- Modify: services/company/operations/tests/task.test.ts
- Modify: services/company/operations/tests/okr.test.ts

**Interfaces:**

- Produces operating.task_projects(workspace_id, task_id, project_id, created_at) with primary key (task_id, project_id).
- Produces strategy.okr_objective_projects(workspace_id, objective_id, project_id, created_at) with primary key (objective_id, project_id).
- Adds UNIQUE (id, workspace_id) to operating.tasks, strategy.okr_objectives, strategy.projects and strategy.portfolios; every new relationship references its target through the same workspace.

- [ ] **Step 1: Add migrations-first integrity tests**

In the existing project, task and OKR test suites, create Workspace A and B fixtures. Assert that inserting a Task A → Project B and Objective A → Project B relation rejects with a foreign-key error, while two Project A links succeed. Add one test for a workspace-wide Task and Objective with no link rows:

~~~ts
expect(await listTaskProjectIds(taskA.id, workspaceA)).toEqual([]);
await expect(linkTaskProject(taskA.id, projectB.id, workspaceA)).rejects.toThrow();
~~~

- [ ] **Step 2: Verify the current schema cannot protect the relation**

Run:

~~~bash
cd services/company && encore test
~~~

Expected: the new link-table imports/methods are unavailable and the suite fails before migration/schema implementation.

- [ ] **Step 3: Add preflight and composite constraints in migration 12**

At the start of the migration, query and raise a descriptive exception for:

1. project.portfolio_id referring to a portfolio in another Workspace;
2. portfolio_projects whose project or portfolio does not match row.workspace_id;
3. any null workspace_id in a relation target.

Then add composite uniqueness, replace global project/portfolio foreign keys with same-workspace foreign keys, and create both link tables. Use a composite foreign key such as:

~~~sql
FOREIGN KEY (project_id, workspace_id)
  REFERENCES strategy.projects (id, workspace_id)
  ON DELETE CASCADE
~~~

For nullable projects.portfolio_id, use the PostgreSQL column-list form ON DELETE SET NULL (portfolio_id), leaving projects.workspace_id intact. Do not silently delete orphaned or cross-workspace historical rows.

- [ ] **Step 4: Model the tables in Drizzle**

Export taskProjects and okrObjectiveProjects from shared/db/schema/operations.ts. Add explicit workspaceId, taskId/objectiveId and projectId fields so domain services can use these tables without raw SQL. Preserve existing initiatives.projectId and twelveWeekCycles.projectId semantics; neither becomes a tenant key.

- [ ] **Step 5: Run migration and service regression suites**

Run:

~~~bash
make services-migrate-company
cd services/company && encore test
~~~

Expected: fresh schema applies migration 12; same-workspace links and zero-link entities work; all cross-workspace combinations are rejected by the database.

- [ ] **Step 6: Commit**

~~~bash
git add services/company/operations/migrations/12_workspace_project_integrity_and_links.up.sql services/company/shared/db/schema/operations.ts services/company/operations/tests/project.test.ts services/company/operations/tests/task.test.ts services/company/operations/tests/okr.test.ts
git commit -m "feat: enforce workspace scoped project relations"
~~~

### Task 3: Harden Project, Portfolio and every Strategy endpoint with one Workspace guard

**Files:**

- Modify: services/company/operations/services/project.service.ts
- Modify: services/company/operations/handlers/project.handler.ts
- Modify: services/company/operations/strategy/handlers/{assumption,decision-record,discovery-signal,evidence,experiment,gate-evaluation,interview,next-best-action,stage-policy,stage-transition}.handler.ts
- Modify: services/company/operations/strategy/handlers/index.ts
- Modify: services/company/operations/tests/project.test.ts
- Modify: services/company/operations/strategy/tests/strategy-handlers.test.ts

**Interfaces:**

- Changes Project/Portfolio create input to omit workspaceId; handlers derive it from requireWorkspaceAccess(authorization, xWorkspaceId).
- Produces getProjectService(id, context), listProjectsService(context), createProjectService(input, context), and equivalent Portfolio methods.
- Requires each Strategy handler to receive Authorization and X-Workspace-Id and to scope every select/update/delete by workspaceId.

- [ ] **Step 1: Write endpoint-level cross-Workspace tests**

Convert strategy handler tests from direct unauthenticated calls to requests/handler calls carrying the authenticated Workspace context. Create a Project and strategy chain in Workspace A; request its ID with an authenticated Workspace B caller and assert 404. Add a create test proving a workspaceId in a JSON body is ignored/rejected:

~~~ts
expect(await getProjectAs(workspaceB, projectA.id)).rejects.toMatchObject({ code: "not_found" });
expect(await createProjectAs(workspaceA, { title: "A", workspaceId: workspaceB })).toHaveProperty("workspaceId", workspaceA);
~~~

- [ ] **Step 2: Verify the current exposure**

Run:

~~~bash
cd services/company && encore test
~~~

Expected: project routes currently have no membership guard and at least one Strategy get/update/list path accepts an ID or empty filter outside Workspace A.

- [ ] **Step 3: Refactor Project and Portfolio contracts**

At each public handler, require Authorization and X-Workspace-Id, resolve TenantContext once, and pass it to the service. Remove /operations/workspaces/:workspaceId/projects and /portfolios product route variants. Use:

~~~ts
const [row] = await db.select().from(projects)
  .where(and(eq(projects.id, BigInt(id)), eq(projects.workspaceId, BigInt(context.workspaceId))))
  .limit(1);
~~~

Validate a requested portfolio with the same predicate before a Project insert/update. Return generic not-found when its id belongs to another Workspace.

- [ ] **Step 4: Apply the same pattern to Strategy**

For all ten Strategy handler files:

1. remove companyId and optional workspace filters from public request types;
2. require a resolved Workspace context for list/create/read/update/delete;
3. filter target IDs in SQL with workspaceId, not after an unscoped read;
4. validate every related project, policy, assumption, experiment, evidence, evaluation, candidate and transition in the active Workspace before use.

Do not leave a query where absence of workspaceId means all Workspaces. Keep deterministic strategy calculations unchanged.

- [ ] **Step 5: Run tenancy regressions**

Run:

~~~bash
cd services/company && encore test
make services-test-company
~~~

Expected: authenticated members see only their Workspace Project/Portfolio/Strategy records; all legacy unauthenticated calls fail; existing same-Workspace strategy chain remains green.

- [ ] **Step 6: Commit**

~~~bash
git add services/company/operations/services/project.service.ts services/company/operations/handlers/project.handler.ts services/company/operations/strategy/handlers services/company/operations/tests/project.test.ts services/company/operations/strategy/tests/strategy-handlers.test.ts
git commit -m "fix: scope project and strategy operations to workspace"
~~~

### Task 4: Expose many-to-many Task and Objective project links, then backfill only proven Task links

**Files:**

- Create: services/company/operations/migrations/13_backfill_task_project_links.up.sql
- Modify: services/company/operations/services/task.service.ts
- Modify: services/company/operations/handlers/task.handler.ts
- Modify: services/company/operations/services/okr.service.ts
- Modify: services/company/operations/handlers/okr.handler.ts
- Modify: services/company/operations/tests/task.test.ts
- Modify: services/company/operations/tests/okr.test.ts

**Interfaces:**

- Produces task response and Objective response field projectIds: string[]; no rows means [].
- Produces workspace-scoped add/list/remove operations for Task and Objective project links.
- Backfills only rows that satisfy task.workspace_id = initiative.workspace_id = initiative.project.workspace_id; Objective links are never inferred.

- [ ] **Step 1: Add failing multi-project behavior tests**

Create a Task in Workspace A, link it to Project A1 and A2, and assert the API returns both stable IDs. Repeat for an Objective. Assert duplicate add is idempotent, unlink removes one link, and a Project B link returns not-found/invalid-argument without revealing Project B:

~~~ts
expect(task.projectIds).toEqual([projectA1.id, projectA2.id]);
expect(objectiveWithoutLinks.projectIds).toEqual([]);
~~~

- [ ] **Step 2: Verify current behavior has no relationship API**

Run:

~~~bash
cd services/company && encore test
~~~

Expected: tests fail because Task and OKR Objective DTOs/services expose no projectIds or safe link operations.

- [ ] **Step 3: Implement workspace-scoped link services**

Add handlers under the existing resource routes:

~~~text
POST   /operations/tasks/:id/projects
GET    /operations/tasks/:id/projects
DELETE /operations/tasks/:id/projects/:projectId
POST   /operations/okr/objectives/:id/projects
GET    /operations/okr/objectives/:id/projects
DELETE /operations/okr/objectives/:id/projects/:projectId
~~~

Each operation resolves TenantContext from Authorization + X-Workspace-Id, fetches both target records through id + workspace_id, then writes/reads the link table scoped by workspace. Preserve existing Task and OKR commands; link changes do not require or create a synthetic shared Project.

- [ ] **Step 4: Add an idempotent, non-inferential backfill migration**

Migration 13 inserts task_projects from operating.tasks joined to strategy.initiatives and strategy.projects only where all three workspace IDs agree and initiative.project_id is not null:

~~~sql
INSERT INTO operating.task_projects (workspace_id, task_id, project_id, created_at)
SELECT t.workspace_id, t.id, p.id, NOW()
FROM operating.tasks t
JOIN strategy.initiatives i ON i.id = t.initiative_id AND i.workspace_id = t.workspace_id
JOIN strategy.projects p ON p.id = i.project_id AND p.workspace_id = t.workspace_id
ON CONFLICT (task_id, project_id) DO NOTHING;
~~~

Add a postcondition that fails if the query could produce a cross-Workspace relation. Do not create Objective links from cycle, key-result or title heuristics.

- [ ] **Step 5: Run migration and focused regressions**

Run:

~~~bash
make services-migrate-company
cd services/company && encore test
~~~

Expected: valid historical Task-to-Initiative-to-Project chains receive one link; missing/inconsistent legacy data remains unlinked; new APIs allow zero, one and many same-Workspace links only.

- [ ] **Step 6: Commit**

~~~bash
git add services/company/operations/migrations/13_backfill_task_project_links.up.sql services/company/operations/services/task.service.ts services/company/operations/handlers/task.handler.ts services/company/operations/services/okr.service.ts services/company/operations/handlers/okr.handler.ts services/company/operations/tests/task.test.ts services/company/operations/tests/okr.test.ts
git commit -m "feat: link workspace tasks and objectives to projects"
~~~

### Task 5: Remove Platform company identity from public Identity, login and selection flows

**Files:**

- Modify: services/company/identity/services/platform.client.ts
- Modify: services/company/identity/services/sync.service.ts
- Modify: services/company/identity/handlers/sync.handler.ts
- Modify: services/company/identity/services/tenant-context.service.ts
- Modify: services/company/identity/tests/sync.test.ts
- Modify: frontend/lib/modules/auth/services/auth_service.dart
- Modify: frontend/lib/modules/auth/controllers/auth_controller.dart
- Create: frontend/lib/modules/workspace_picker/{bindings,controllers,views}/workspace_picker_*.dart
- Delete: frontend/lib/modules/company_picker/bindings/company_picker_binding.dart
- Delete: frontend/lib/modules/company_picker/controllers/company_picker_controller.dart
- Delete: frontend/lib/modules/company_picker/views/company_picker_view.dart
- Modify: frontend/lib/core/routing/app_pages.dart
- Modify: frontend/test/auth_flow_test.dart

**Interfaces:**

- Produces private listPlatformMemberships(token) used server-side by sync; no browser request carries company_id.
- Changes sync result to local token plus WorkspaceSummary[] containing workspaceId, name, role and status only.
- Replaces CompanyMembershipInfo and Company Picker with WorkspaceSummary and Workspace Picker; only workspace_id is persisted by the frontend.

- [ ] **Step 1: Add failing contract tests at both boundaries**

In Identity sync tests, mock multiple Platform memberships and assert response values have workspaceId but never companyId/platformCompanyId. In frontend tests, assert final request after login contains no company_id, SharedPreferences has no company_id, and the selection UI renders “Chọn workspace”:

~~~dart
expect(prefs.getString('company_id'), isNull);
expect(headers.containsKey('X-Company-Id'), isFalse);
~~~

- [ ] **Step 2: Verify the legacy public company flow**

Run:

~~~bash
cd services/company && encore test
cd frontend && flutter test test/auth_flow_test.dart
~~~

Expected: current tests/code show companyId in platform-sync payload, result DTO and picker state.

- [ ] **Step 3: Make sync an internal platform projection operation**

Have sync authenticate the Platform token, obtain the caller's memberships inside services/company, upsert each workspace by private platform_company_id, and return sanitized WorkspaceSummary records. Do not provide a public companyId parameter. A missing projection/membership is a sync failure, not a local Workspace creation bypass.

Keep core.workspaces.platform_company_id and private platform mapping code. Its values must not be serialized into SyncFromPlatformResult, /identity/me, logs intended for users, or any frontend model.

- [ ] **Step 4: Switch the Flutter product model and routes**

Delete the old company_picker files only after app_pages and AuthController use WorkspacePicker. Replace names, text and state from companyId/company list to WorkspaceSummary/workspace list. Store selection solely in secure workspace_id. If a user has one Workspace, select it; if several, show Workspace Picker. Do not rename Platform-facing internal transport fields in a way that makes a public company ID reappear in app state.

- [ ] **Step 5: Run product contract regressions**

Run:

~~~bash
cd services/company && encore test
cd frontend && flutter test test/auth_flow_test.dart
cd frontend && flutter analyze
~~~

Expected: login/sync/selection is Workspace-only in app contracts; Identity still maintains private platform mapping; Flutter analyzer reports zero diagnostics.

- [ ] **Step 6: Commit**

~~~bash
git add services/company/identity/services/platform.client.ts services/company/identity/services/sync.service.ts services/company/identity/handlers/sync.handler.ts services/company/identity/services/tenant-context.service.ts services/company/identity/tests/sync.test.ts frontend/lib/modules/auth/services/auth_service.dart frontend/lib/modules/auth/controllers/auth_controller.dart frontend/lib/modules/workspace_picker frontend/lib/core/routing/app_pages.dart frontend/test/auth_flow_test.dart
git rm frontend/lib/modules/company_picker/bindings/company_picker_binding.dart frontend/lib/modules/company_picker/controllers/company_picker_controller.dart frontend/lib/modules/company_picker/views/company_picker_view.dart
git commit -m "refactor: expose workspace instead of company in product login"
~~~

### Task 6: Cut COSA and Control Plane product paths over to workspace-only scope

**Files:**

- Modify: apps/cosa/auth/dependency.py
- Rename: apps/cosa/auth/company_client.py to apps/cosa/auth/workspace_client.py
- Delete: apps/cosa/auth/cosa_client.py
- Modify: apps/cosa/api/{routes,schemas}.py
- Modify: apps/cosa/worker/handlers.py
- Modify: apps/cosa/{policies,capabilities,composition}/**/*.py
- Modify: services/cosa/{storage/control-plane-schema.ts,storage/schema.ts,handlers/agent-policy.handler.ts,handlers/workspace-connector.handler.ts,handlers/workspace-schedule.handler.ts,services/agent-policy.service.ts,services/workspace-connector.service.ts,services/workspace-schedule.service.ts}
- Create: services/cosa/migrations/13_workspace_only_product_scope.up.sql
- Modify: services/cosa/tests/{agent-policy,workspace-connector,workspace-schedule}.test.ts
- Modify: tests/apps/cosa/auth/{test_dependency,test_cosa_client}.py
- Rename: tests/apps/cosa/policies/test_company_policy_client.py to tests/apps/cosa/policies/test_workspace_policy_client.py
- Modify: tests/apps/cosa/{auth_test_helpers,policy_test_helpers,test_tenant_isolation,test_artifact_routes,test_scheduled_session_worker,test_workspace_execution_e2e}.py

**Interfaces:**

- AuthenticatedIdentity contains principal_id, platform_user_id, workspace_id, role_id and bearer_token; no company_id.
- COSA requires Authorization + X-Workspace-Id and resolves it through Identity's workspace-only endpoint.
- Connector grants, schedules and policy snapshots are keyed by workspace_id; any Platform-company lookup occurs inside a private Identity/Platform adapter and its output never includes company ID.

- [ ] **Step 1: Add failing workspace-only COSA tests**

Replace the dependency fixture response with no companyId. Add tests that missing X-Workspace-Id is 400, X-Company-Id is ignored/rejected at the boundary, a non-member gets 403, and a correct Workspace gets an AuthenticatedIdentity without company_id:

~~~python
identity = await get_authenticated_identity(
    authorization=f"Bearer {_token(sub='99')}", x_workspace_id="ws_authoritative"
)
assert identity.workspace_id == "ws_authoritative"
assert not hasattr(identity, "company_id")
~~~

Add connector, schedule, policy and run tests showing two different Workspace IDs cannot access each other's data even if their historical platform company identifiers would collide.

- [ ] **Step 2: Verify current auth and payload dependency**

Run:

~~~bash
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/auth/test_dependency.py tests/apps/cosa/test_tenant_isolation.py -q
cd services/cosa && encore test
~~~

Expected: current code/test construction requires X-Company-Id and passes company_id in policy, grant, schedule and worker payloads.

- [ ] **Step 3: Replace public COSA authentication**

Implement WorkspaceTenantContextClient.resolve(bearer_token, workspace_id), calling Identity with { workspaceId }. dependency.py validates bearer identity and header then compares the server response Workspace ID to the request. Remove CosaControlPlaneAuthClient from this product path. Rename test helpers and all dependency overrides at the same time so no stale company fixture keeps a false-green test.

- [ ] **Step 4: Scope COSA control-plane product records by Workspace**

In migration 13, verify workspace_id is non-null before dropping company_id and any combined company/workspace indexes from connector installation, authorization, grant and schedule tables. Update Drizzle schema, services and handlers to receive Workspace scope. Policy client asks the private bridge for a workspace-keyed snapshot whose model has workspace_id, workspace_status, principal_status and rules. The private bridge may map to an upstream company only inside the Platform integration implementation.

- [ ] **Step 5: Remove company from FastAPI transport and worker**

Delete company fields from all response models, conversation/run API checks, scheduler payloads, RunRequest creation, artifact creation, connector assertion and policy snapshot contexts. Make every API/repository call use workspace_id. User-visible behavior for an inaccessible resource remains 404.

- [ ] **Step 6: Run COSA and Control Plane suites**

Run:

~~~bash
cd services/cosa && encore test
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/auth tests/apps/cosa/policies tests/apps/cosa/test_tenant_isolation.py tests/apps/cosa/test_artifact_routes.py tests/apps/cosa/test_scheduled_session_worker.py -q
make apps-cosa-test
~~~

Expected: only X-Workspace-Id is accepted; cross-Workspace requests never disclose a record; policy, connector, schedule and worker runs remain functional without company values.

- [ ] **Step 7: Commit**

~~~bash
git add apps/cosa services/cosa tests/apps/cosa
git commit -m "refactor: scope cosa product runtime by workspace"
~~~

### Task 7: Migrate Agent Core to workspace_id as its sole tenant key

**Files:**

- Create: packages/agent_core/migrations/017_workspace_only_tenancy.sql
- Modify: packages/agent_core/contracts/run.py
- Modify: packages/agent_core/runs/{models,repository}.py
- Modify: packages/agent_core/conversations/{models,repository}.py
- Modify: packages/agent_core/artifacts/{models,repository,postgres}.py
- Modify: packages/agent_core/memory/{models,providers/postgres}.py
- Modify: packages/agent_core/kernel/openai_agents_kernel.py
- Modify: tests/agent_core/{runs,artifacts,memory}/**/*.py
- Modify: tests/apps/cosa/{test_tenant_isolation,test_artifact_routes,worker/test_handlers}.py

**Interfaces:**

- RunRequest, RunRecord, ConversationRecord, WorkspaceArtifact and MemoryItem carry workspace_id but not company_id or tenant_id.
- Repository get/list/archive methods accept workspace_id in their scope signatures, and SQL applies it directly.
- Migration 017 verifies workspace scope, removes company_id and redundant tenant_id from Agent Core tenant-owned tables, and leaves migrations 001/006/009/016 unchanged.

- [ ] **Step 1: Add failing model and repository isolation tests**

Update test factories to construct only workspace-scoped models. Store records in ws_a and ws_b, then assert all get/list/archive calls return only rows from the selected Workspace:

~~~python
assert await artifacts.get("ws_b", artifact_a.artifact_id) is None
assert await conversations.get_scoped_conversation("ws_b", conversation_a.conversation_id) is None
~~~

Add schema-migration test/preflight coverage for a null workspace_id row so migration refuses to drop legacy scope columns.

- [ ] **Step 2: Verify current interfaces are company-dependent**

Run:

~~~bash
PYTHONPATH=. .venv/bin/pytest tests/agent_core/runs tests/agent_core/artifacts tests/agent_core/memory tests/apps/cosa/test_tenant_isolation.py -q
~~~

Expected: changed factories/tests fail because the present Pydantic models and repository calls require company_id.

- [ ] **Step 3: Remove redundant scope fields in models and SQL**

Change interfaces to:

~~~python
class RunRequest(BaseModel):
    workspace_id: str
    # no tenant_id and no company_id
~~~

Apply equivalent deletions throughout model serialization, in-memory filtering, Postgres INSERT/SELECT/WHERE clauses, kernel context and tests. Do not replace company_id with a second alias field. Tenant scope SQL must contain workspace_id for every tenant-bound read/write.

- [ ] **Step 4: Add immutable migration 017**

The migration first raises on missing workspace_id in agent_core.runs, agent_conversation.conversations, agent_memory.agent_memories and agent_artifact.workspace_artifacts. It then drops company_id, tenant_id and their indexes/metadata backfill references, adds/retains workspace indexes, and preserves all rows with valid Workspace scope. Remove legacy _company_id metadata keys only after columns are removed and migration has preserved non-scope metadata.

- [ ] **Step 5: Run database and application regression suites**

Run:

~~~bash
PYTHONPATH=. .venv/bin/python -m packages.agent_core.scripts.migrate
PYTHONPATH=. .venv/bin/pytest tests/agent_core tests/apps/cosa -q
make agent-core-test
make apps-cosa-test
~~~

Expected: migrations apply on a fresh and upgraded database; Agent Core remains package-boundary clean; every run/conversation/artifact/memory tenant check depends only on Workspace.

- [ ] **Step 6: Commit**

~~~bash
git add packages/agent_core tests/agent_core tests/apps/cosa
git commit -m "refactor: make workspace the sole agent core tenant key"
~~~

### Task 8: Remove remaining client company headers and complete the end-to-end tenant gate

**Files:**

- Modify: frontend/lib/core/network/api_client.dart
- Modify: frontend/lib/core/network/workspace_scoped_service.dart
- Modify: frontend/lib/modules/{chat,company_runtime,finance,legal,sales,strategy}/**/*.dart
- Rename: frontend/lib/modules/company_runtime to frontend/lib/modules/workspace_runtime
- Modify: frontend/lib/core/routing/app_pages.dart
- Modify: frontend/test/{auth_flow_test,company_runtime_service_test,company_runtime_views_test,modules/chat/chat_module_test,modules/chat/session_view_test}.dart
- Modify: Makefile
- Modify: .github/workflows/quality.yml
- Modify: docs/features/skills.md

**Interfaces:**

- ApiClient sends Authorization and X-Workspace-Id only; it never reads SharedPreferences company_id.
- Every frontend workspace-scoped service relies on the header, not a client-controlled workspace_id query/body value unless a legacy endpoint expressly requires it during transitional removal.
- Produces make tenancy-check, included in verify and CI, which runs the Company, COSA and Agent Core workspace-isolation suites.

- [ ] **Step 1: Add failing frontend and black-box tenant tests**

Add a mock HTTP assertion that outgoing headers never contain X-Company-Id and that a JSON body with workspaceId is not emitted by create calls. Add an end-to-end scenario with one principal in ws_a and ws_b verifying data, finance/CRM workspace records, Task/OKR links, conversations and artifacts never cross selection.

- [ ] **Step 2: Verify legacy header/state leaks**

Run:

~~~bash
cd frontend && flutter test
rg -n 'X-Company-Id|company_id|companyId' frontend/lib apps/cosa packages/agent_core
~~~

Expected: pre-change scan identifies the remaining product leaks; tests make the HTTP header assertion red.

- [ ] **Step 3: Delete product company persistence and terminology**

Remove companyId() from WorkspaceScopedService and X-Company-Id injection from ApiClient. Rename CompanyRuntime UI/model paths and visible copy to WorkspaceRuntime. Update chat/session model serialization to eliminate company_id. Do not alter private Identity Platform mapping source or platform audit storage in this task.

- [ ] **Step 4: Make workspace isolation a normal quality gate**

Add:

~~~make
tenancy-check:
	cd services/company && encore test
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/agent_core tests/apps/cosa/test_tenant_isolation.py -q
	cd frontend && flutter test test/auth_flow_test.dart test/modules/chat/session_view_test.dart
~~~

Call it from verify and add equivalent explicit CI steps. Update docs/features/skills.md to state that source skillpacks are reference-only until the workspace-only runtime gates have passed.

- [ ] **Step 5: Run the complete release gate**

Run:

~~~bash
make tenancy-check
make boundary-check
make services-test
make agent-core-test
make apps-cosa-test
make frontend-test
make frontend-analyze
rg -n 'X-Company-Id|company_id|companyId' frontend/lib apps/cosa packages/agent_core
~~~

Expected: all required checks pass, and the final scan returns no product-side occurrences. Occurrences under Identity's explicitly private Platform integration and historical immutable migrations are reviewed and documented, not deleted.

- [ ] **Step 6: Commit**

~~~bash
git add frontend Makefile .github/workflows/quality.yml docs/features/skills.md
git commit -m "test: enforce workspace-only product tenancy"
~~~

## Final acceptance checklist

- [ ] Product callers select and send only a Workspace; company identifiers cannot be observed in browser storage, public JSON or public headers.
- [ ] Every Project belongs to exactly one Workspace; Project and Portfolio reads/writes are membership-gated and SQL-scoped.
- [ ] A Task and an OKR Objective may have zero, one or many same-Workspace Project links; cross-Workspace links are rejected in service and database.
- [ ] Finance/accounting, CRM, people, knowledge, Task, OKR, 12-week plan, conversation, run, memory and artifact remain valid Workspace-wide without a Project link.
- [ ] Agent Core, COSA, connector/schedule/policy product data have workspace_id as the only tenant key.
- [ ] Platform company mapping remains only behind Identity's private synchronization/integration boundary.
- [ ] All commands in Task 8 pass before enabling write-capable agent skills.
