import { APIError } from "encore.dev/api";
import { eq, or, asc, and, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { taskDependencies, taskSchedules, tasks } = schema;

// M1 §4 — mọi task id trong request phải thuộc workspace của caller.
async function assertTasksInWorkspace(taskIds: bigint[], workspaceId: bigint): Promise<void> {
  const unique = [...new Set(taskIds.map((t) => t.toString()))].map((s) => BigInt(s));
  const rows = await db
    .select({ id: tasks.id })
    .from(tasks)
    .where(and(inArray(tasks.id, unique), eq(tasks.workspaceId, workspaceId)));
  if (rows.length !== unique.length) {
    throw APIError.notFound("One or more referenced tasks are not in this workspace");
  }
}

export interface TaskDependency {
  id: string;
  taskId: string;
  dependsOnTaskId: string;
  dependencyType: string;
  status: string;
  createdAt: string;
}

export interface CreateTaskDependencyRequest {
  taskId: string | number;
  dependsOnTaskId: string | number;
  dependencyType?: string;
  workspaceId: string;
  authorization?: string;
}

export interface TaskSchedule {
  id: string;
  taskId: string;
  scheduleType: string;
  cronExpr?: string | null;
  nextRunAt?: string | null;
  active: boolean;
  createdAt: string;
}

export interface CreateTaskScheduleRequest {
  taskId: string | number;
  scheduleType: string;
  cronExpr?: string | null;
  nextRunAt?: string | null;
  active?: boolean;
  workspaceId: string;
  authorization?: string;
}

function toTaskDependency(row: typeof taskDependencies.$inferSelect): TaskDependency {
  return {
    id: row.id.toString(),
    taskId: row.taskId.toString(),
    dependsOnTaskId: row.dependsOnTaskId.toString(),
    dependencyType: row.dependencyType || "BLOCKS",
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createTaskDependencyService(req: CreateTaskDependencyRequest): Promise<TaskDependency> {
  if (!req.taskId || !req.dependsOnTaskId) {
    throw APIError.invalidArgument("taskId and dependsOnTaskId are required");
  }
  if (BigInt(req.taskId) === BigInt(req.dependsOnTaskId)) {
    throw APIError.invalidArgument("A task cannot depend on itself");
  }

  const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
  await assertTasksInWorkspace(
    [BigInt(req.taskId), BigInt(req.dependsOnTaskId)],
    BigInt(ctx.workspaceId)
  );

  const [row] = await db
    .insert(taskDependencies)
    .values({
      id: generateSnowflake(),
      taskId: BigInt(req.taskId),
      dependsOnTaskId: BigInt(req.dependsOnTaskId),
      dependencyType: req.dependencyType || "BLOCKS",
      status: "PENDING",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create task dependency");
  return toTaskDependency(row);
}

export async function listTaskDependenciesService(taskId: string | number): Promise<TaskDependency[]> {
  const targetId = BigInt(taskId);
  const rows = await db
    .select()
    .from(taskDependencies)
    .where(or(eq(taskDependencies.taskId, targetId), eq(taskDependencies.dependsOnTaskId, targetId)))
    .orderBy(asc(taskDependencies.id));

  return rows.map(toTaskDependency);
}

export async function createTaskScheduleService(req: CreateTaskScheduleRequest): Promise<TaskSchedule> {
  if (!req.taskId || !req.scheduleType) {
    throw APIError.invalidArgument("taskId and scheduleType are required");
  }

  const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
  await assertTasksInWorkspace([BigInt(req.taskId)], BigInt(ctx.workspaceId));

  const [row] = await db
    .insert(taskSchedules)
    .values({
      id: generateSnowflake(),
      taskId: BigInt(req.taskId),
      scheduleType: req.scheduleType,
      cronExpr: req.cronExpr || null,
      nextRunAt: req.nextRunAt ? new Date(req.nextRunAt) : null,
      active: req.active ?? true,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create task schedule");
  return {
    id: row.id.toString(),
    taskId: row.taskId.toString(),
    scheduleType: row.scheduleType,
    cronExpr: row.cronExpr,
    nextRunAt: row.nextRunAt ? row.nextRunAt.toISOString() : null,
    active: row.active,
    createdAt: row.createdAt.toISOString(),
  };
}
