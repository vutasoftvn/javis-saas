import { api, APIError } from "encore.dev/api";
import { eq, or, asc } from "drizzle-orm";
import { db, schema } from "../models/db";

const { taskDependencies, taskSchedules } = schema;

export interface TaskDependency {
  id: number;
  taskId: number;
  dependsOnTaskId: number;
  dependencyType: string;
  status: string;
  createdAt: string;
}

export interface CreateTaskDependencyRequest {
  taskId: number;
  dependsOnTaskId: number;
  dependencyType?: string;
}

export interface TaskSchedule {
  id: number;
  taskId: number;
  scheduleType: string;
  cronExpr?: string | null;
  nextRunAt?: string | null;
  active: boolean;
  createdAt: string;
}

export interface CreateTaskScheduleRequest {
  taskId: number;
  scheduleType: string;
  cronExpr?: string | null;
  nextRunAt?: string | null;
  active?: boolean;
}

// ─── Task Dependencies Endpoints ───

export const createTaskDependency = api(
  { expose: true, method: "POST", path: "/operations/task-dependencies" },
  async (req: CreateTaskDependencyRequest): Promise<TaskDependency> => {
    if (!req.taskId || !req.dependsOnTaskId) {
      throw APIError.invalidArgument("taskId and dependsOnTaskId are required");
    }
    if (req.taskId === req.dependsOnTaskId) {
      throw APIError.invalidArgument("A task cannot depend on itself");
    }

    const [row] = await db
      .insert(taskDependencies)
      .values({
        taskId: BigInt(req.taskId),
        dependsOnTaskId: BigInt(req.dependsOnTaskId),
        dependencyType: req.dependencyType || "BLOCKS",
        status: "PENDING",
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create task dependency");
    return {
      id: Number(row.id),
      taskId: Number(row.taskId),
      dependsOnTaskId: Number(row.dependsOnTaskId),
      dependencyType: row.dependencyType || "BLOCKS",
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const listTaskDependencies = api(
  { expose: true, method: "GET", path: "/operations/tasks/:taskId/dependencies" },
  async (params: { taskId: number }): Promise<{ dependencies: TaskDependency[] }> => {
    const targetId = BigInt(params.taskId);
    const rows = await db
      .select()
      .from(taskDependencies)
      .where(or(eq(taskDependencies.taskId, targetId), eq(taskDependencies.dependsOnTaskId, targetId)))
      .orderBy(asc(taskDependencies.id));

    return {
      dependencies: rows.map((row) => ({
        id: Number(row.id),
        taskId: Number(row.taskId),
        dependsOnTaskId: Number(row.dependsOnTaskId),
        dependencyType: row.dependencyType || "BLOCKS",
        status: row.status,
        createdAt: row.createdAt.toISOString(),
      })),
    };
  }
);

// ─── Task Schedules Endpoints ───

export const createTaskSchedule = api(
  { expose: true, method: "POST", path: "/operations/task-schedules" },
  async (req: CreateTaskScheduleRequest): Promise<TaskSchedule> => {
    if (!req.taskId || !req.scheduleType) {
      throw APIError.invalidArgument("taskId and scheduleType are required");
    }

    const [row] = await db
      .insert(taskSchedules)
      .values({
        taskId: BigInt(req.taskId),
        scheduleType: req.scheduleType,
        cronExpr: req.cronExpr || null,
        nextRunAt: req.nextRunAt ? new Date(req.nextRunAt) : null,
        active: req.active ?? true,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create task schedule");
    return {
      id: Number(row.id),
      taskId: Number(row.taskId),
      scheduleType: row.scheduleType,
      cronExpr: row.cronExpr,
      nextRunAt: row.nextRunAt ? row.nextRunAt.toISOString() : null,
      active: row.active,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
