import { api, APIError } from "encore.dev/api";
import { eq, desc, and, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { getWorkforceMember } from "../../identity/handlers/organization.handler";
import { buildTaskCompletedEvent, buildTaskCreatedEvent, taskEvents } from "../services/task-events.service";

const { tasks } = schema;

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
  idempotencyKey?: string;
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

    if (params.idempotencyKey) {
      const [existing] = await db
        .select()
        .from(tasks)
        .where(
          and(
            eq(tasks.workspaceId, BigInt(params.workspaceId)),
            eq(tasks.idempotencyKey, params.idempotencyKey)
          )
        )
        .limit(1);

      if (existing) {
        return {
          id: Number(existing.id),
          workspaceId: Number(existing.workspaceId),
          title: existing.title,
          idempotencyKey: existing.idempotencyKey,
          status: existing.status as TaskStatus,
          priority: existing.priority as Task["priority"],
          plannedStartAt: existing.plannedStartAt ? existing.plannedStartAt.toISOString() : null,
          dueAt: existing.dueAt ? existing.dueAt.toISOString() : null,
          timezone: existing.timezone,
          assigneeId: existing.assigneeId ? Number(existing.assigneeId) : null,
          source: existing.source,
          completionPolicy: existing.completionPolicy,
          initiativeId: existing.initiativeId ? Number(existing.initiativeId) : null,
          weeklyCommitmentId: existing.weeklyCommitmentId ? Number(existing.weeklyCommitmentId) : null,
          sortKey: existing.sortKey,
          assigneeMemberId: existing.assigneeMemberId ? Number(existing.assigneeMemberId) : null,
          ownerMemberId: existing.ownerMemberId ? Number(existing.ownerMemberId) : null,
          executionMode: existing.executionMode as Task["executionMode"],
          function: existing.function,
          createdAt: existing.createdAt.toISOString(),
          updatedAt: existing.updatedAt.toISOString(),
        };
      }
    }

    const [row] = await db
      .insert(tasks)
      .values({
        workspaceId: BigInt(params.workspaceId),
        title: params.title,
        priority: params.priority || "medium",
        dueAt: params.dueAt ? new Date(params.dueAt) : null,
        initiativeId: params.initiativeId ? BigInt(params.initiativeId) : null,
        assigneeMemberId: params.assigneeMemberId ? BigInt(params.assigneeMemberId) : null,
        ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,
        executionMode: params.executionMode || null,
        function: params.function || null,
        idempotencyKey: params.idempotencyKey || null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create task");

    const task: Task = {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      idempotencyKey: row.idempotencyKey,
      status: row.status as TaskStatus,
      priority: row.priority as Task["priority"],
      plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
      dueAt: row.dueAt ? row.dueAt.toISOString() : null,
      timezone: row.timezone,
      assigneeId: row.assigneeId ? Number(row.assigneeId) : null,
      source: row.source,
      completionPolicy: row.completionPolicy,
      initiativeId: row.initiativeId ? Number(row.initiativeId) : null,
      weeklyCommitmentId: row.weeklyCommitmentId ? Number(row.weeklyCommitmentId) : null,
      sortKey: row.sortKey,
      assigneeMemberId: row.assigneeMemberId ? Number(row.assigneeMemberId) : null,
      ownerMemberId: row.ownerMemberId ? Number(row.ownerMemberId) : null,
      executionMode: row.executionMode as Task["executionMode"],
      function: row.function,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };

    await taskEvents.publish(buildTaskCreatedEvent(task));
    return task;
  }
);

export const getTask = api(
  { method: "GET", path: "/operations/tasks/:id", expose: true },
  async ({ id }: { id: number }): Promise<Task> => {
    const [row] = await db
      .select()
      .from(tasks)
      .where(eq(tasks.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`task ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      idempotencyKey: row.idempotencyKey,
      status: row.status as TaskStatus,
      priority: row.priority as Task["priority"],
      plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
      dueAt: row.dueAt ? row.dueAt.toISOString() : null,
      timezone: row.timezone,
      assigneeId: row.assigneeId ? Number(row.assigneeId) : null,
      source: row.source,
      completionPolicy: row.completionPolicy,
      initiativeId: row.initiativeId ? Number(row.initiativeId) : null,
      weeklyCommitmentId: row.weeklyCommitmentId ? Number(row.weeklyCommitmentId) : null,
      sortKey: row.sortKey,
      assigneeMemberId: row.assigneeMemberId ? Number(row.assigneeMemberId) : null,
      ownerMemberId: row.ownerMemberId ? Number(row.ownerMemberId) : null,
      executionMode: row.executionMode as Task["executionMode"],
      function: row.function,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listTasks = api(
  { method: "GET", path: "/operations/tasks", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ tasks: Task[] }> => {
    const rows = await db
      .select()
      .from(tasks)
      .where(eq(tasks.workspaceId, BigInt(workspaceId)))
      .orderBy(desc(tasks.createdAt));

    return {
      tasks: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        title: row.title,
        idempotencyKey: row.idempotencyKey,
        status: row.status as TaskStatus,
        priority: row.priority as Task["priority"],
        plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
        dueAt: row.dueAt ? row.dueAt.toISOString() : null,
        timezone: row.timezone,
        assigneeId: row.assigneeId ? Number(row.assigneeId) : null,
        source: row.source,
        completionPolicy: row.completionPolicy,
        initiativeId: row.initiativeId ? Number(row.initiativeId) : null,
        weeklyCommitmentId: row.weeklyCommitmentId ? Number(row.weeklyCommitmentId) : null,
        sortKey: row.sortKey,
        assigneeMemberId: row.assigneeMemberId ? Number(row.assigneeMemberId) : null,
        ownerMemberId: row.ownerMemberId ? Number(row.ownerMemberId) : null,
        executionMode: row.executionMode as Task["executionMode"],
        function: row.function,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateTaskStatus = api(
  { method: "POST", path: "/operations/tasks/:id/status", expose: true },
  async ({ id, status }: { id: number; status: TaskStatus }): Promise<Task> => {
    if (!TASK_STATUSES.includes(status)) {
      throw APIError.invalidArgument(`status must be one of ${TASK_STATUSES.join(", ")}`);
    }

    const [row] = await db
      .update(tasks)
      .set({
        status,
        updatedAt: new Date(),
      })
      .where(eq(tasks.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`task ${id} not found`);
    const task: Task = {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      idempotencyKey: row.idempotencyKey,
      status: row.status as TaskStatus,
      priority: row.priority as Task["priority"],
      plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
      dueAt: row.dueAt ? row.dueAt.toISOString() : null,
      timezone: row.timezone,
      assigneeId: row.assigneeId ? Number(row.assigneeId) : null,
      source: row.source,
      completionPolicy: row.completionPolicy,
      initiativeId: row.initiativeId ? Number(row.initiativeId) : null,
      weeklyCommitmentId: row.weeklyCommitmentId ? Number(row.weeklyCommitmentId) : null,
      sortKey: row.sortKey,
      assigneeMemberId: row.assigneeMemberId ? Number(row.assigneeMemberId) : null,
      ownerMemberId: row.ownerMemberId ? Number(row.ownerMemberId) : null,
      executionMode: row.executionMode as Task["executionMode"],
      function: row.function,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };

    if (task.status === "done") {
      await taskEvents.publish(buildTaskCompletedEvent(task));
    }
    return task;
  }
);
