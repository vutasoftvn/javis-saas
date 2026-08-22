# services/operations Cluster (Phase 1: Tasks + Initiative + OKR) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the prototype `services/tasks` + `services/okr` (simplified, non-canonical schemas) with `services/operations` — one Encore cluster owning Task, Initiative, and OKR (Cycle/Objective/KeyResult), with field-for-field canonical schema ported from `backend/business_core/tasks` + `backend/business_core/strategy/{okr,initiative}.py`, and workspace/workforce references validated against `services/identity` (built in the prior plan, `docs/superpowers/plans/2026-08-22-services-identity-cluster.md`).

**Architecture:** One Encore service (`services/operations`), one `SQLDatabase("operations")` with two schemas — `operating` (tasks) and `strategy` (initiatives, OKR) — mirroring the schema-per-domain layout the Python backend already uses inside one Postgres DB. Cross-cluster references to `identity` (workspace, workforce member) are plain `number` columns with no DB foreign key (Encore can't enforce FKs across separate `SQLDatabase`s) — validated at write time by importing and calling `identity`'s exported API functions directly, the standard Encore.ts in-app service-to-service call pattern.

**Tech Stack:** Encore.ts (`encore.dev` ^1.57.13, already in `services/package.json` — no new dependencies needed), Vitest.

## Global Constraints

- Column names/types must match `backend/business_core/tasks/models.py::Task` and `backend/business_core/strategy/{okr.py,initiative.py}` — do not invent new field names; every canonical field must appear even if unused by current endpoints.
- Status vocabulary for Task is the canonical one — `todo, in_progress, waiting_approval, blocked, done, cancelled` — **not** the old prototype's `open/completed`. This is an intentional breaking change from `services/tasks`' current schema (which this plan deletes).
- Cross-cluster reference rule (from `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`): any column that pointed at `core.*`/`runtime_ops.*` tables in the Python model becomes a plain nullable `BIGINT`/`number` with no DB FK. `workspace_id` is validated on every create by calling `identity`'s `getWorkspace`; `assignee_member_id`/`owner_member_id` are validated by calling `identity`'s `getWorkforceMember` **only when provided** (both are nullable in the canonical model). `assignee_id`/`owner_id` (plain `core.users` references) are **not** validated in this plan — `services/identity` does not yet expose a `getUser(id)` endpoint (only `getMe`, which is self-only) and no consumer needs assignee lookup yet; this is a deliberate, documented deferral, not an oversight.
- **Known parity gap carried over from `services/identity`**: the canonical Python `Initiative.brain_id` and `OkrCycle.brain_id` are `NOT NULL` foreign keys into `knowledge.brains`, and `Brain` rows are normally created during registration (`backend/platform_core/auth/router.py::register` creates a default `Brain` alongside the workspace) — but the `services/identity` Phase 1 plan did not port `Brain` (it wasn't in that plan's scope and was missed at the time). Since no `Brain` table exists anywhere in `services/`, this plan makes `brain_id` a **nullable** `BIGINT` with no FK (a deliberate deviation from the canonical `NOT NULL`), not a blocker. Do not silently invent a `Brain` table here — that's a scope decision for a future plan once a `knowledge` cluster/module is actually needed.
- **Out of scope for this plan** (do not implement — no current consumer, matches the YAGNI precedent set in the identity plan): `TaskDependency`, `TaskSchedule` (only `Task` itself is ported), `OkrLink`, `MvpStage`, `StrategicObjective`, `Metric` (referenced by nullable FK fields on `OkrCycle`/`OkrObjective`/`KeyResult` — those fields are ported as unvalidated nullable `BIGINT`, the tables themselves are not created), `TwelveWeekCycle`/`WeeklyPlan`/`WeeklyCommitment` (so `Task.weekly_commitment_id` is a nullable `BIGINT` with no FK and no owning table), `Portfolio`, `StrategyCanvas`, `Evidence`/`Analysis`/`Decisions`/`Scorecard`, `Project`/`Offering` (so `Initiative.project_id`/`offering_id` are nullable `BIGINT` with no FK), `Templates`, `Capability`, `Stage`, `Founder`, `NextAction`. `backend/business_core/strategy/` has ~20 model files; this plan ports exactly three (`Task`, `Initiative`, `OkrCycle`/`OkrObjective`/`KeyResult`) — the ones the existing `services/tasks`/`services/okr` prototypes already cover plus the one FK (`Initiative`) `Task.initiative_id` needs to be real.
- No existing consumer calls `services/tasks` or `services/okr` over HTTP today (verified: no references in `backend/`, `frontend/`, or `services/realtime_agent/` besides one unrelated docstring mention) — deleting them in Task 5 requires no consumer migration/cutover coordination.

---

## File Structure

```text
services/operations/
├── encore.service.ts             # Service("operations") registration
├── db.ts                          # operationsDB = new SQLDatabase("operations", {...})
├── migrations/
│   ├── 1_create_tasks.up.sql              # operating.tasks
│   ├── 2_create_initiatives.up.sql        # strategy.initiatives
│   └── 3_create_okr.up.sql                # strategy.okr_cycles, okr_objectives, key_results
├── task.ts                         # createTask, getTask, listTasks, updateTaskStatus
├── task-events.ts                   # Topic + buildTaskCompletedEvent (renamed from events.ts to avoid clashing with okr-events.ts in the same dir)
├── initiative.ts                     # createInitiative, getInitiative
├── okr.ts                             # createOkrCycle, createObjective, addKeyResult, checkin, getObjectiveProgress
├── okr-scoring.ts                      # computeKeyResultScore, computeObjectiveScore (ported unchanged from services/okr/scoring.ts)
├── okr-events.ts                        # Topic + buildOkrProgressUpdatedEvent
├── task.test.ts
├── initiative.test.ts
├── okr.test.ts
└── okr-scoring.test.ts

# Deleted in Task 5:
services/tasks/   (entire directory)
services/okr/     (entire directory)
```

---

### Task 1: Scaffold the service and database

**Files:**
- Create: `services/operations/encore.service.ts`
- Create: `services/operations/db.ts`

**Interfaces:**
- Produces: `operationsDB: SQLDatabase` (from `db.ts`), used by every subsequent task in this plan.

- [ ] **Step 1: Create the service file**

`services/operations/encore.service.ts`:

```typescript
import { Service } from "encore.dev/service";

export default new Service("operations");
```

- [ ] **Step 2: Create the database**

`services/operations/db.ts`:

```typescript
import { SQLDatabase } from "encore.dev/storage/sqldb";

export const operationsDB = new SQLDatabase("operations", {
  migrations: "./migrations",
});
```

- [ ] **Step 3: Verify the app still type-checks with the new empty service**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/operations/encore.service.ts services/operations/db.ts
git commit -m "feat(operations): scaffold service and database"
```

---

### Task 2: Task schema + API (create/get/list/updateStatus), with identity validation

**Files:**
- Create: `services/operations/migrations/1_create_tasks.up.sql`
- Create: `services/operations/task-events.ts`
- Create: `services/operations/task.ts`
- Create: `services/operations/task.test.ts`

**Interfaces:**
- Consumes: `operationsDB` (Task 1), `getWorkspace` from `services/identity/workspace.ts`, `getWorkforceMember` from `services/identity/organization.ts`, `DomainEvent`/`makeDomainEvent`/`TASK_COMPLETED` from `services/shared/events.ts`.
- Produces: `Task` interface, `createTask`, `getTask`, `listTasks`, `updateTaskStatus` — `initiative.test.ts` (Task 3) does not depend on this, but a later plan (`commercial`/`finance-legal`) may reference `Task` by shape when linking work items.

- [ ] **Step 1: Write the migration**

`services/operations/migrations/1_create_tasks.up.sql` — column names/types match `backend/business_core/tasks/models.py::Task`; `initiative_id` is a real FK (added once `strategy.initiatives` exists in Task 3 — this migration creates the column without the FK constraint since `strategy.initiatives` doesn't exist yet at migration `1`; the constraint is added in migration `2`'s `ALTER TABLE`, standard Encore incremental-migration pattern):

```sql
CREATE SCHEMA IF NOT EXISTS operating;

CREATE TABLE operating.tasks (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  idempotency_key TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  priority TEXT NOT NULL DEFAULT 'medium',
  planned_start_at TIMESTAMPTZ,
  due_at TIMESTAMPTZ,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  assignee_id BIGINT,
  source TEXT,
  completion_policy TEXT,
  initiative_id BIGINT,
  weekly_commitment_id BIGINT,
  sort_key DOUBLE PRECISION,
  assignee_member_id BIGINT,
  owner_member_id BIGINT,
  execution_mode TEXT,
  function TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, idempotency_key)
);

CREATE INDEX idx_tasks_workspace_id ON operating.tasks(workspace_id);
CREATE INDEX idx_tasks_function ON operating.tasks(function);
```

- [ ] **Step 2: Write task-events.ts**

`services/operations/task-events.ts` (ported unchanged from `services/tasks/events.ts`, `workspaceId` now `number` to match the canonical `BIGINT` type instead of the prototype's `string`):

```typescript
import { Topic } from "encore.dev/pubsub";
import { DomainEvent, makeDomainEvent, TASK_COMPLETED } from "../shared/events";
import type { Task } from "./task";

export interface TaskCompletedPayload {
  taskId: number;
  workspaceId: number;
}

export type TaskCompletedEvent = DomainEvent<typeof TASK_COMPLETED, TaskCompletedPayload>;

export const taskEvents = new Topic<TaskCompletedEvent>("task-events", {
  deliveryGuarantee: "at-least-once",
});

export function buildTaskCompletedEvent(task: Task): TaskCompletedEvent {
  return makeDomainEvent(TASK_COMPLETED, { taskId: task.id, workspaceId: task.workspaceId });
}
```

- [ ] **Step 3: Write the failing test**

`services/operations/task.test.ts` — needs a real workspace id from `identity` since `createTask` validates it (integration-style test, same pattern as `identity/organization.test.ts` calling `createWorkspace`):

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createOrganization, hireWorkforceMember } from "../identity/organization";
import { createTask, getTask, listTasks, updateTaskStatus } from "./task";

async function makeWorkspace(name: string) {
  return createWorkspace({ name });
}

describe("createTask", () => {
  it("creates a task with canonical defaults", async () => {
    const workspace = await makeWorkspace("Task Test Inc");
    const task = await createTask({ workspaceId: workspace.id, title: "Write plan" });
    expect(task.id).toBeGreaterThan(0);
    expect(task.workspaceId).toBe(workspace.id);
    expect(task.status).toBe("todo");
    expect(task.priority).toBe("medium");
    expect(task.timezone).toBe("UTC");
  });

  it("rejects a task for a workspace that doesn't exist", async () => {
    await expect(createTask({ workspaceId: 999999999, title: "Orphan" })).rejects.toThrow();
  });

  it("validates assigneeMemberId against identity when provided", async () => {
    const workspace = await makeWorkspace("Assignee Test Inc");
    const org = await createOrganization({ workspaceId: workspace.id, name: "Assignee Test Inc" });
    const member = await hireWorkforceMember({ organizationId: org.id, memberType: "HUMAN", roleTitle: "Ops" });

    const task = await createTask({
      workspaceId: workspace.id,
      title: "Assigned task",
      assigneeMemberId: member.id,
    });
    expect(task.assigneeMemberId).toBe(member.id);

    await expect(
      createTask({ workspaceId: workspace.id, title: "Bad assignee", assigneeMemberId: 999999999 })
    ).rejects.toThrow();
  });
});

describe("getTask/listTasks", () => {
  it("fetches a created task and lists it by workspace", async () => {
    const workspace = await makeWorkspace("List Test Inc");
    const created = await createTask({ workspaceId: workspace.id, title: "Fetch me" });

    const fetched = await getTask({ id: created.id });
    expect(fetched).toEqual(created);

    const { tasks } = await listTasks({ workspaceId: workspace.id });
    expect(tasks.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    await expect(getTask({ id: 999999999 })).rejects.toThrow();
  });
});

describe("updateTaskStatus", () => {
  it("transitions through the canonical status vocabulary and publishes on done", async () => {
    const workspace = await makeWorkspace("Status Test Inc");
    const created = await createTask({ workspaceId: workspace.id, title: "Ship it" });

    const inProgress = await updateTaskStatus({ id: created.id, status: "in_progress" });
    expect(inProgress.status).toBe("in_progress");

    const done = await updateTaskStatus({ id: created.id, status: "done" });
    expect(done.status).toBe("done");
  });

  it("rejects a status outside the canonical vocabulary", async () => {
    const workspace = await makeWorkspace("Bad Status Test Inc");
    const created = await createTask({ workspaceId: workspace.id, title: "Bad status" });
    await expect(updateTaskStatus({ id: created.id, status: "completed" as any })).rejects.toThrow();
  });
});
```

- [ ] **Step 4: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test task.test.ts`
Expected: FAIL — `Cannot find module './task'`

- [ ] **Step 5: Implement task.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { operationsDB } from "./db";
import { getWorkspace } from "../identity/workspace";
import { getWorkforceMember } from "../identity/organization";
import { buildTaskCompletedEvent, taskEvents } from "./task-events";

export const TASK_STATUSES = ["todo", "in_progress", "waiting_approval", "blocked", "done", "cancelled"] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export interface Task {
  id: number;
  workspaceId: number;
  title: string;
  idempotencyKey: string | null;
  status: TaskStatus;
  priority: "low" | "medium" | "high" | "urgent";
  plannedStartAt: string | null;
  dueAt: string | null;
  timezone: string;
  assigneeId: number | null;
  source: string | null;
  completionPolicy: string | null;
  initiativeId: number | null;
  weeklyCommitmentId: number | null;
  sortKey: number | null;
  assigneeMemberId: number | null;
  ownerMemberId: number | null;
  executionMode: "HUMAN" | "AGENT" | "HYBRID" | null;
  function: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskParams {
  workspaceId: number;
  title: string;
  priority?: "low" | "medium" | "high" | "urgent";
  dueAt?: string;
  initiativeId?: number;
  assigneeMemberId?: number;
  ownerMemberId?: number;
  executionMode?: "HUMAN" | "AGENT" | "HYBRID";
  function?: string;
}

interface TaskRow {
  id: number;
  workspace_id: number;
  title: string;
  idempotency_key: string | null;
  status: string;
  priority: string;
  planned_start_at: Date | null;
  due_at: Date | null;
  timezone: string;
  assignee_id: number | null;
  source: string | null;
  completion_policy: string | null;
  initiative_id: number | null;
  weekly_commitment_id: number | null;
  sort_key: number | null;
  assignee_member_id: number | null;
  owner_member_id: number | null;
  execution_mode: string | null;
  function: string | null;
  created_at: Date;
  updated_at: Date;
}

function rowToTask(row: TaskRow): Task {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    idempotencyKey: row.idempotency_key,
    status: row.status as TaskStatus,
    priority: row.priority as Task["priority"],
    plannedStartAt: row.planned_start_at ? row.planned_start_at.toISOString() : null,
    dueAt: row.due_at ? row.due_at.toISOString() : null,
    timezone: row.timezone,
    assigneeId: row.assignee_id,
    source: row.source,
    completionPolicy: row.completion_policy,
    initiativeId: row.initiative_id,
    weeklyCommitmentId: row.weekly_commitment_id,
    sortKey: row.sort_key,
    assigneeMemberId: row.assignee_member_id,
    ownerMemberId: row.owner_member_id,
    executionMode: row.execution_mode as Task["executionMode"],
    function: row.function,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createTask = api(
  { method: "POST", path: "/operations/tasks", expose: true },
  async (params: CreateTaskParams): Promise<Task> => {
    await getWorkspace({ id: params.workspaceId });
    if (params.assigneeMemberId !== undefined) {
      await getWorkforceMember({ id: params.assigneeMemberId });
    }
    if (params.ownerMemberId !== undefined) {
      await getWorkforceMember({ id: params.ownerMemberId });
    }

    const row = await operationsDB.queryRow<TaskRow>`
      INSERT INTO operating.tasks (
        workspace_id, title, priority, due_at, initiative_id,
        assignee_member_id, owner_member_id, execution_mode, function
      )
      VALUES (
        ${params.workspaceId}, ${params.title}, ${params.priority ?? "medium"}, ${params.dueAt ?? null},
        ${params.initiativeId ?? null}, ${params.assigneeMemberId ?? null}, ${params.ownerMemberId ?? null},
        ${params.executionMode ?? null}, ${params.function ?? null}
      )
      RETURNING id, workspace_id, title, idempotency_key, status, priority, planned_start_at, due_at,
        timezone, assignee_id, source, completion_policy, initiative_id, weekly_commitment_id, sort_key,
        assignee_member_id, owner_member_id, execution_mode, function, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create task");
    return rowToTask(row);
  }
);

export const getTask = api(
  { method: "GET", path: "/operations/tasks/:id", expose: true },
  async ({ id }: { id: number }): Promise<Task> => {
    const row = await operationsDB.queryRow<TaskRow>`
      SELECT id, workspace_id, title, idempotency_key, status, priority, planned_start_at, due_at,
        timezone, assignee_id, source, completion_policy, initiative_id, weekly_commitment_id, sort_key,
        assignee_member_id, owner_member_id, execution_mode, function, created_at, updated_at
      FROM operating.tasks WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`task ${id} not found`);
    return rowToTask(row);
  }
);

export const listTasks = api(
  { method: "GET", path: "/operations/tasks", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ tasks: Task[] }> => {
    const rows = operationsDB.query<TaskRow>`
      SELECT id, workspace_id, title, idempotency_key, status, priority, planned_start_at, due_at,
        timezone, assignee_id, source, completion_policy, initiative_id, weekly_commitment_id, sort_key,
        assignee_member_id, owner_member_id, execution_mode, function, created_at, updated_at
      FROM operating.tasks WHERE workspace_id = ${workspaceId}
      ORDER BY created_at DESC
    `;
    const tasks: Task[] = [];
    for await (const row of rows) {
      tasks.push(rowToTask(row));
    }
    return { tasks };
  }
);

export const updateTaskStatus = api(
  { method: "POST", path: "/operations/tasks/:id/status", expose: true },
  async ({ id, status }: { id: number; status: TaskStatus }): Promise<Task> => {
    if (!TASK_STATUSES.includes(status)) {
      throw APIError.invalidArgument(`status must be one of ${TASK_STATUSES.join(", ")}`);
    }
    const row = await operationsDB.queryRow<TaskRow>`
      UPDATE operating.tasks SET status = ${status}, updated_at = now()
      WHERE id = ${id}
      RETURNING id, workspace_id, title, idempotency_key, status, priority, planned_start_at, due_at,
        timezone, assignee_id, source, completion_policy, initiative_id, weekly_commitment_id, sort_key,
        assignee_member_id, owner_member_id, execution_mode, function, created_at, updated_at
    `;
    if (!row) throw APIError.notFound(`task ${id} not found`);
    const task = rowToTask(row);
    if (task.status === "done") {
      await taskEvents.publish(buildTaskCompletedEvent(task));
    }
    return task;
  }
);
```

- [ ] **Step 6: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test task.test.ts`
Expected: PASS (7 tests)

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/operations/migrations/1_create_tasks.up.sql services/operations/task-events.ts services/operations/task.ts services/operations/task.test.ts
git commit -m "feat(operations): canonical Task schema and API with identity validation"
```

---

### Task 3: Initiative schema + API

**Files:**
- Create: `services/operations/migrations/2_create_initiatives.up.sql`
- Create: `services/operations/initiative.ts`
- Create: `services/operations/initiative.test.ts`

**Interfaces:**
- Consumes: `operationsDB` (Task 1), `getWorkspace` from `services/identity/workspace.ts`.
- Produces: `Initiative` interface, `createInitiative`, `getInitiative` — Task 4's OKR objectives don't consume this directly, but `Task.initiativeId` (Task 2) now has a real table to point at once this migration runs.

- [ ] **Step 1: Write the migration**

`services/operations/migrations/2_create_initiatives.up.sql` — also adds the deferred FK constraint from `operating.tasks.initiative_id` now that the target table exists; `brain_id`/`project_id`/`offering_id` are nullable per Global Constraints (canonical has `brain_id` `NOT NULL` — deviation is intentional and documented):

```sql
CREATE SCHEMA IF NOT EXISTS strategy;

CREATE TABLE strategy.initiatives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  brain_id BIGINT,
  project_id BIGINT,
  offering_id BIGINT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_initiatives_workspace_id ON strategy.initiatives(workspace_id);

ALTER TABLE operating.tasks
  ADD CONSTRAINT fk_tasks_initiative_id FOREIGN KEY (initiative_id) REFERENCES strategy.initiatives(id);
```

- [ ] **Step 2: Write the failing test**

`services/operations/initiative.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createInitiative, getInitiative } from "./initiative";
import { createTask } from "./task";

describe("createInitiative", () => {
  it("creates an initiative with the default active status", async () => {
    const workspace = await createWorkspace({ name: "Initiative Test Inc" });
    const initiative = await createInitiative({ workspaceId: workspace.id, title: "Launch v1" });
    expect(initiative.id).toBeGreaterThan(0);
    expect(initiative.status).toBe("active");
  });

  it("rejects an initiative for a workspace that doesn't exist", async () => {
    await expect(createInitiative({ workspaceId: 999999999, title: "Orphan" })).rejects.toThrow();
  });
});

describe("getInitiative", () => {
  it("fetches a previously created initiative", async () => {
    const workspace = await createWorkspace({ name: "Fetch Initiative Inc" });
    const created = await createInitiative({ workspaceId: workspace.id, title: "Fetch me" });
    const fetched = await getInitiative({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getInitiative({ id: 999999999 })).rejects.toThrow();
  });
});

describe("Task.initiativeId FK", () => {
  it("accepts a task linked to a real initiative", async () => {
    const workspace = await createWorkspace({ name: "Task Initiative Link Inc" });
    const initiative = await createInitiative({ workspaceId: workspace.id, title: "Linked initiative" });
    const task = await createTask({ workspaceId: workspace.id, title: "Linked task", initiativeId: initiative.id });
    expect(task.initiativeId).toBe(initiative.id);
  });

  it("rejects a task linked to a non-existent initiative (real DB FK)", async () => {
    const workspace = await createWorkspace({ name: "Bad Initiative Link Inc" });
    await expect(
      createTask({ workspaceId: workspace.id, title: "Bad link", initiativeId: 999999999 })
    ).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test initiative.test.ts`
Expected: FAIL — `Cannot find module './initiative'`

- [ ] **Step 4: Implement initiative.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { operationsDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface Initiative {
  id: number;
  workspaceId: number;
  brainId: number | null;
  projectId: number | null;
  offeringId: number | null;
  title: string;
  status: string;
  ownerId: number | null;
  createdAt: string;
}

export interface CreateInitiativeParams {
  workspaceId: number;
  title: string;
  ownerId?: number;
}

interface InitiativeRow {
  id: number;
  workspace_id: number;
  brain_id: number | null;
  project_id: number | null;
  offering_id: number | null;
  title: string;
  status: string;
  owner_id: number | null;
  created_at: Date;
}

function rowToInitiative(row: InitiativeRow): Initiative {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    brainId: row.brain_id,
    projectId: row.project_id,
    offeringId: row.offering_id,
    title: row.title,
    status: row.status,
    ownerId: row.owner_id,
    createdAt: row.created_at.toISOString(),
  };
}

export const createInitiative = api(
  { method: "POST", path: "/operations/initiatives", expose: true },
  async (params: CreateInitiativeParams): Promise<Initiative> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await operationsDB.queryRow<InitiativeRow>`
      INSERT INTO strategy.initiatives (workspace_id, title, owner_id)
      VALUES (${params.workspaceId}, ${params.title}, ${params.ownerId ?? null})
      RETURNING id, workspace_id, brain_id, project_id, offering_id, title, status, owner_id, created_at
    `;
    if (!row) throw APIError.internal("failed to create initiative");
    return rowToInitiative(row);
  }
);

export const getInitiative = api(
  { method: "GET", path: "/operations/initiatives/:id", expose: true },
  async ({ id }: { id: number }): Promise<Initiative> => {
    const row = await operationsDB.queryRow<InitiativeRow>`
      SELECT id, workspace_id, brain_id, project_id, offering_id, title, status, owner_id, created_at
      FROM strategy.initiatives WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`initiative ${id} not found`);
    return rowToInitiative(row);
  }
);
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test initiative.test.ts task.test.ts`
Expected: PASS (all tests in both files — this also re-runs Task 2's suite since the new FK constraint touches `operating.tasks`)

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/operations/migrations/2_create_initiatives.up.sql services/operations/initiative.ts services/operations/initiative.test.ts
git commit -m "feat(operations): Initiative schema and API, real FK from Task.initiativeId"
```

---

### Task 4: OKR schema + API (Cycle, Objective, KeyResult)

**Files:**
- Create: `services/operations/migrations/3_create_okr.up.sql`
- Create: `services/operations/okr-scoring.ts`
- Create: `services/operations/okr-scoring.test.ts`
- Create: `services/operations/okr-events.ts`
- Create: `services/operations/okr.ts`
- Create: `services/operations/okr.test.ts`

**Interfaces:**
- Consumes: `operationsDB` (Task 1), `getWorkspace` from `services/identity/workspace.ts`, `OKR_PROGRESS_UPDATED` from `services/shared/events.ts`.
- Produces: `createOkrCycle`, `createObjective`, `addKeyResult`, `checkin`, `getObjectiveProgress`.

- [ ] **Step 1: Write the migration**

`services/operations/migrations/3_create_okr.up.sql` — column names match `backend/business_core/strategy/okr.py`; `brain_id`/`mvp_stage_id`/`strategic_objective_id`/`metric_id` nullable-no-FK per Global Constraints:

```sql
CREATE TABLE strategy.okr_cycles (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  brain_id BIGINT,
  mvp_stage_id BIGINT,
  name TEXT NOT NULL,
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE strategy.okr_objectives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT NOT NULL REFERENCES strategy.okr_cycles(id),
  strategic_objective_id BIGINT,
  title TEXT NOT NULL,
  why TEXT,
  owner_id BIGINT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE strategy.key_results (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  objective_id BIGINT NOT NULL REFERENCES strategy.okr_objectives(id),
  title TEXT,
  metric_id BIGINT,
  baseline_value DOUBLE PRECISION,
  current_value DOUBLE PRECISION,
  target_value DOUBLE PRECISION,
  unit TEXT,
  cadence TEXT,
  metric_type TEXT,
  evidence_refs JSONB,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_okr_cycles_workspace_id ON strategy.okr_cycles(workspace_id);
CREATE INDEX idx_okr_objectives_workspace_id ON strategy.okr_objectives(workspace_id);
CREATE INDEX idx_okr_objectives_cycle_id ON strategy.okr_objectives(cycle_id);
CREATE INDEX idx_key_results_workspace_id ON strategy.key_results(workspace_id);
CREATE INDEX idx_key_results_objective_id ON strategy.key_results(objective_id);
```

- [ ] **Step 2: Write okr-scoring.ts and its test (ported unchanged from `services/okr/scoring.ts`)**

`services/operations/okr-scoring.ts`:

```typescript
export function computeKeyResultScore(targetValue: number, currentValue: number): number {
  if (targetValue <= 0) return 0;
  return Math.min(currentValue / targetValue, 1);
}

export function computeObjectiveScore(scores: number[]): number {
  if (scores.length === 0) return 0;
  return scores.reduce((sum, score) => sum + score, 0) / scores.length;
}
```

`services/operations/okr-scoring.test.ts` (ported unchanged from `services/okr/scoring.test.ts`):

```typescript
import { describe, expect, it } from "vitest";
import { computeKeyResultScore, computeObjectiveScore } from "./okr-scoring";

describe("computeKeyResultScore", () => {
  it("returns 0 when target is 0 or negative", () => {
    expect(computeKeyResultScore(0, 5)).toBe(0);
    expect(computeKeyResultScore(-1, 5)).toBe(0);
  });

  it("returns the current/target ratio", () => {
    expect(computeKeyResultScore(10, 5)).toBe(0.5);
  });

  it("caps the score at 1 even when current exceeds target", () => {
    expect(computeKeyResultScore(10, 15)).toBe(1);
  });
});

describe("computeObjectiveScore", () => {
  it("returns 0 for an empty list", () => {
    expect(computeObjectiveScore([])).toBe(0);
  });

  it("averages the scores", () => {
    expect(computeObjectiveScore([0.5, 1, 0])).toBeCloseTo(0.5);
  });

  it("returns the single score for a one-element list", () => {
    expect(computeObjectiveScore([0.75])).toBe(0.75);
  });

  it("returns 1 when every key result is fully met", () => {
    expect(computeObjectiveScore([1, 1, 1])).toBe(1);
  });
});
```

Run: `cd /Volumes/SSD/javis-saas/services && encore test okr-scoring.test.ts`
Expected: PASS (7 tests) — this has no dependency on the migration, so it can be verified before moving on.

- [ ] **Step 3: Write okr-events.ts**

`services/operations/okr-events.ts` (ported from `services/okr/events.ts`, unchanged logic):

```typescript
import { Topic } from "encore.dev/pubsub";
import { DomainEvent, makeDomainEvent, OKR_PROGRESS_UPDATED } from "../shared/events";

export interface OkrProgressUpdatedPayload {
  objectiveId: number;
  score: number;
}

export type OkrProgressUpdatedEvent = DomainEvent<typeof OKR_PROGRESS_UPDATED, OkrProgressUpdatedPayload>;

export const okrEvents = new Topic<OkrProgressUpdatedEvent>("okr-events", {
  deliveryGuarantee: "at-least-once",
});

export function buildOkrProgressUpdatedEvent(objectiveId: number, score: number): OkrProgressUpdatedEvent {
  return makeDomainEvent(OKR_PROGRESS_UPDATED, { objectiveId, score });
}
```

- [ ] **Step 4: Write the failing okr.ts test**

`services/operations/okr.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createOkrCycle, createObjective, addKeyResult, checkin, getObjectiveProgress } from "./okr";

async function makeCycle() {
  const workspace = await createWorkspace({ name: `OKR Test ${Date.now()}` });
  const cycle = await createOkrCycle({ workspaceId: workspace.id, name: "Q1" });
  return { workspace, cycle };
}

describe("createOkrCycle", () => {
  it("creates a cycle with the default draft status", async () => {
    const { cycle } = await makeCycle();
    expect(cycle.id).toBeGreaterThan(0);
    expect(cycle.status).toBe("draft");
  });

  it("rejects a cycle for a workspace that doesn't exist", async () => {
    await expect(createOkrCycle({ workspaceId: 999999999, name: "Bad" })).rejects.toThrow();
  });
});

describe("createObjective", () => {
  it("creates an objective under a cycle", async () => {
    const { workspace, cycle } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue" });
    expect(objective.id).toBeGreaterThan(0);
    expect(objective.cycleId).toBe(cycle.id);
  });

  it("rejects an objective under a cycle that doesn't exist (real DB FK)", async () => {
    const { workspace } = await makeCycle();
    await expect(
      createObjective({ workspaceId: workspace.id, cycleId: 999999999, title: "Orphan" })
    ).rejects.toThrow();
  });
});

describe("addKeyResult + checkin + getObjectiveProgress", () => {
  it("scores an objective from its key results after check-ins", async () => {
    const { workspace, cycle } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue" });
    const kr1 = await addKeyResult({ objectiveId: objective.id, title: "Sign 10 customers", targetValue: 10 });
    const kr2 = await addKeyResult({ objectiveId: objective.id, title: "Reach $10k MRR", targetValue: 10000 });

    await checkin({ id: kr1.id, value: 5 });
    await checkin({ id: kr2.id, value: 10000 });

    const progress = await getObjectiveProgress({ objectiveId: objective.id });
    expect(progress.score).toBeCloseTo(0.75);
    expect(progress.keyResults).toHaveLength(2);
  });
});
```

- [ ] **Step 5: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test okr.test.ts`
Expected: FAIL — `Cannot find module './okr'`

- [ ] **Step 6: Implement okr.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { operationsDB } from "./db";
import { getWorkspace } from "../identity/workspace";
import { buildOkrProgressUpdatedEvent, okrEvents } from "./okr-events";
import { computeKeyResultScore, computeObjectiveScore } from "./okr-scoring";

export interface OkrCycle {
  id: number;
  workspaceId: number;
  name: string;
  status: string;
  createdAt: string;
}

export interface CreateOkrCycleParams {
  workspaceId: number;
  name: string;
}

interface OkrCycleRow {
  id: number;
  workspace_id: number;
  name: string;
  status: string;
  created_at: Date;
}

function rowToOkrCycle(row: OkrCycleRow): OkrCycle {
  return { id: row.id, workspaceId: row.workspace_id, name: row.name, status: row.status, createdAt: row.created_at.toISOString() };
}

export const createOkrCycle = api(
  { method: "POST", path: "/operations/okr-cycles", expose: true },
  async (params: CreateOkrCycleParams): Promise<OkrCycle> => {
    await getWorkspace({ id: params.workspaceId });
    const row = await operationsDB.queryRow<OkrCycleRow>`
      INSERT INTO strategy.okr_cycles (workspace_id, name)
      VALUES (${params.workspaceId}, ${params.name})
      RETURNING id, workspace_id, name, status, created_at
    `;
    if (!row) throw APIError.internal("failed to create okr cycle");
    return rowToOkrCycle(row);
  }
);

export interface Objective {
  id: number;
  workspaceId: number;
  cycleId: number;
  title: string;
  why: string | null;
  ownerId: number | null;
  status: string;
  createdAt: string;
}

export interface CreateObjectiveParams {
  workspaceId: number;
  cycleId: number;
  title: string;
  why?: string;
  ownerId?: number;
}

interface ObjectiveRow {
  id: number;
  workspace_id: number;
  cycle_id: number;
  title: string;
  why: string | null;
  owner_id: number | null;
  status: string;
  created_at: Date;
}

function rowToObjective(row: ObjectiveRow): Objective {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    cycleId: row.cycle_id,
    title: row.title,
    why: row.why,
    ownerId: row.owner_id,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const createObjective = api(
  { method: "POST", path: "/operations/objectives", expose: true },
  async (params: CreateObjectiveParams): Promise<Objective> => {
    await getWorkspace({ id: params.workspaceId });
    const row = await operationsDB.queryRow<ObjectiveRow>`
      INSERT INTO strategy.okr_objectives (workspace_id, cycle_id, title, why, owner_id)
      VALUES (${params.workspaceId}, ${params.cycleId}, ${params.title}, ${params.why ?? null}, ${params.ownerId ?? null})
      RETURNING id, workspace_id, cycle_id, title, why, owner_id, status, created_at
    `;
    if (!row) throw APIError.internal("failed to create objective");
    return rowToObjective(row);
  }
);

export interface KeyResult {
  id: number;
  objectiveId: number;
  title: string | null;
  targetValue: number | null;
  currentValue: number | null;
  unit: string | null;
  status: string;
  createdAt: string;
}

export interface AddKeyResultParams {
  objectiveId: number;
  title: string;
  targetValue: number;
  unit?: string;
}

interface KeyResultRow {
  id: number;
  objective_id: number;
  title: string | null;
  target_value: number | null;
  current_value: number | null;
  unit: string | null;
  status: string;
  created_at: Date;
}

function rowToKeyResult(row: KeyResultRow): KeyResult {
  return {
    id: row.id,
    objectiveId: row.objective_id,
    title: row.title,
    targetValue: row.target_value,
    currentValue: row.current_value,
    unit: row.unit,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const addKeyResult = api(
  { method: "POST", path: "/operations/objectives/:objectiveId/key-results", expose: true },
  async (params: AddKeyResultParams): Promise<KeyResult> => {
    const row = await operationsDB.queryRow<KeyResultRow>`
      INSERT INTO strategy.key_results (objective_id, title, target_value, current_value, unit)
      VALUES (${params.objectiveId}, ${params.title}, ${params.targetValue}, 0, ${params.unit ?? "count"})
      RETURNING id, objective_id, title, target_value, current_value, unit, status, created_at
    `;
    if (!row) throw APIError.internal("failed to add key result");
    return rowToKeyResult(row);
  }
);

export const checkin = api(
  { method: "POST", path: "/operations/key-results/:id/checkin", expose: true },
  async ({ id, value }: { id: number; value: number }): Promise<KeyResult> => {
    const row = await operationsDB.queryRow<KeyResultRow>`
      UPDATE strategy.key_results SET current_value = ${value}
      WHERE id = ${id}
      RETURNING id, objective_id, title, target_value, current_value, unit, status, created_at
    `;
    if (!row) throw APIError.notFound(`key result ${id} not found`);
    return rowToKeyResult(row);
  }
);

export const getObjectiveProgress = api(
  { method: "GET", path: "/operations/objectives/:objectiveId/progress", expose: true },
  async ({
    objectiveId,
  }: {
    objectiveId: number;
  }): Promise<{ objectiveId: number; score: number; keyResults: { id: number; title: string | null; score: number }[] }> => {
    const rows = operationsDB.query<KeyResultRow>`
      SELECT id, objective_id, title, target_value, current_value, unit, status, created_at
      FROM strategy.key_results WHERE objective_id = ${objectiveId}
    `;
    const keyResults: { id: number; title: string | null; score: number }[] = [];
    for await (const row of rows) {
      const kr = rowToKeyResult(row);
      keyResults.push({ id: kr.id, title: kr.title, score: computeKeyResultScore(kr.targetValue ?? 0, kr.currentValue ?? 0) });
    }
    const score = computeObjectiveScore(keyResults.map((kr) => kr.score));
    await okrEvents.publish(buildOkrProgressUpdatedEvent(objectiveId, score));
    return { objectiveId, score, keyResults };
  }
);
```

- [ ] **Step 7: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test okr.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/operations/migrations/3_create_okr.up.sql services/operations/okr-scoring.ts services/operations/okr-scoring.test.ts services/operations/okr-events.ts services/operations/okr.ts services/operations/okr.test.ts
git commit -m "feat(operations): OKR cycle/objective/key-result schema and API"
```

---

### Task 5: Cutover — delete the old prototypes, full verification

**Files:**
- Delete: `services/tasks/` (entire directory)
- Delete: `services/okr/` (entire directory)
- Modify: `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` (append parity note)

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: nothing new — verification and cleanup checkpoint.

- [ ] **Step 1: Confirm (again) there are no real consumers before deleting**

Run: `grep -rl "services/tasks\|services/okr" /Volumes/SSD/javis-saas/backend /Volumes/SSD/javis-saas/frontend /Volumes/SSD/javis-saas/services/realtime_agent 2>/dev/null | grep -v node_modules`
Expected: at most the one pre-existing unrelated docstring mention in `backend/agentos/evals/business_outcome_eval.py` (verified in this plan's Global Constraints) — if this now shows a real new consumer, STOP and re-scope this task instead of deleting.

- [ ] **Step 2: Delete the old prototype services**

```bash
cd /Volumes/SSD/javis-saas
git rm -r services/tasks services/okr
```

- [ ] **Step 3: Run the entire `services/` test suite**

Run: `cd /Volumes/SSD/javis-saas/services && npm run encore-test 2>/dev/null || encore test`
(if there's no `encore-test` script, just: `encore test`)
Expected: PASS — every test file under `identity/` and `operations/`, plus `shared/`, all green; no `tasks/`/`okr/` test files remain to fail.

- [ ] **Step 4: Type-check the whole services app**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Smoke-test the HTTP surface by hand**

Run: `cd /Volumes/SSD/javis-saas/services && encore run` (leave running in one terminal)
In another terminal:
```bash
WORKSPACE_ID=$(curl -s -X POST http://localhost:4000/identity/workspaces -H 'Content-Type: application/json' -d '{"name":"Ops Smoke Test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST http://localhost:4000/operations/tasks -H 'Content-Type: application/json' \
  -d "{\"workspaceId\":$WORKSPACE_ID,\"title\":\"Smoke task\"}"
```
Expected: JSON response with `status: "todo"`, `priority: "medium"`. Stop `encore run` (Ctrl+C) once confirmed.

- [ ] **Step 6: Record the parity status**

Append to `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`, after the `services/identity` parity note added by the prior plan:

```markdown

**Parity status — `services/operations` (Phase 1, done):** Task (canonical fields), Initiative, OkrCycle/OkrObjective/KeyResult ported; `services/tasks` and `services/okr` prototypes deleted. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): `TaskDependency`/`TaskSchedule`/`OkrLink` not ported (no consumer); `TwelveWeekCycle`/`WeeklyPlan`/`WeeklyCommitment` not ported, so `Task.weeklyCommitmentId` is unvalidated; `Portfolio`/`StrategyCanvas`/`Project`/`Offering`/`Templates`/`Capability`/`Stage`/`Founder`/`NextAction` not ported. Carried-over gap from `services/identity`: `Brain` was never ported, so `Initiative.brainId`/`OkrCycle.brainId` are nullable instead of the canonical `NOT NULL` — needs reconciliation once a `knowledge`/Brain module is actually needed by a consumer.
```

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add docs/superpowers/specs/2026-08-22-services-cluster-model-design.md
git commit -m "chore(operations): delete tasks/okr prototypes, record Phase 1 parity status"
```

---

## Self-Review Notes

- **Spec coverage**: parent spec's `services/operations` row lists "Tasks, Strategy (OKR, 12-Week-Year, Initiative, Portfolio), Projects, Workflow engine, Learning". This plan covers Tasks + OKR + Initiative only — 12-Week-Year/Portfolio/Projects/Workflow engine/Learning are explicitly named out-of-scope in Global Constraints (no consumer yet, matching the identity plan's YAGNI precedent), not silently dropped. They need their own follow-up plan(s) when a real consumer needs them.
- **Discovered gap surfaced, not silently patched**: the `Brain` omission from the `services/identity` plan is called out explicitly (Global Constraints + Task 5's parity note) rather than fixed unilaterally by reopening the already-shipped identity plan.
- **Cross-cluster reference rule applied consistently**: `workspace_id` validated via `identity.getWorkspace` on every create in `task.ts`/`initiative.ts`/`okr.ts`; `assignee_member_id`/`owner_member_id` validated via `identity.getWorkforceMember` when provided; `assignee_id`/`owner_id` deliberately left unvalidated with reasoning given (no `getUser` endpoint exists, no consumer needs it).
- **Type consistency checked**: `Task`/`Initiative`/`OkrCycle`/`Objective`/`KeyResult` interfaces and their row-mappers use consistent field names across `task.ts`, `initiative.ts`, `okr.ts`, and the corresponding test files that import them.

## Next Plan

This plan covers `services/operations` only. Per the parent spec's dependency order, the next implementation plan is `services/commercial` (CRM, Sales, Marketing, Billing — CRM/Billing are net-new, no existing Python model to port field-for-field), which will consume `services/identity`'s `getWorkspace` the same way this plan does.
