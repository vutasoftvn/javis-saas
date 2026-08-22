# AgentOS Phase 2 — Business OS MVP (Encore TypeScript) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `services/` Encore TypeScript app (blueprint's Business OS layer) with two production-shaped domain services — Tasks and OKR — each with typed API endpoints, its own Postgres-backed migrations, and canonical `entity.action` domain events, per Phase 2 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4.

**Architecture:** New standalone app `services/` (Encore TypeScript, one Encore microservice per domain folder). Each service owns its own SQL migrations and database (Encore provisions/migrates Postgres automatically per service — this is a separate database from the existing `cosa_postgres` container in `docker-compose.yml`, which keeps serving the current Python backend unchanged). Domain events use a canonical `entity.action` naming module shared across services, mirroring the naming convention already established in `backend/agentos/core/events.py` (Phase 0) on the Python side — this is the "early normalization" principle from the spec (§92 of the Master Architecture doc), kept consistent across both stacks even though nothing wires them together yet. No integration with `backend/agentos/` or any existing Python module happens in this plan — that cutover is a later phase.

**Tech Stack:** Encore TypeScript (CLI `v1.57.13`, confirmed installed via `encore version`), Node.js v22, TypeScript 5.7, Vitest (via `encore test`, Encore's built-in test runner).

## Global Constraints

- All new code lives under `services/` at the repo root (sibling to `backend/`, `frontend/`) — do not modify anything under `backend/` in this plan.
- Encore manages its own local Postgres container per app automatically on `encore run` / `encore test` (first invocation pulls/starts Docker containers, which can take a minute) — do not point it at the existing `cosa_postgres` container or `DATABASE_URL` from `docker-compose.yml`; the two are intentionally separate at this phase.
- Event names follow `entity.action` (lowercase, dot-separated) — see `services/shared/events.ts` (Task 2) — the same convention as `backend/agentos/core/events.py` `EVENT_*` constants from the Phase 0/1 plan.
- Every domain event's payload-construction logic is a pure, DB/pubsub-free function (`build*Event`) so it can be unit tested without spinning up Encore's Pub/Sub runtime — endpoints call the pure builder, then publish.
- Money/percentage-like values (OKR progress) are `DOUBLE PRECISION` in Postgres and `number` in TypeScript for MVP — do not introduce a decimal library; this is explicitly flagged as an MVP simplification, not a finance-grade precision guarantee.
- Run tests via: `cd services && encore test ./<service>/<file>.test.ts`
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.5 (Business OS), §4 (Phase 2 scope).

---

## File Structure

```text
services/
├── encore.app                       # {"id": ""}
├── package.json
├── tsconfig.json
├── shared/
│   ├── events.ts                     # canonical event names, DomainEvent<Name, Payload>, makeDomainEvent
│   └── events.test.ts
├── tasks/
│   ├── encore.service.ts              # Service("tasks")
│   ├── db.ts                           # SQLDatabase("tasks", ...)
│   ├── migrations/
│   │   └── 1_create_tasks.up.sql
│   ├── task.ts                          # Task/CreateTaskParams types, createTask, getTask, listTasks, completeTask endpoints
│   ├── events.ts                         # TaskCompletedEvent, taskEvents Topic, buildTaskCompletedEvent
│   ├── task.test.ts
│   └── events.test.ts
└── okr/
    ├── encore.service.ts
    ├── db.ts
    ├── migrations/
    │   └── 1_create_okr.up.sql
    ├── okr.ts                            # Objective/KeyResult types, createObjective, addKeyResult, checkin, getObjectiveProgress
    ├── scoring.ts                         # computeKeyResultScore, computeObjectiveScore (pure)
    ├── events.ts                           # OkrProgressUpdatedEvent, okrEvents Topic, buildOkrProgressUpdatedEvent
    ├── okr.test.ts
    ├── scoring.test.ts
    └── events.test.ts
```

---

### Task 1: Scaffold Encore TypeScript app

**Files:**
- Create: `services/encore.app`
- Create: `services/package.json`
- Create: `services/tsconfig.json`
- Create: `services/shared/encore.service.ts` *(not created — `shared/` is a plain utility module, not an Encore service; skip)*
- Test: `services/shared/events.test.ts` *(trivial smoke test written in this task, real content added in Task 2)*

**Interfaces:** None yet — this task only proves the toolchain runs.

- [ ] **Step 1: Create the Encore app manifest**

```json
// services/encore.app
{
  "id": ""
}
```

- [ ] **Step 2: Create package.json**

```json
// services/package.json
{
  "name": "ai-agent-os-services",
  "private": true,
  "type": "module",
  "dependencies": {
    "encore.dev": "^1.57.0"
  },
  "devDependencies": {
    "typescript": "^5.7.3",
    "vitest": "^3.0.0"
  }
}
```

- [ ] **Step 3: Create tsconfig.json**

```json
// services/tsconfig.json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  }
}
```

- [ ] **Step 4: Write a smoke-test placeholder that will be filled in by Task 2**

```typescript
// services/shared/events.ts
export const SCAFFOLD_OK = true;
```

```typescript
// services/shared/events.test.ts
import { describe, expect, it } from "vitest";
import { SCAFFOLD_OK } from "./events";

describe("scaffold", () => {
  it("boots the Encore test runner", () => {
    expect(SCAFFOLD_OK).toBe(true);
  });
});
```

- [ ] **Step 5: Install dependencies and run the smoke test**

Run: `cd services && npm install && encore test ./shared/events.test.ts`
Expected: 1 passed (first run may take longer while Encore provisions its local Docker daemon connection — no database is needed yet since no service defines one in this task)

- [ ] **Step 6: Commit**

```bash
git add services/encore.app services/package.json services/tsconfig.json services/shared/events.ts services/shared/events.test.ts
git commit -m "chore(services): scaffold Encore TypeScript app"
```

---

### Task 2: Shared canonical event naming module

**Files:**
- Modify: `services/shared/events.ts` (replace scaffold placeholder)
- Modify: `services/shared/events.test.ts` (replace scaffold smoke test)

**Interfaces:**
- Produces: `TASK_CREATED`, `TASK_COMPLETED`, `OKR_PROGRESS_UPDATED` (string constants, `"entity.action"` form); `DomainEvent<Name extends string, Payload>` (`{ name: Name; emittedAt: string; payload: Payload }`); `makeDomainEvent<Name extends string, Payload>(name: Name, payload: Payload): DomainEvent<Name, Payload>`.

- [ ] **Step 1: Write the failing test**

```typescript
// services/shared/events.test.ts
import { describe, expect, it } from "vitest";
import { makeDomainEvent, TASK_COMPLETED } from "./events";

describe("makeDomainEvent", () => {
  it("stamps the canonical name, payload, and an ISO timestamp", () => {
    const event = makeDomainEvent(TASK_COMPLETED, { taskId: 1 });
    expect(event.name).toBe("task.completed");
    expect(event.payload).toEqual({ taskId: 1 });
    expect(() => new Date(event.emittedAt).toISOString()).not.toThrow();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd services && encore test ./shared/events.test.ts`
Expected: FAIL — `TASK_COMPLETED` / `makeDomainEvent` not exported from `./events`

- [ ] **Step 3: Write the implementation**

```typescript
// services/shared/events.ts
// Canonical event names follow "entity.action" — mirrors
// backend/agentos/core/events.py EVENT_* constants on the Python side.
// See docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md §3.9/§46.
export const TASK_CREATED = "task.created";
export const TASK_COMPLETED = "task.completed";
export const OKR_PROGRESS_UPDATED = "okr.progress_updated";

export interface DomainEvent<Name extends string, Payload> {
  name: Name;
  emittedAt: string;
  payload: Payload;
}

export function makeDomainEvent<Name extends string, Payload>(
  name: Name,
  payload: Payload
): DomainEvent<Name, Payload> {
  return { name, emittedAt: new Date().toISOString(), payload };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd services && encore test ./shared/events.test.ts`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add services/shared/events.ts services/shared/events.test.ts
git commit -m "feat(services): add canonical entity.action event naming module"
```

---

### Task 3: Tasks service — migration, `createTask`, `getTask`

**Files:**
- Create: `services/tasks/encore.service.ts`
- Create: `services/tasks/db.ts`
- Create: `services/tasks/migrations/1_create_tasks.up.sql`
- Create: `services/tasks/task.ts`
- Test: `services/tasks/task.test.ts`

**Interfaces:**
- Produces: `Task { id: number; workspaceId: string; title: string; status: "open" | "completed"; priority: "low" | "medium" | "high"; dueDate: string | null; createdAt: string; updatedAt: string }`; `CreateTaskParams { workspaceId: string; title: string; priority?: "low" | "medium" | "high"; dueDate?: string }`; `createTask(params: CreateTaskParams): Promise<Task>`; `getTask({ id: number }): Promise<Task>` (throws `APIError.notFound` if missing).

- [ ] **Step 1: Write the failing tests**

```typescript
// services/tasks/task.test.ts
import { describe, expect, it } from "vitest";
import { createTask, getTask } from "./task";

describe("createTask", () => {
  it("creates a task with default priority and open status", async () => {
    const task = await createTask({ workspaceId: "ws1", title: "Write plan" });
    expect(task.id).toBeGreaterThan(0);
    expect(task.workspaceId).toBe("ws1");
    expect(task.title).toBe("Write plan");
    expect(task.status).toBe("open");
    expect(task.priority).toBe("medium");
  });

  it("accepts an explicit priority", async () => {
    const task = await createTask({ workspaceId: "ws1", title: "Urgent", priority: "high" });
    expect(task.priority).toBe("high");
  });
});

describe("getTask", () => {
  it("returns a previously created task", async () => {
    const created = await createTask({ workspaceId: "ws1", title: "Fetch me" });
    const fetched = await getTask({ id: created.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found for a missing id", async () => {
    await expect(getTask({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services && encore test ./tasks/task.test.ts`
Expected: FAIL — `Cannot find module './task'` (file does not exist yet)

- [ ] **Step 3: Write the service registration, database, and migration**

```typescript
// services/tasks/encore.service.ts
import { Service } from "encore.dev/service";

export default new Service("tasks");
```

```typescript
// services/tasks/db.ts
import { SQLDatabase } from "encore.dev/storage/sqldb";

export const tasksDB = new SQLDatabase("tasks", {
  migrations: "./migrations",
});
```

```sql
-- services/tasks/migrations/1_create_tasks.up.sql
CREATE TABLE tasks (
  id BIGSERIAL PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  priority TEXT NOT NULL DEFAULT 'medium',
  due_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 4: Write the implementation**

```typescript
// services/tasks/task.ts
import { api, APIError } from "encore.dev/api";
import { tasksDB } from "./db";

export interface Task {
  id: number;
  workspaceId: string;
  title: string;
  status: "open" | "completed";
  priority: "low" | "medium" | "high";
  dueDate: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskParams {
  workspaceId: string;
  title: string;
  priority?: "low" | "medium" | "high";
  dueDate?: string;
}

interface TaskRow {
  id: number;
  workspace_id: string;
  title: string;
  status: "open" | "completed";
  priority: "low" | "medium" | "high";
  due_date: Date | null;
  created_at: Date;
  updated_at: Date;
}

function rowToTask(row: TaskRow): Task {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    status: row.status,
    priority: row.priority,
    dueDate: row.due_date ? row.due_date.toISOString() : null,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createTask = api(
  { method: "POST", path: "/tasks", expose: true },
  async (params: CreateTaskParams): Promise<Task> => {
    const row = await tasksDB.queryRow<TaskRow>`
      INSERT INTO tasks (workspace_id, title, priority, due_date)
      VALUES (${params.workspaceId}, ${params.title}, ${params.priority ?? "medium"}, ${params.dueDate ?? null})
      RETURNING id, workspace_id, title, status, priority, due_date, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create task");
    return rowToTask(row);
  }
);

export const getTask = api(
  { method: "GET", path: "/tasks/:id", expose: true },
  async ({ id }: { id: number }): Promise<Task> => {
    const row = await tasksDB.queryRow<TaskRow>`
      SELECT id, workspace_id, title, status, priority, due_date, created_at, updated_at
      FROM tasks WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`task ${id} not found`);
    return rowToTask(row);
  }
);
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd services && encore test ./tasks/task.test.ts`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add services/tasks/encore.service.ts services/tasks/db.ts services/tasks/migrations/1_create_tasks.up.sql services/tasks/task.ts services/tasks/task.test.ts
git commit -m "feat(services): add tasks service with createTask/getTask"
```

---

### Task 4: Tasks service — `listTasks`, `completeTask`, `task.completed` event

**Files:**
- Modify: `services/tasks/task.ts` (add `listTasks`, `completeTask`)
- Create: `services/tasks/events.ts`
- Test: `services/tasks/task.test.ts` (extend)
- Test: `services/tasks/events.test.ts`

**Interfaces:**
- Consumes: `Task`, `rowToTask`-shaped row from `services/tasks/task.ts` (Task 3); `DomainEvent`, `makeDomainEvent`, `TASK_COMPLETED` from `services/shared/events.ts` (Task 2).
- Produces: `listTasks({ workspaceId: string }): Promise<{ tasks: Task[] }>`; `completeTask({ id: number }): Promise<Task>`; `TaskCompletedEvent = DomainEvent<typeof TASK_COMPLETED, { taskId: number; workspaceId: string }>`; `buildTaskCompletedEvent(task: Task): TaskCompletedEvent`; `taskEvents: Topic<TaskCompletedEvent>`.

- [ ] **Step 1: Write the failing tests**

```typescript
// services/tasks/events.test.ts
import { describe, expect, it } from "vitest";
import { buildTaskCompletedEvent } from "./events";
import type { Task } from "./task";

describe("buildTaskCompletedEvent", () => {
  it("builds a task.completed event from a task", () => {
    const task: Task = {
      id: 1,
      workspaceId: "ws1",
      title: "x",
      status: "completed",
      priority: "medium",
      dueDate: null,
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };
    const event = buildTaskCompletedEvent(task);
    expect(event.name).toBe("task.completed");
    expect(event.payload).toEqual({ taskId: 1, workspaceId: "ws1" });
  });
});
```

```typescript
// services/tasks/task.test.ts — append these describe blocks
describe("listTasks", () => {
  it("returns only tasks for the requested workspace", async () => {
    await createTask({ workspaceId: "ws-list-a", title: "A1" });
    await createTask({ workspaceId: "ws-list-a", title: "A2" });
    await createTask({ workspaceId: "ws-list-b", title: "B1" });

    const { tasks } = await listTasks({ workspaceId: "ws-list-a" });

    expect(tasks).toHaveLength(2);
    expect(tasks.every((t) => t.workspaceId === "ws-list-a")).toBe(true);
  });
});

describe("completeTask", () => {
  it("transitions status to completed", async () => {
    const created = await createTask({ workspaceId: "ws1", title: "Finish me" });
    const completed = await completeTask({ id: created.id });
    expect(completed.status).toBe("completed");
  });
});
```

Update the import line at the top of `task.test.ts` to `import { completeTask, createTask, getTask, listTasks } from "./task";`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services && encore test ./tasks/`
Expected: FAIL — `listTasks`/`completeTask` not exported from `./task`, `Cannot find module './events'`

- [ ] **Step 3: Write the event module**

```typescript
// services/tasks/events.ts
import { Topic } from "encore.dev/pubsub";
import { DomainEvent, makeDomainEvent, TASK_COMPLETED } from "../shared/events";
import type { Task } from "./task";

export interface TaskCompletedPayload {
  taskId: number;
  workspaceId: string;
}

export type TaskCompletedEvent = DomainEvent<typeof TASK_COMPLETED, TaskCompletedPayload>;

export const taskEvents = new Topic<TaskCompletedEvent>("task-events", {
  deliveryGuarantee: "at-least-once",
});

export function buildTaskCompletedEvent(task: Task): TaskCompletedEvent {
  return makeDomainEvent(TASK_COMPLETED, { taskId: task.id, workspaceId: task.workspaceId });
}
```

- [ ] **Step 4: Add `listTasks` and `completeTask` to `task.ts`**

Append to `services/tasks/task.ts` (after `getTask`, keep the existing imports and add `import { buildTaskCompletedEvent, taskEvents } from "./events";` at the top):

```typescript
export const listTasks = api(
  { method: "GET", path: "/tasks", expose: true },
  async ({ workspaceId }: { workspaceId: string }): Promise<{ tasks: Task[] }> => {
    const rows = tasksDB.query<TaskRow>`
      SELECT id, workspace_id, title, status, priority, due_date, created_at, updated_at
      FROM tasks WHERE workspace_id = ${workspaceId}
      ORDER BY created_at DESC
    `;
    const tasks: Task[] = [];
    for await (const row of rows) {
      tasks.push(rowToTask(row));
    }
    return { tasks };
  }
);

export const completeTask = api(
  { method: "POST", path: "/tasks/:id/complete", expose: true },
  async ({ id }: { id: number }): Promise<Task> => {
    const row = await tasksDB.queryRow<TaskRow>`
      UPDATE tasks SET status = 'completed', updated_at = now()
      WHERE id = ${id}
      RETURNING id, workspace_id, title, status, priority, due_date, created_at, updated_at
    `;
    if (!row) throw APIError.notFound(`task ${id} not found`);
    const task = rowToTask(row);
    await taskEvents.publish(buildTaskCompletedEvent(task));
    return task;
  }
);
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd services && encore test ./tasks/`
Expected: 7 passed (4 from Task 3 + 1 events + 2 new)

- [ ] **Step 6: Commit**

```bash
git add services/tasks/task.ts services/tasks/events.ts services/tasks/task.test.ts services/tasks/events.test.ts
git commit -m "feat(services): add listTasks/completeTask and task.completed event"
```

---

### Task 5: OKR service — migration, `createObjective`, `addKeyResult`

**Files:**
- Create: `services/okr/encore.service.ts`
- Create: `services/okr/db.ts`
- Create: `services/okr/migrations/1_create_okr.up.sql`
- Create: `services/okr/okr.ts`
- Test: `services/okr/okr.test.ts`

**Interfaces:**
- Produces: `Objective { id: number; workspaceId: string; title: string; period: string; owner: string; createdAt: string }`; `KeyResult { id: number; objectiveId: number; title: string; targetValue: number; currentValue: number; unit: string; createdAt: string; updatedAt: string }`; `CreateObjectiveParams { workspaceId: string; title: string; period: string; owner: string }`; `createObjective(params: CreateObjectiveParams): Promise<Objective>`; `AddKeyResultParams { objectiveId: number; title: string; targetValue: number; unit?: string }`; `addKeyResult(params: AddKeyResultParams): Promise<KeyResult>`.

- [ ] **Step 1: Write the failing tests**

```typescript
// services/okr/okr.test.ts
import { describe, expect, it } from "vitest";
import { addKeyResult, createObjective } from "./okr";

describe("createObjective", () => {
  it("creates an objective", async () => {
    const objective = await createObjective({
      workspaceId: "ws1",
      title: "Grow revenue",
      period: "2026-Q1",
      owner: "founder",
    });
    expect(objective.id).toBeGreaterThan(0);
    expect(objective.title).toBe("Grow revenue");
    expect(objective.period).toBe("2026-Q1");
  });
});

describe("addKeyResult", () => {
  it("attaches a key result to an objective with zero starting progress", async () => {
    const objective = await createObjective({
      workspaceId: "ws1",
      title: "Grow revenue",
      period: "2026-Q1",
      owner: "founder",
    });
    const kr = await addKeyResult({
      objectiveId: objective.id,
      title: "Hit $10k MRR",
      targetValue: 10000,
      unit: "usd",
    });
    expect(kr.objectiveId).toBe(objective.id);
    expect(kr.targetValue).toBe(10000);
    expect(kr.currentValue).toBe(0);
    expect(kr.unit).toBe("usd");
  });

  it("defaults unit to count when not provided", async () => {
    const objective = await createObjective({
      workspaceId: "ws1",
      title: "Ship features",
      period: "2026-Q1",
      owner: "founder",
    });
    const kr = await addKeyResult({ objectiveId: objective.id, title: "Ship 5 features", targetValue: 5 });
    expect(kr.unit).toBe("count");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services && encore test ./okr/okr.test.ts`
Expected: FAIL — `Cannot find module './okr'`

- [ ] **Step 3: Write the service registration, database, and migration**

```typescript
// services/okr/encore.service.ts
import { Service } from "encore.dev/service";

export default new Service("okr");
```

```typescript
// services/okr/db.ts
import { SQLDatabase } from "encore.dev/storage/sqldb";

export const okrDB = new SQLDatabase("okr", {
  migrations: "./migrations",
});
```

```sql
-- services/okr/migrations/1_create_okr.up.sql
CREATE TABLE objectives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  title TEXT NOT NULL,
  period TEXT NOT NULL,
  owner TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE key_results (
  id BIGSERIAL PRIMARY KEY,
  objective_id BIGINT NOT NULL REFERENCES objectives(id),
  title TEXT NOT NULL,
  target_value DOUBLE PRECISION NOT NULL,
  current_value DOUBLE PRECISION NOT NULL DEFAULT 0,
  unit TEXT NOT NULL DEFAULT 'count',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 4: Write the implementation**

```typescript
// services/okr/okr.ts
import { api, APIError } from "encore.dev/api";
import { okrDB } from "./db";

export interface Objective {
  id: number;
  workspaceId: string;
  title: string;
  period: string;
  owner: string;
  createdAt: string;
}

export interface KeyResult {
  id: number;
  objectiveId: number;
  title: string;
  targetValue: number;
  currentValue: number;
  unit: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateObjectiveParams {
  workspaceId: string;
  title: string;
  period: string;
  owner: string;
}

export interface AddKeyResultParams {
  objectiveId: number;
  title: string;
  targetValue: number;
  unit?: string;
}

interface ObjectiveRow {
  id: number;
  workspace_id: string;
  title: string;
  period: string;
  owner: string;
  created_at: Date;
}

interface KeyResultRow {
  id: number;
  objective_id: number;
  title: string;
  target_value: number;
  current_value: number;
  unit: string;
  created_at: Date;
  updated_at: Date;
}

function rowToObjective(row: ObjectiveRow): Objective {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    period: row.period,
    owner: row.owner,
    createdAt: row.created_at.toISOString(),
  };
}

export function rowToKeyResult(row: KeyResultRow): KeyResult {
  return {
    id: row.id,
    objectiveId: row.objective_id,
    title: row.title,
    targetValue: row.target_value,
    currentValue: row.current_value,
    unit: row.unit,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createObjective = api(
  { method: "POST", path: "/objectives", expose: true },
  async (params: CreateObjectiveParams): Promise<Objective> => {
    const row = await okrDB.queryRow<ObjectiveRow>`
      INSERT INTO objectives (workspace_id, title, period, owner)
      VALUES (${params.workspaceId}, ${params.title}, ${params.period}, ${params.owner})
      RETURNING id, workspace_id, title, period, owner, created_at
    `;
    if (!row) throw APIError.internal("failed to create objective");
    return rowToObjective(row);
  }
);

export const addKeyResult = api(
  { method: "POST", path: "/objectives/:objectiveId/key-results", expose: true },
  async (params: AddKeyResultParams): Promise<KeyResult> => {
    const row = await okrDB.queryRow<KeyResultRow>`
      INSERT INTO key_results (objective_id, title, target_value, unit)
      VALUES (${params.objectiveId}, ${params.title}, ${params.targetValue}, ${params.unit ?? "count"})
      RETURNING id, objective_id, title, target_value, current_value, unit, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to add key result");
    return rowToKeyResult(row);
  }
);
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd services && encore test ./okr/okr.test.ts`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add services/okr/encore.service.ts services/okr/db.ts services/okr/migrations/1_create_okr.up.sql services/okr/okr.ts services/okr/okr.test.ts
git commit -m "feat(services): add okr service with createObjective/addKeyResult"
```

---

### Task 6: OKR service — scoring, `checkin`, `getObjectiveProgress`, `okr.progress_updated` event

**Files:**
- Create: `services/okr/scoring.ts`
- Test: `services/okr/scoring.test.ts`
- Create: `services/okr/events.ts`
- Test: `services/okr/events.test.ts`
- Modify: `services/okr/okr.ts` (add `checkin`, `getObjectiveProgress`)
- Test: `services/okr/okr.test.ts` (extend)

**Interfaces:**
- Consumes: `KeyResult`, `rowToKeyResult` from `services/okr/okr.ts` (Task 5); `DomainEvent`, `makeDomainEvent`, `OKR_PROGRESS_UPDATED` from `services/shared/events.ts` (Task 2).
- Produces: `computeKeyResultScore(targetValue: number, currentValue: number): number` (clamped 0–1); `computeObjectiveScore(scores: number[]): number` (average, 0 for empty); `checkin({ id: number; value: number }): Promise<KeyResult>`; `getObjectiveProgress({ objectiveId: number }): Promise<{ objectiveId: number; score: number; keyResults: { id: number; title: string; score: number }[] }>`; `OkrProgressUpdatedEvent = DomainEvent<typeof OKR_PROGRESS_UPDATED, { objectiveId: number; score: number }>`; `buildOkrProgressUpdatedEvent(objectiveId: number, score: number): OkrProgressUpdatedEvent`; `okrEvents: Topic<OkrProgressUpdatedEvent>`.

- [ ] **Step 1: Write the failing tests**

```typescript
// services/okr/scoring.test.ts
import { describe, expect, it } from "vitest";
import { computeKeyResultScore, computeObjectiveScore } from "./scoring";

describe("computeKeyResultScore", () => {
  it("returns 0 when current value is 0", () => {
    expect(computeKeyResultScore(100, 0)).toBe(0);
  });

  it("returns 1 when current value meets target", () => {
    expect(computeKeyResultScore(100, 100)).toBe(1);
  });

  it("returns a fraction for partial progress", () => {
    expect(computeKeyResultScore(100, 25)).toBe(0.25);
  });

  it("clamps at 1 when current value exceeds target", () => {
    expect(computeKeyResultScore(100, 150)).toBe(1);
  });

  it("returns 0 when target is 0 (avoids division by zero)", () => {
    expect(computeKeyResultScore(0, 0)).toBe(0);
  });
});

describe("computeObjectiveScore", () => {
  it("averages key result scores", () => {
    expect(computeObjectiveScore([1, 0.5, 0])).toBeCloseTo(0.5);
  });

  it("returns 0 for an objective with no key results", () => {
    expect(computeObjectiveScore([])).toBe(0);
  });
});
```

```typescript
// services/okr/events.test.ts
import { describe, expect, it } from "vitest";
import { buildOkrProgressUpdatedEvent } from "./events";

describe("buildOkrProgressUpdatedEvent", () => {
  it("builds an okr.progress_updated event", () => {
    const event = buildOkrProgressUpdatedEvent(1, 0.75);
    expect(event.name).toBe("okr.progress_updated");
    expect(event.payload).toEqual({ objectiveId: 1, score: 0.75 });
  });
});
```

```typescript
// services/okr/okr.test.ts — append these describe blocks
describe("checkin", () => {
  it("updates the key result's current value", async () => {
    const objective = await createObjective({ workspaceId: "ws1", title: "Grow", period: "2026-Q1", owner: "founder" });
    const kr = await addKeyResult({ objectiveId: objective.id, title: "Hit target", targetValue: 100 });

    const updated = await checkin({ id: kr.id, value: 40 });

    expect(updated.currentValue).toBe(40);
  });
});

describe("getObjectiveProgress", () => {
  it("computes per-key-result and overall objective score", async () => {
    const objective = await createObjective({ workspaceId: "ws1", title: "Grow", period: "2026-Q1", owner: "founder" });
    const krA = await addKeyResult({ objectiveId: objective.id, title: "A", targetValue: 100 });
    const krB = await addKeyResult({ objectiveId: objective.id, title: "B", targetValue: 50 });
    await checkin({ id: krA.id, value: 100 });
    await checkin({ id: krB.id, value: 0 });

    const progress = await getObjectiveProgress({ objectiveId: objective.id });

    expect(progress.objectiveId).toBe(objective.id);
    expect(progress.score).toBeCloseTo(0.5);
    expect(progress.keyResults).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: krA.id, score: 1 }),
        expect.objectContaining({ id: krB.id, score: 0 }),
      ])
    );
  });
});
```

Update the import line at the top of `okr.test.ts` to `import { addKeyResult, checkin, createObjective, getObjectiveProgress } from "./okr";`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services && encore test ./okr/`
Expected: FAIL — `Cannot find module './scoring'`, `Cannot find module './events'`, `checkin`/`getObjectiveProgress` not exported from `./okr`

- [ ] **Step 3: Write the scoring module**

```typescript
// services/okr/scoring.ts
export function computeKeyResultScore(targetValue: number, currentValue: number): number {
  if (targetValue <= 0) return 0;
  return Math.min(currentValue / targetValue, 1);
}

export function computeObjectiveScore(scores: number[]): number {
  if (scores.length === 0) return 0;
  return scores.reduce((sum, score) => sum + score, 0) / scores.length;
}
```

- [ ] **Step 4: Write the events module**

```typescript
// services/okr/events.ts
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

- [ ] **Step 5: Add `checkin` and `getObjectiveProgress` to `okr.ts`**

Append to `services/okr/okr.ts` (add `import { computeKeyResultScore, computeObjectiveScore } from "./scoring";` and `import { buildOkrProgressUpdatedEvent, okrEvents } from "./events";` to the top):

```typescript
export const checkin = api(
  { method: "POST", path: "/key-results/:id/checkin", expose: true },
  async ({ id, value }: { id: number; value: number }): Promise<KeyResult> => {
    const row = await okrDB.queryRow<KeyResultRow>`
      UPDATE key_results SET current_value = ${value}, updated_at = now()
      WHERE id = ${id}
      RETURNING id, objective_id, title, target_value, current_value, unit, created_at, updated_at
    `;
    if (!row) throw APIError.notFound(`key result ${id} not found`);
    return rowToKeyResult(row);
  }
);

export const getObjectiveProgress = api(
  { method: "GET", path: "/objectives/:objectiveId/progress", expose: true },
  async ({
    objectiveId,
  }: {
    objectiveId: number;
  }): Promise<{ objectiveId: number; score: number; keyResults: { id: number; title: string; score: number }[] }> => {
    const rows = okrDB.query<KeyResultRow>`
      SELECT id, objective_id, title, target_value, current_value, unit, created_at, updated_at
      FROM key_results WHERE objective_id = ${objectiveId}
    `;
    const keyResults: { id: number; title: string; score: number }[] = [];
    for await (const row of rows) {
      const kr = rowToKeyResult(row);
      keyResults.push({ id: kr.id, title: kr.title, score: computeKeyResultScore(kr.targetValue, kr.currentValue) });
    }
    const score = computeObjectiveScore(keyResults.map((kr) => kr.score));
    await okrEvents.publish(buildOkrProgressUpdatedEvent(objectiveId, score));
    return { objectiveId, score, keyResults };
  }
);
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd services && encore test ./okr/`
Expected: 13 passed (3 from Task 5 `okr.test.ts` + 7 new `scoring.test.ts` + 1 new `events.test.ts` + 2 new `okr.test.ts`)

- [ ] **Step 7: Run the full `services` suite to confirm no regressions**

Run: `cd services && encore test`
Expected: all green — 1 (`shared/events.test.ts`) + 7 (`tasks/`) + 13 (`okr/`) = 21 passed

- [ ] **Step 8: Commit**

```bash
git add services/okr/scoring.ts services/okr/scoring.test.ts services/okr/events.ts services/okr/events.test.ts services/okr/okr.ts services/okr/okr.test.ts
git commit -m "feat(services): add OKR scoring, checkin, getObjectiveProgress, and okr.progress_updated event"
```

---

## Verification (end of Phase 2)

1. Run the full new suite: `cd services && encore test` — all tests pass (21 total per Task 6 Step 7).
2. Confirm the existing Python backend is untouched: `git status backend/` shows no changes from this plan.
3. Confirm no cross-stack wiring was introduced yet: `grep -rn "agentos" services --include="*.ts"` returns no results — the Python `agentos/` runtime and the TypeScript `services/` Business OS remain unconnected until a later phase explicitly builds the Tool Adapter (blueprint §3.5: "Agent Core không thao tác DB business trực tiếp — luôn qua Tool Adapter → Encore Business API").
4. Manually exercise one endpoint with `encore run` (in a second terminal) + `curl -X POST http://localhost:4000/tasks -d '{"workspaceId":"ws1","title":"smoke test"}'` to confirm the app boots outside the test runner too.

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 3 (Memory: episodic/semantic, retrieval, consolidation, Python side) and Phase 4 (Skill Layer) are next, followed by the Tool Adapter work that eventually lets `backend/agentos/` call into these Encore endpoints. Each should get its own plan via `superpowers:writing-plans`.
