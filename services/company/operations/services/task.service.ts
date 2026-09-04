import { APIError } from "encore.dev/api";
import { eq, desc, and, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { getWorkforceMember } from "../../identity/handlers/workforce.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { buildTaskCompletedEvent, buildTaskCreatedEvent, EventContext } from "./task-events.service";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

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
  source: string | null;
  completionPolicy: string | null;
  initiativeId: string | null;
  weeklyCommitmentId: string | null;
  sortKey: number | null;
  assigneeMemberId: string | null;
  ownerMemberId: string | null;
  executionMode: "HUMAN" | "AGENT" | "HYBRID" | null;
  function: string | null;
  projectIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskParams {
  workspaceId: string;
  title: string;
  priority?: "low" | "medium" | "high" | "urgent";
  dueAt?: string;
  initiativeId?: string;
  assigneeMemberId?: string;
  ownerMemberId?: string;
  executionMode?: "HUMAN" | "AGENT" | "HYBRID";
  function?: string;
  idempotencyKey?: string;
  correlationId?: string;
  actor?: { kind: "user" | "agent" | "system"; id: string };
}

function toTask(row: typeof tasks.$inferSelect, projectIds: string[] = []): Task {
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
    source: row.source,
    completionPolicy: row.completionPolicy,
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    weeklyCommitmentId: row.weeklyCommitmentId ? row.weeklyCommitmentId.toString() : null,
    sortKey: row.sortKey,
    assigneeMemberId: row.assigneeMemberId ? row.assigneeMemberId.toString() : null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    executionMode: row.executionMode as Task["executionMode"],
    function: row.function,
    projectIds,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createTaskService(
  params: CreateTaskParams,
  authorization: string | undefined
): Promise<Task> {
  const authCtx = await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });
  if (params.assigneeMemberId !== undefined) {
    await getWorkforceMember({
      id: params.assigneeMemberId,
      workspaceId: params.workspaceId,
      authorization,
    });
  }
  if (params.ownerMemberId !== undefined) {
    await getWorkforceMember({
      id: params.ownerMemberId,
      workspaceId: params.workspaceId,
      authorization,
    });
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

  const actor = params.actor || (authCtx.userId ? { kind: "user" as const, id: authCtx.userId } : { kind: "system" as const, id: "operations" });
  const eventCtx: EventContext = {
    correlationId: params.correlationId,
    actor,
  };

  const task = await db.transaction(async (tx) => {
    const [row] = await tx
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

    const t = toTask(row);
    await appendOutboxEvent(tx, buildTaskCreatedEvent(t, eventCtx));
    return t;
  });

  return task;
}

export async function getTaskService(id: string, ctx: TenantContext): Promise<Task> {
  const [row] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`task ${id} not found`);

  // Populate projectIds from link table
  const { listTaskProjects } = await import("./project-link.service");
  const projectIds = await listTaskProjects(ctx, id);

  return toTask(row, projectIds);
}

export async function listTasksService(
  workspaceId: string,
  authorization: string | undefined
): Promise<Task[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.workspaceId, BigInt(workspaceId)), isNull(tasks.deletedAt)))
    .orderBy(desc(tasks.createdAt));

  return rows.map((row) => toTask(row));
}

export async function updateTaskStatusService(
  id: string,
  status: TaskStatus,
  ctx: TenantContext,
  eventCtx?: EventContext
): Promise<Task> {
  if (!TASK_STATUSES.includes(status)) {
    throw APIError.invalidArgument(`status must be one of ${TASK_STATUSES.join(", ")}`);
  }

  const actor = eventCtx?.actor || (ctx.userId ? { kind: "user" as const, id: ctx.userId } : { kind: "system" as const, id: "operations" });
  const finalEventCtx: EventContext = {
    correlationId: eventCtx?.correlationId,
    actor,
  };

  const task = await db.transaction(async (tx) => {
    const [row] = await tx
      .update(tasks)
      .set({
        status,
        updatedAt: new Date(),
      })
      .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
      .returning();

    if (!row) throw APIError.notFound(`task ${id} not found`);
    const t = toTask(row);

    if (status === "done") {
      await appendOutboxEvent(tx, buildTaskCompletedEvent(t, finalEventCtx));
    }
    return t;
  });

  return task;
}

export async function updateTaskScheduleService(
  id: string,
  plannedStartAt: string | null,
  ctx: TenantContext
): Promise<Task> {
  let parsedPlannedStartAt: Date | null = null;
  if (plannedStartAt !== null && plannedStartAt !== undefined) {
    parsedPlannedStartAt = new Date(plannedStartAt);
    if (Number.isNaN(parsedPlannedStartAt.getTime())) {
      throw APIError.invalidArgument("plannedStartAt phải là ISO date hợp lệ");
    }
  }

  const [row] = await db
    .update(tasks)
    .set({ plannedStartAt: parsedPlannedStartAt, updatedAt: new Date() })
    .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
    .returning();

  if (!row) throw APIError.notFound(`task ${id} not found`);
  return toTask(row);
}
