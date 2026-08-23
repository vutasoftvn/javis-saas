import { APIError } from "encore.dev/api";
import { eq, desc, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { getWorkforceMember } from "../../identity/handlers/organization.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { buildTaskCompletedEvent, buildTaskCreatedEvent, taskEvents } from "./task-events.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { tasks } = schema;

export type TaskStatus = "todo" | "in_progress" | "waiting_approval" | "blocked" | "done" | "cancelled";
export const TASK_STATUSES: readonly TaskStatus[] = ["todo", "in_progress", "waiting_approval", "blocked", "done", "cancelled"];

export interface Task {
  id: string;
  workspaceId: string;
  title: string;
  idempotencyKey: string | null;
  status: TaskStatus;
  priority: "low" | "medium" | "high" | "urgent";
  plannedStartAt: string | null;
  dueAt: string | null;
  timezone: string;
  assigneeId: string | null;
  source: string | null;
  completionPolicy: string | null;
  initiativeId: string | null;
  weeklyCommitmentId: string | null;
  sortKey: number | null;
  assigneeMemberId: string | null;
  ownerMemberId: string | null;
  executionMode: "HUMAN" | "AGENT" | "HYBRID" | null;
  function: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskParams {
  workspaceId: string | number;
  title: string;
  priority?: "low" | "medium" | "high" | "urgent";
  dueAt?: string;
  initiativeId?: string | number;
  assigneeMemberId?: string | number;
  ownerMemberId?: string | number;
  executionMode?: "HUMAN" | "AGENT" | "HYBRID";
  function?: string;
  idempotencyKey?: string;
}

function toTask(row: typeof tasks.$inferSelect): Task {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    idempotencyKey: row.idempotencyKey,
    status: row.status as TaskStatus,
    priority: row.priority as Task["priority"],
    plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
    dueAt: row.dueAt ? row.dueAt.toISOString() : null,
    timezone: row.timezone,
    assigneeId: row.assigneeId ? row.assigneeId.toString() : null,
    source: row.source,
    completionPolicy: row.completionPolicy,
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    weeklyCommitmentId: row.weeklyCommitmentId ? row.weeklyCommitmentId.toString() : null,
    sortKey: row.sortKey,
    assigneeMemberId: row.assigneeMemberId ? row.assigneeMemberId.toString() : null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    executionMode: row.executionMode as Task["executionMode"],
    function: row.function,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createTaskService(
  params: CreateTaskParams,
  authorization: string | undefined
): Promise<Task> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
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
      return toTask(existing);
    }
  }

  const [row] = await db
    .insert(tasks)
    .values({
      id: generateSnowflake(),
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

  const task = toTask(row);
  await taskEvents.publish(buildTaskCreatedEvent(task));
  return task;
}

export async function getTaskService(id: string | number, authorization: string | undefined): Promise<Task> {
  const [row] = await db
    .select()
    .from(tasks)
    .where(eq(tasks.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`task ${id} not found`);
  await requireWorkspaceAccess(authorization, row.workspaceId);
  return toTask(row);
}

export async function listTasksService(
  workspaceId: string | number,
  authorization: string | undefined
): Promise<Task[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(tasks)
    .where(eq(tasks.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(tasks.createdAt));

  return rows.map(toTask);
}

export async function updateTaskStatusService(
  id: string | number,
  status: TaskStatus,
  authorization: string | undefined
): Promise<Task> {
  if (!TASK_STATUSES.includes(status)) {
    throw APIError.invalidArgument(`status must be one of ${TASK_STATUSES.join(", ")}`);
  }

  const [existing] = await db
    .select({ workspaceId: tasks.workspaceId })
    .from(tasks)
    .where(eq(tasks.id, BigInt(id)))
    .limit(1);
  if (!existing) throw APIError.notFound(`task ${id} not found`);
  await requireWorkspaceAccess(authorization, existing.workspaceId);

  const [row] = await db
    .update(tasks)
    .set({
      status,
      updatedAt: new Date(),
    })
    .where(eq(tasks.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`task ${id} not found`);
  const task = toTask(row);

  if (task.status === "done") {
    await taskEvents.publish(buildTaskCompletedEvent(task));
  }
  return task;
}
