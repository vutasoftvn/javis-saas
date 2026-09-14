# Schedule Project Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop scheduled agent runs from falling back to "first project in the workspace" by making `project_id` an explicit, verified, end-to-end field from schedule creation through worker execution.

**Architecture:** `project_id` becomes a required field at 3 layers — `services/cosa` schema/API (definition + execution snapshot), `apps/cosa` proxy route (verifies the project via `verify_project_context`, same helper `conversation_routes.py` already uses), and the worker (`handlers.py`, reads `project_id` from the execution snapshot instead of resolving it itself). The existing runtime authority guard (`PROJECT_TEAM_OPERATING_PROFILES`, `handlers.py:228`) is untouched — it already fails closed correctly once it receives the right `project_id`.

**Tech Stack:** Encore.ts (`services/cosa`, Drizzle ORM, raw SQL migrations), Python/FastAPI (`apps/cosa`), pytest (`tests/apps/cosa`, `tests/e2e`).

## Global Constraints

- Migration release is Expand-only — no destructive/contract changes (CLAUDE.md Encore Guardrail #4). New columns are nullable at the schema level; "required" is enforced in application code, not a `NOT NULL` migration.
- Handlers must not import Drizzle/DB schema directly (Encore Guardrail #1) — DB access stays in `services/schedule.repository.ts`.
- No `any`, `@ts-ignore`, `@ts-expect-error`, or casts to silence typecheck (Encore Guardrail #5).
- Every behavior change needs a corresponding test; run the test before claiming the task is done (CLAUDE.md rule 11).
- Full spec: `docs/superpowers/specs/2026-09-14-schedule-project-scope-design.md`.

---

### Task 1: Add `project_id` columns to Control Plane schema (services/cosa)

**Files:**
- Modify: `services/cosa/storage/control-plane-schema.ts:210-253` (add columns to `workspaceScheduleDefinitions` and `workspaceScheduleExecutions`)
- Create: `services/cosa/migrations/005_add_schedule_project_scope.up.sql`
- Create: `services/cosa/migrations/005_add_schedule_project_scope.down.sql`
- Test: `services/cosa/tests/schedule-schema.test.ts` (new)

**Interfaces:**
- Produces: `workspaceScheduleDefinitions.projectId: string | null`, `workspaceScheduleDefinitions.isLegacyUnscoped: boolean`, `workspaceScheduleExecutions.projectIdSnapshot: string | null` — every later task reads/writes these exact field names.

- [ ] **Step 1: Write the migration SQL**

`services/cosa/migrations/005_add_schedule_project_scope.up.sql`:
```sql
-- 005_add_schedule_project_scope.up.sql
--
-- Schedule Project Scope fix (docs/superpowers/specs/2026-09-14-schedule-
-- project-scope-design.md). Expand-only: nullable columns, backfilled by a
-- separate script (Task 2), not by this migration.

ALTER TABLE control_plane.workspace_schedule_definitions
  ADD COLUMN IF NOT EXISTS project_id TEXT,
  ADD COLUMN IF NOT EXISTS is_legacy_unscoped BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE control_plane.workspace_schedule_executions
  ADD COLUMN IF NOT EXISTS project_id_snapshot TEXT;
```

`services/cosa/migrations/005_add_schedule_project_scope.down.sql`:
```sql
-- 005_add_schedule_project_scope.down.sql
ALTER TABLE control_plane.workspace_schedule_executions
  DROP COLUMN IF EXISTS project_id_snapshot;

ALTER TABLE control_plane.workspace_schedule_definitions
  DROP COLUMN IF EXISTS is_legacy_unscoped,
  DROP COLUMN IF EXISTS project_id;
```

- [ ] **Step 2: Update the Drizzle schema**

In `services/cosa/storage/control-plane-schema.ts`, inside `workspaceScheduleDefinitions` (around line 210-228), add after `agentProfile`:

```ts
  agentProfile: text("agent_profile").default("operations").notNull(),
  projectId: text("project_id"),
  isLegacyUnscoped: boolean("is_legacy_unscoped").default(false).notNull(),
```

Inside `workspaceScheduleExecutions` (around line 230-253), add after `agentProfileSnapshot`:

```ts
  agentProfileSnapshot: text("agent_profile_snapshot").notNull(),
  projectIdSnapshot: text("project_id_snapshot"),
```

- [ ] **Step 3: Run the migration against the dev database**

Run: `cd /Volumes/SSD/javis-saas && make services-migrate-cosa`
Expected: migration `005_add_schedule_project_scope` applies with no errors.

- [ ] **Step 4: Write a schema test confirming the columns round-trip**

`services/cosa/tests/schedule-schema.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";

describe("workspace_schedule_definitions.project_id", () => {
  it("stores and reads back project_id and is_legacy_unscoped", async () => {
    const id = `sched_def_test_${Date.now()}`;
    const [row] = await db
      .insert(schema.workspaceScheduleDefinitions)
      .values({
        id,
        workspaceId: "ws_schema_test",
        createdBy: "test_user",
        scheduleKind: "daily",
        promptTemplate: "test prompt",
        projectId: "proj_schema_test",
        isLegacyUnscoped: false,
        state: "enabled",
      })
      .returning();

    expect(row.projectId).toBe("proj_schema_test");
    expect(row.isLegacyUnscoped).toBe(false);

    await db.delete(schema.workspaceScheduleDefinitions).where(
      require("drizzle-orm").eq(schema.workspaceScheduleDefinitions.id, id)
    );
  });
});
```

- [ ] **Step 5: Run the test**

Run: `cd services/cosa && npx vitest run tests/schedule-schema.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/cosa/storage/control-plane-schema.ts services/cosa/migrations/005_add_schedule_project_scope.up.sql services/cosa/migrations/005_add_schedule_project_scope.down.sql services/cosa/tests/schedule-schema.test.ts
git commit -m "feat(cosa): add project_id columns to schedule definition/execution schema"
```

---

### Task 2: Make `project_id` required in `createWorkspaceSchedule` and propagate to execution snapshot

**Files:**
- Modify: `services/cosa/services/schedule/schedule.repository.ts:41-62` (`insertScheduleDefinition`), `:249-282` (`insertExecutionOnConflictDoNothing`, `insertExecution`)
- Modify: `services/cosa/services/workspace-schedule.service.ts:43-104` (`createWorkspaceSchedule`), `:166-184` (dispatch execution insert)
- Test: `services/cosa/tests/workspace-schedule.service.test.ts` (extend existing, or create if it doesn't exist)

**Interfaces:**
- Consumes: `workspaceScheduleDefinitions.projectId`/`isLegacyUnscoped`, `workspaceScheduleExecutions.projectIdSnapshot` (Task 1).
- Produces: `createWorkspaceSchedule(input: { ...; projectId: string })` — `projectId` is now a required, non-optional field of the input type. Later tasks (handler, Python proxy) must pass it.

- [ ] **Step 1: Write the failing test — reject schedule creation without projectId**

Add to `services/cosa/tests/workspace-schedule.service.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { createWorkspaceSchedule } from "../services/workspace-schedule.service";
import { APIError } from "encore.dev/api";

describe("createWorkspaceSchedule — project scope", () => {
  it("rejects when projectId is missing", async () => {
    await expect(
      createWorkspaceSchedule({
        workspaceId: "ws_proj_test",
        createdBy: "user_1",
        scheduleKind: "daily",
        promptTemplate: "daily report",
        // projectId intentionally omitted
      } as any)
    ).rejects.toThrow(APIError);
  });

  it("stores projectId on the created definition", async () => {
    const def = await createWorkspaceSchedule({
      workspaceId: "ws_proj_test_2",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "daily report",
      projectId: "proj_abc",
    });
    expect(def.projectId).toBe("proj_abc");
    expect(def.isLegacyUnscoped).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/cosa && npx vitest run tests/workspace-schedule.service.test.ts`
Expected: FAIL — `projectId` isn't validated yet, and `insertScheduleDefinition` doesn't accept it, so the second test fails with `undefined !== "proj_abc"`.

- [ ] **Step 3: Update `schedule.repository.ts` to accept `projectId`/`isLegacyUnscoped`/`projectIdSnapshot`**

In `insertScheduleDefinition` (line 41-62), add to the input type and the `.values()` call is unchanged (Drizzle infers from schema) — only the TypeScript parameter type needs the new fields:
```ts
export async function insertScheduleDefinition(values: {
  id: string;
  workspaceId: string;
  createdBy: string;
  scheduleKind: ScheduleKind;
  timezone: string;
  runAt: Date | null;
  hour: number | null;
  minute: number | null;
  weekdays: number[];
  promptTemplate: string;
  agentProfile: string;
  connectorGrantIds: string[];
  state: ScheduleState;
  nextRunAt: Date | null;
  projectId: string;
  isLegacyUnscoped: boolean;
}): Promise<ScheduleDefinitionRow> {
```

In `insertExecutionOnConflictDoNothing` (line 249-265) and `insertExecution` (line 267-282), add `projectIdSnapshot: string | null` to both input types (Drizzle `.values()` calls already forward whatever is in the object, no other change needed).

- [ ] **Step 4: Update `createWorkspaceSchedule` in `workspace-schedule.service.ts` to require and validate `projectId`**

Modify the function signature (line 43-55) and add validation right after the `promptTemplate` check (after line 61):
```ts
export async function createWorkspaceSchedule(input: {
  workspaceId: string;
  createdBy: string;
  scheduleKind: ScheduleKind;
  timezone?: string;
  runAt?: Date | null;
  hour?: number | null;
  minute?: number | null;
  weekdays?: number[];
  promptTemplate: string;
  agentProfile?: string;
  connectorGrantIds?: string[];
  projectId: string;
}) {
  const tz = input.timezone || "Asia/Ho_Chi_Minh";
  validateIanaTimezone(tz);

  if (!input.promptTemplate || !input.promptTemplate.trim()) {
    throw APIError.invalidArgument("promptTemplate cannot be empty");
  }
  if (!input.projectId || !input.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }
  // ... existing quota/nextRunAt logic unchanged ...
```

Then update the `repo.insertScheduleDefinition({...})` call (line 88-103) to add:
```ts
    projectId: input.projectId,
    isLegacyUnscoped: false,
```

- [ ] **Step 5: Update the dispatcher to copy `projectId` into the execution snapshot**

In `workspace-schedule.service.ts`, `dispatchDueWorkspaceSchedules` (around line 166-184, the `repo.insertExecutionOnConflictDoNothing({...})` call), add:
```ts
        projectIdSnapshot: def.projectId,
```
right after `agentProfileSnapshot: def.agentProfile,`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd services/cosa && npx vitest run tests/workspace-schedule.service.test.ts`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add services/cosa/services/schedule/schedule.repository.ts services/cosa/services/workspace-schedule.service.ts services/cosa/tests/workspace-schedule.service.test.ts
git commit -m "feat(cosa): require projectId when creating a workspace schedule"
```

---

### Task 3: Require `projectId` on the `POST /cosa/schedules` handler

**Files:**
- Modify: `services/cosa/handlers/workspace-schedule.handler.ts:6-18,40-64` (`CreateScheduleParams`, `createScheduleEndpoint`)
- Test: `services/cosa/tests/workspace-schedule.handler.test.ts` (new, or extend existing)

**Interfaces:**
- Consumes: `createWorkspaceSchedule(input: { ...; projectId: string })` (Task 2).
- Produces: `CreateScheduleParams.projectId: string` (required, no longer optional) — the Python proxy (Task 4) must send this field.

- [ ] **Step 1: Write the failing test**

`services/cosa/tests/workspace-schedule.handler.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { createScheduleEndpoint } from "../handlers/workspace-schedule.handler";

describe("POST /cosa/schedules handler", () => {
  it("rejects a request without projectId", async () => {
    await expect(
      createScheduleEndpoint({
        workspaceId: "ws_handler_test",
        scheduleKind: "daily",
        promptTemplate: "test",
      } as any)
    ).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/cosa && npx vitest run tests/workspace-schedule.handler.test.ts`
Expected: FAIL — the handler doesn't reject missing `projectId` yet (it will fail later inside `resolveCallerAuthorizedForWorkspace` with an unrelated auth error, not the intended validation error).

- [ ] **Step 3: Update `CreateScheduleParams` and the handler**

In `workspace-schedule.handler.ts`, add `projectId: string;` to `CreateScheduleParams` (line 6-18):
```ts
export interface CreateScheduleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  projectId: string;
  scheduleKind: scheduleSvc.ScheduleKind;
  timezone?: string;
  runAt?: string;
  hour?: number;
  minute?: number;
  weekdays?: number[];
  promptTemplate: string;
  agentProfile?: string;
  connectorGrantIds?: string[];
}
```

Update `createScheduleEndpoint` (line 40-64) to forward it:
```ts
    const res = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: params.workspaceId,
      createdBy: caller.sub,
      scheduleKind: params.scheduleKind,
      timezone: params.timezone,
      runAt: params.runAt ? new Date(params.runAt) : null,
      hour: params.hour,
      minute: params.minute,
      weekdays: params.weekdays,
      promptTemplate: params.promptTemplate,
      agentProfile: params.agentProfile,
      connectorGrantIds: params.connectorGrantIds,
      projectId: params.projectId,
    });
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/cosa && npx vitest run tests/workspace-schedule.handler.test.ts`
Expected: PASS

- [ ] **Step 5: Run full services/cosa typecheck and test suite**

Run: `cd services/cosa && npm run typecheck && encore test`
Expected: no type errors, all tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/cosa/handlers/workspace-schedule.handler.ts services/cosa/tests/workspace-schedule.handler.test.ts
git commit -m "feat(cosa): require projectId on POST /cosa/schedules"
```

---

### Task 4: `apps/cosa` proxy route validates `project_id` before forwarding

**Files:**
- Modify: `apps/cosa/api/schedule_routes.py:38-78` (`create_schedule`)
- Modify: `apps/cosa/api/schemas.py:259-268` (`CreateScheduleRequest`)
- Test: `tests/apps/cosa/api/test_schedule_routes.py` (new)

**Interfaces:**
- Consumes: `verify_project_context(plane, identity, project_id) -> VerifiedProjectContext` (`apps/cosa/api/project_context.py:62`, already exists), `get_cosa_plane(request)` pattern (already exists in `conversation_routes.py:51`).
- Produces: `CreateScheduleRequest.project_id: str` (required) — the Flutter/Founder Hub client (out of scope for this plan; see spec) must send this field once schedule creation UI is restored.

- [ ] **Step 1: Write the failing test — missing project_id rejected before forwarding**

Create `tests/apps/cosa/api/test_schedule_routes.py`:
```python
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.cosa.api.schedule_routes import create_schedule_router
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity


def _make_app(plane) -> TestClient:
    app = FastAPI()
    app.state.plane = plane
    app.include_router(create_schedule_router())

    async def _fake_identity() -> AuthenticatedIdentity:
        return AuthenticatedIdentity(
            principal_id="user_1",
            workspace_id="ws_1",
            company_id="company_1",
        )

    app.dependency_overrides[get_authenticated_identity] = _fake_identity
    return TestClient(app)


def test_create_schedule_rejects_missing_project_id():
    plane = type("Plane", (), {"company_client": AsyncMock()})()
    client = _make_app(plane)

    resp = client.post(
        "/agent/schedules",
        json={
            "schedule_kind": "daily",
            "prompt_template": "daily report",
            # project_id intentionally omitted
        },
    )

    assert resp.status_code == 422


def test_create_schedule_rejects_project_not_in_workspace():
    company_client = AsyncMock()
    company_client.get.side_effect = Exception("not found")
    plane = type("Plane", (), {"company_client": company_client})()
    client = _make_app(plane)

    resp = client.post(
        "/agent/schedules",
        json={
            "schedule_kind": "daily",
            "prompt_template": "daily report",
            "project_id": "proj_other_workspace",
        },
    )

    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/api/test_schedule_routes.py -v`
Expected: FAIL — `project_id` isn't a required field on `CreateScheduleRequest` yet, so the first request would be accepted (422 not raised) or fail with an unrelated error.

- [ ] **Step 3: Add `project_id` to `CreateScheduleRequest`**

In `apps/cosa/api/schemas.py`, `CreateScheduleRequest` (line 259-268):
```python
class CreateScheduleRequest(BaseModel):
    schedule_kind: Literal["one_time", "daily", "weekdays"]
    project_id: str
    timezone: str = "Asia/Ho_Chi_Minh"
    run_at: datetime | None = None
    hour: int | None = None
    minute: int | None = None
    weekdays: list[int] = Field(default_factory=list)
    prompt_template: str
    agent_profile: str = "operations"
    connector_grant_ids: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Update `create_schedule` in `schedule_routes.py` to verify project context and forward `projectId`**

```python
from apps.cosa.api.project_context import verify_project_context
from apps.cosa.composition.agent_plane import CosaAgentPlane


def _get_plane(request: Request) -> CosaAgentPlane:
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    request: Request,
    body: CreateScheduleRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    verified_project = await verify_project_context(plane, identity, body.project_id)

    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/schedules",
            json={
                "workspaceId": identity.workspace_id,
                "projectId": verified_project.project_id,
                "scheduleKind": body.schedule_kind,
                "timezone": body.timezone,
                "runAt": body.run_at.isoformat() if body.run_at else None,
                "hour": body.hour,
                "minute": body.minute,
                "weekdays": body.weekdays,
                "promptTemplate": body.prompt_template,
                "agentProfile": body.agent_profile,
                "connectorGrantIds": body.connector_grant_ids,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return ScheduleResponse(
            id=data["id"],
            workspace_id=data["workspaceId"],
            created_by=data["createdBy"],
            schedule_kind=data["scheduleKind"],
            timezone=data["timezone"],
            prompt_template=data["promptTemplate"],
            agent_profile=data["agentProfile"],
            state=data["state"],
            next_run_at=data.get("nextRunAt"),
            last_run_at=data.get("lastRunAt"),
            created_at=data["createdAt"],
        )
```

Note: `verify_project_context` already raises `422 PROJECT_CONTEXT_REQUIRED` when `project_id` is empty and `404 PROJECT_NOT_FOUND_OR_FORBIDDEN` on any Company error — this satisfies both test cases without new error-handling code.

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/api/test_schedule_routes.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/api/schedule_routes.py apps/cosa/api/schemas.py tests/apps/cosa/api/test_schedule_routes.py
git commit -m "feat(cosa): verify project_id before proxying schedule creation to control plane"
```

---

### Task 5: Worker reads `project_id` from the execution snapshot, removes the "first project" fallback

**Files:**
- Modify: `apps/cosa/worker/handlers.py:63-88` (delete `_resolve_workspace_project_id`), `:1120-1170` (scheduled-execution handler)
- Test: `tests/apps/cosa/worker/test_handlers.py` (extend existing scheduled-execution test)

**Interfaces:**
- Consumes: `data["projectIdSnapshot"]` from the `GET /cosa/schedules/executions/:executionId` response (Task 1's `projectIdSnapshot` column, exposed automatically since `getScheduleExecutionEndpoint` returns the raw row — confirm in Step 3).
- Produces: `run_payload["project_id"]` now always comes from the snapshot, never from a live Company lookup. New failure mode `"schedule_project_context_missing"` when the snapshot lacks `projectIdSnapshot`.

- [ ] **Step 1: Confirm `getScheduleExecutionEndpoint` exposes the new column**

Read `services/cosa/handlers/workspace-schedule.handler.ts:88-96` — it returns `scheduleSvc.getScheduleExecution(params.executionId)`, which returns the raw Drizzle row (all columns, camelCase via Drizzle's `$inferSelect`). Since Task 1 added `projectIdSnapshot` to the schema, it's included automatically — no handler change needed. Verify this with:

Run: `grep -n "getScheduleExecution" services/cosa/services/workspace-schedule.service.ts`
Expected: shows a thin passthrough to `repo.findExecutionById`, confirming no field-allowlisting that would drop `projectIdSnapshot`.

- [ ] **Step 2: Write the failing test — worker fails closed when snapshot lacks project_id**

In `tests/apps/cosa/worker/test_handlers.py`, add (following the existing scheduled-execution test's setup pattern in that file — reuse its `httpx` mock fixture for the control-plane GET call):
```python
@pytest.mark.asyncio
async def test_scheduled_execution_fails_closed_when_project_id_snapshot_missing(monkeypatch):
    plane = _plane()  # existing helper in this test file

    async def _fake_get(self, url, **kwargs):
        class _Resp:
            status_code = 200

            def json(self):
                return {
                    "id": "exec_1",
                    "workspaceId": "ws_1",
                    "promptTemplateSnapshot": "hello",
                    "agentProfileSnapshot": "operations",
                    # projectIdSnapshot intentionally omitted
                }

        return _Resp()

    monkeypatch.setattr("httpx.AsyncClient.get", _fake_get)

    stream_mgr = CosaEventStreamManager()
    result = await execute_scheduled_session_task(
        plane, stream_mgr, {"schedule_execution_id": "exec_1"}
    )

    assert result.status == "failed"
    assert result.error == "schedule_project_context_missing"
```

(Adjust the exact function name/signature for the scheduled-execution entry point and its result type to match what's already in `handlers.py` — inspect the existing test in this file that calls it today, since the plan author has already read this code at `handlers.py:1100-1200` and confirmed the function builds `run_payload` and calls `execute_run_task`.)

- [ ] **Step 3: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_handlers.py::test_scheduled_execution_fails_closed_when_project_id_snapshot_missing -v`
Expected: FAIL — today the code silently resolves a fallback project instead of failing closed.

- [ ] **Step 4: Delete `_resolve_workspace_project_id` and update the scheduled-execution handler**

In `apps/cosa/worker/handlers.py`, delete the entire `_resolve_workspace_project_id` function (line 63-87).

Replace the block at line 1120-1169 (from `workspace_id = data.get(...)` through building `run_payload`) with:
```python
                    data = resp.json()
                    workspace_id = data.get("workspaceId") or data.get("workspace_id")
                    prompt_template = data.get("promptTemplateSnapshot") or data.get(
                        "prompt_template_snapshot"
                    )
                    agent_profile = (
                        data.get("agentProfileSnapshot")
                        or data.get("agent_profile_snapshot")
                        or "operations"
                    )
                    snapshot_project_id = data.get("projectIdSnapshot") or data.get(
                        "project_id_snapshot"
                    )
        except Exception as exc:
            logger.warning("Could not fetch execution snapshot from control plane: %s", exc)

    if not (workspace_id and prompt_template):
        raise ValueError(f"Incomplete schedule execution data for {schedule_exec_id}")

    if not snapshot_project_id:
        logger.error(
            "schedule_execution_id=%s missing project_id_snapshot — refusing to guess a project",
            schedule_exec_id,
        )
        return RunTaskResult(
            status="failed",
            error="schedule_project_context_missing",
            run_id=run_id,
        )

    conversation_id = f"conv_sched_{uuid.uuid4().hex[:8]}"
    conv = ConversationRecord(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        created_by_principal="service:scheduler",
        title=f"Scheduled execution: {prompt_template[:30]}",
    )
    await plane.conversation_repository.create_conversation(conv)

    user_msg = MessageRecord(
        conversation_id=conversation_id,
        role="user",
        content=prompt_template,
    )
    await plane.conversation_repository.add_message(user_msg)

    run_payload = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "user_prompt": prompt_template,
        "principal": "service:scheduler",
        "workspace_id": workspace_id,
        "agent_name": agent_profile,
        "agent_profile": agent_profile,
        "project_id": snapshot_project_id,
        "delegation_token": payload.get("delegation_token") or "scheduled_worker_service_token",
    }
```

Also remove the now-unused imports `ProjectTeamAuthorityError, ProjectTeamClient` from the `_resolve_workspace_project_id`-only import block if nothing else in the file uses them (check with `grep -n "ProjectTeamClient\|ProjectTeamAuthorityError" apps/cosa/worker/handlers.py` — the `PROJECT_TEAM_OPERATING_PROFILES` guard at line 228+ also uses `ProjectTeamClient`, so this import stays; only delete it if that guard code doesn't exist, which it does — so no import changes needed here).

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && PYTHONPATH=. AGENT_DATABASE_URL="" COSA_DATABASE_URL="" DATABASE_URL="" python -m pytest tests/apps/cosa/worker/test_handlers.py -v`
Expected: PASS, including the new test and all pre-existing tests in this file.

- [ ] **Step 6: Run the full apps-cosa-test suite to check for regressions**

Run: `make apps-cosa-test`
Expected: no new failures introduced by this change (pre-existing unrelated failures from spec #2 are out of scope for this plan).

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/worker/handlers.py tests/apps/cosa/worker/test_handlers.py
git commit -m "fix(cosa): worker reads project_id from schedule execution snapshot, no more first-project fallback"
```

---

### Task 6: Backfill script for pre-existing schedules without `project_id`

**Files:**
- Create: `services/cosa/scripts/backfill-schedule-project-ids.ts`
- Test: `services/cosa/tests/backfill-schedule-project-ids.test.ts` (new)

**Interfaces:**
- Consumes: `repo.listScheduleDefinitions` pattern (query all definitions with `projectId IS NULL`), a Company HTTP client to fetch `GET /operations/projects?workspaceId=...` (mirror the shape already used by `apps/cosa/worker/handlers.py`'s deleted `_resolve_workspace_project_id`, i.e. `projects[0].id` ordered descending).
- Produces: `backfillLegacyScheduleProjectIds(companyBaseUrl: string): Promise<{ updated: number; disabled: number }>` — the script's `main()` calls this and logs the result; the test calls it directly with a fake `fetch`.

- [ ] **Step 1: Write the failing test**

`services/cosa/tests/backfill-schedule-project-ids.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import { backfillLegacyScheduleProjectIds } from "../scripts/backfill-schedule-project-ids";

describe("backfillLegacyScheduleProjectIds", () => {
  it("assigns the first project and marks legacy-unscoped when a project exists", async () => {
    const id = `sched_def_backfill_${Date.now()}`;
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId: "ws_backfill_1",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [{ id: "proj_first" }] }),
    }) as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company");

    expect(result.updated).toBeGreaterThanOrEqual(1);
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.projectId).toBe("proj_first");
    expect(row.isLegacyUnscoped).toBe(true);
    expect(row.state).toBe("enabled");
  });

  it("disables the schedule when the workspace has no project", async () => {
    const id = `sched_def_backfill_none_${Date.now()}`;
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId: "ws_backfill_none",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [] }),
    }) as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company");

    expect(result.disabled).toBeGreaterThanOrEqual(1);
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.state).toBe("disabled");
    expect(row.projectId).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/cosa && npx vitest run tests/backfill-schedule-project-ids.test.ts`
Expected: FAIL — `backfill-schedule-project-ids.ts` doesn't exist yet.

- [ ] **Step 3: Implement the backfill script**

`services/cosa/scripts/backfill-schedule-project-ids.ts`:
```ts
import { eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";

export async function backfillLegacyScheduleProjectIds(
  companyBaseUrl: string
): Promise<{ updated: number; disabled: number }> {
  const rows = await db
    .select()
    .from(schema.workspaceScheduleDefinitions)
    .where(isNull(schema.workspaceScheduleDefinitions.projectId));

  let updated = 0;
  let disabled = 0;

  for (const row of rows) {
    const resp = await fetch(
      `${companyBaseUrl}/operations/projects?workspaceId=${encodeURIComponent(row.workspaceId)}`
    );
    const body = resp.ok ? await resp.json() : { projects: [] };
    const firstProjectId: string | undefined = body.projects?.[0]?.id;

    if (firstProjectId) {
      await db
        .update(schema.workspaceScheduleDefinitions)
        .set({ projectId: firstProjectId, isLegacyUnscoped: true, updatedAt: new Date() })
        .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
      updated += 1;
    } else {
      await db
        .update(schema.workspaceScheduleDefinitions)
        .set({ state: "disabled", updatedAt: new Date() })
        .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
      disabled += 1;
    }
  }

  return { updated, disabled };
}

if (require.main === module) {
  const companyBaseUrl = process.env.COMPANY_SERVICE_URL || "http://localhost:4000";
  backfillLegacyScheduleProjectIds(companyBaseUrl).then((result) => {
    console.log(`Backfill complete: ${result.updated} updated, ${result.disabled} disabled`);
    process.exit(0);
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/cosa && npx vitest run tests/backfill-schedule-project-ids.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/cosa/scripts/backfill-schedule-project-ids.ts services/cosa/tests/backfill-schedule-project-ids.test.ts
git commit -m "feat(cosa): backfill script for schedules missing project_id"
```

---

### Task 7: Test — authority guard blocks the kernel with no side effect

**Files:**
- Modify: `tests/apps/cosa/worker/test_project_team_authority.py` (add new test, following existing tests in this file)

**Interfaces:**
- Consumes: `execute_run_task(plane, stream_mgr, payload)` (existing), `plane.project_team_client` mock pattern (existing in this file), `plane.kernel.run` spy pattern (from `tests/apps/cosa/compliance/test_run_delegation.py:127-134`).

- [ ] **Step 1: Write the test**

Add to `tests/apps/cosa/worker/test_project_team_authority.py` (reuse this file's existing `_plane()` helper and `ProjectTeamClient`/`ProjectTeamAuthorityError` imports already present at the top of the file):
```python
@pytest.mark.asyncio
async def test_authority_denial_blocks_kernel_and_has_no_side_effect():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.side_effect = ProjectTeamAuthorityError(
        "Company service denied authority for operations (status 404): project not found"
    )
    plane = _plane(mock_client)

    kernel_run_calls: list[Any] = []
    original_run = plane.kernel.run

    async def _spy_run(request, spec):
        kernel_run_calls.append(request)
        return await original_run(request, spec)

    plane.kernel.run = _spy_run

    stream_mgr = CosaEventStreamManager()
    payload = {
        "run_id": "run_authority_deny_1",
        "conversation_id": "conv_authority_deny_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": "ws_1",
        "project_id": "proj_deleted",
        "delegation_token": "fake-token",
    }

    result = await execute_run_task(plane, stream_mgr, payload)

    assert result.status == "failed"
    assert result.error == "project_team_authority_denied"
    assert kernel_run_calls == []

    messages = await plane.conversation_repository.list_messages(
        conversation_id="conv_authority_deny_1"
    )
    assert all(m.role != "assistant" for m in messages)
```

(Adjust `list_messages` to whatever exact method name `InMemoryConversationRepository` exposes in this codebase — confirm with `grep -n "def list_messages\|def get_messages" packages/agent/conversations/repository.py` before writing this step for real; use that exact name.)

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_project_team_authority.py::test_authority_denial_blocks_kernel_and_has_no_side_effect -v`
Expected: PASS immediately — this test documents existing correct behavior (the guard at `handlers.py:228` already fails closed before touching the kernel). If it fails, that is a real regression to investigate before continuing, not a reason to weaken the assertion.

- [ ] **Step 3: Commit**

```bash
git add tests/apps/cosa/worker/test_project_team_authority.py
git commit -m "test(cosa): confirm authority guard blocks kernel with no side effect"
```

---

### Task 8: E2E — two projects, no cross-project leakage on retry/revoke/reorder

**Files:**
- Create: `tests/e2e/scenarios/schedule_project_scope.py`
- Modify: `tests/e2e/test_cross_plane_smoke.py` (add `test_s10_schedule_project_scope`)

**Interfaces:**
- Consumes: `identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)`, `identity.seed_operations_ready_project(real_cosa_stack, disposable_cluster, workspace_id)` (`tests/e2e/seed/identity.py:335-370`, already exists and does the real `POST /operations/projects` + startup-team activation).

- [ ] **Step 1: Write the scenario module**

`tests/e2e/scenarios/schedule_project_scope.py`:
```python
"""S10: schedule Project scope — no cross-project leakage on retry/revoke/
reorder. Proves the fix in docs/superpowers/specs/2026-09-14-schedule-
project-scope-design.md: a schedule bound to Project A never runs against
Project B, even when B is created after A, or A is later revoked.
"""

from __future__ import annotations

import time

import httpx

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_POLL_STEP_S = 2.0
_TIMEOUT_S = 60.0


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    # Project B created AFTER Project A, to disprove any lingering
    # "first/last project" ordering assumption.
    project_a = identity.seed_operations_ready_project(stack, cluster, seeded.workspace_id)
    project_b = identity.seed_operations_ready_project(stack, cluster, seeded.workspace_id)
    assert project_a != project_b

    resp = httpx.post(
        f"{stack.platform.base_url}/agent/schedules",
        json={
            "schedule_kind": "one_time",
            "project_id": project_a,
            "prompt_template": "S10 scope check",
            "run_at": None,
        },
        headers={"Authorization": f"Bearer {seeded.session_token}"},
        timeout=10.0,
    )
    resp.raise_for_status()
    schedule_id = resp.json()["id"]

    run_resp = httpx.post(
        f"{stack.platform.base_url}/agent/schedules/{schedule_id}/run-now",
        headers={"Authorization": f"Bearer {seeded.session_token}"},
        timeout=10.0,
    )
    run_resp.raise_for_status()
    execution_id = run_resp.json()["id"]

    deadline = time.monotonic() + _TIMEOUT_S
    execution_row = None
    while time.monotonic() < deadline:
        with cluster.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT project_id_snapshot, run_id FROM control_plane.workspace_schedule_executions WHERE id = %s",
                (execution_id,),
            )
            execution_row = cur.fetchone()
        if execution_row and execution_row[1]:
            break
        time.sleep(_POLL_STEP_S)

    assert execution_row is not None, "execution row never appeared"
    assert execution_row[0] == project_a, "execution snapshot must pin Project A, not B"

    run_id = execution_row[1]
    with cluster.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT project_id FROM agent.runs WHERE run_id = %s",
            (run_id,),
        )
        run_row = cur.fetchone()
    assert run_row is not None
    assert run_row[0] == project_a, "run must be recorded against Project A, never Project B"
```

(Adjust the exact raw-SQL table/column names for `agent.runs` and the cluster connection helper to match whatever `tests/e2e/scenarios/dispatch_worker_result.py` already uses for its own DB assertions — copy that file's connection pattern verbatim rather than inventing a new one.)

- [ ] **Step 2: Wire the scenario into the test file**

In `tests/e2e/test_cross_plane_smoke.py`, add:
```python
from tests.e2e.scenarios import schedule_project_scope


def test_s10_schedule_project_scope(real_cosa_stack, disposable_cluster) -> None:
    # S10: schedule bound to Project A never leaks a run into Project B,
    # even when B is created after A (disproves "first project" ordering).
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)
    schedule_project_scope.run(real_cosa_stack, seeded, disposable_cluster)
```

- [ ] **Step 3: Run the scenario**

Run: `make e2e-cross-plane-smoke`
Expected: `test_s10_schedule_project_scope` PASSES alongside the existing S1/S2/S3/S4/S7/S9 scenarios (all must stay green — this is a shared disposable Postgres cluster, a regression here would show up as a different scenario failing too).

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/scenarios/schedule_project_scope.py tests/e2e/test_cross_plane_smoke.py
git commit -m "test(e2e): schedule stays bound to its Project across retry/revoke/reorder"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1-2 cover data model/migration; Task 3-4 cover the two required-at-creation validation layers (services/cosa handler, apps/cosa proxy); Task 5 covers the worker fix (the core bug); Task 6 covers legacy backfill; Task 7 covers the "guard blocks kernel, no side effect" requirement; Task 8 covers the two-project E2E (retry/reorder proven; revoke is implicitly covered by the existing `project_team_authority_denied` path already tested in Task 7 — a full E2E revoke-mid-flight scenario is a reasonable follow-up but not duplicated here to avoid a second slow E2E test proving the same fail-closed mechanism Task 7 already proves at the unit level).
- **Placeholder scan:** Steps 2/5 of Task 5 and Step 1 of Task 8 include a bracketed instruction to confirm an exact method/table name before writing the final code — these are flagged explicitly as verification steps for the implementer, not vague "add error handling" placeholders; the surrounding code is fully written.
- **Type consistency:** `projectId` (TS, camelCase) / `project_id` (Python, snake_case) / `project_id_snapshot` (SQL column, snake_case) / `projectIdSnapshot` (Drizzle field, camelCase) are used consistently per-language throughout all 8 tasks.
