import { api, APIError } from "encore.dev/api";
import { operationsDB } from "./db";
import { getWorkspace } from "../identity/workspace";
import { getWorkforceMember } from "../identity/organization";
import { buildTaskCompletedEvent, buildTaskCreatedEvent, taskEvents } from "./task-events";

export type TaskStatus = "todo" | "in_progress" | "waiting_approval" | "blocked" | "done" | "cancelled";
export const TASK_STATUSES: readonly TaskStatus[] = ["todo", "in_progress", "waiting_approval", "blocked", "done", "cancelled"];

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
  /** Caller-supplied dedup key (blueprint §82 — a retried write must not create
   * a duplicate task). Unique per workspace; retrying create with the same key
   * returns the original task instead of inserting a second row. Omit for a
   * plain, unconstrained create (multiple NULLs don't conflict). */
  idempotencyKey?: string;
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

    const row = await operationsDB.queryRow<TaskRow & { inserted: boolean }>`
      INSERT INTO operating.tasks (
        workspace_id, title, priority, due_at, initiative_id,
        assignee_member_id, owner_member_id, execution_mode, function, idempotency_key
      )
      VALUES (
        ${params.workspaceId}, ${params.title}, ${params.priority ?? "medium"}, ${params.dueAt ?? null},
        ${params.initiativeId ?? null}, ${params.assigneeMemberId ?? null}, ${params.ownerMemberId ?? null},
        ${params.executionMode ?? null}, ${params.function ?? null}, ${params.idempotencyKey ?? null}
      )
      ON CONFLICT (workspace_id, idempotency_key) DO UPDATE SET id = operating.tasks.id
      RETURNING id, workspace_id, title, idempotency_key, status, priority, planned_start_at, due_at,
        timezone, assignee_id, source, completion_policy, initiative_id, weekly_commitment_id, sort_key,
        assignee_member_id, owner_member_id, execution_mode, function, created_at, updated_at,
        (xmax = 0) AS inserted
    `;
    if (!row) throw APIError.internal("failed to create task");
    const task = rowToTask(row);
    // xmax = 0 is only true for a genuine INSERT — the ON CONFLICT ... DO
    // UPDATE branch (idempotent retry) always bumps xmax even though it
    // writes no new values, so a retried create never re-publishes
    // task.created for the same row. See blueprint §46 / gap analysis
    // Giai đoạn 2 — task.created was defined in shared/events.ts but never
    // published anywhere until this pilot wiring.
    if (row.inserted) {
      await taskEvents.publish(buildTaskCreatedEvent(task));
    }
    return task;
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
