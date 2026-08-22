import { api, APIError } from "encore.dev/api";
import { SQLDatabase } from "encore.dev/storage/sqldb";

const db = SQLDatabase.named("operations");

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

    const row = await db.queryRow<TaskDependency>`
      INSERT INTO operating.task_dependencies (
        task_id, depends_on_task_id, dependency_type, status
      ) VALUES (
        ${req.taskId}, ${req.dependsOnTaskId},
        ${req.dependencyType ?? "BLOCKS"}, 'PENDING'
      )
      RETURNING
        id, task_id as "taskId", depends_on_task_id as "dependsOnTaskId",
        dependency_type as "dependencyType", status, created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create task dependency");
    return row;
  }
);

export const listTaskDependencies = api(
  { expose: true, method: "GET", path: "/operations/tasks/:taskId/dependencies" },
  async (params: { taskId: number }): Promise<{ dependencies: TaskDependency[] }> => {
    const rows = db.query<TaskDependency>`
      SELECT
        id, task_id as "taskId", depends_on_task_id as "dependsOnTaskId",
        dependency_type as "dependencyType", status, created_at as "createdAt"
      FROM operating.task_dependencies
      WHERE task_id = ${params.taskId} OR depends_on_task_id = ${params.taskId}
      ORDER BY id ASC
    `;
    const dependencies: TaskDependency[] = [];
    for await (const row of rows) dependencies.push(row);
    return { dependencies };
  }
);

// ─── Task Schedules Endpoints ───

export const createTaskSchedule = api(
  { expose: true, method: "POST", path: "/operations/task-schedules" },
  async (req: CreateTaskScheduleRequest): Promise<TaskSchedule> => {
    if (!req.taskId || !req.scheduleType) {
      throw APIError.invalidArgument("taskId and scheduleType are required");
    }

    const row = await db.queryRow<TaskSchedule>`
      INSERT INTO operating.task_schedules (
        task_id, schedule_type, cron_expr, next_run_at, active
      ) VALUES (
        ${req.taskId}, ${req.scheduleType}, ${req.cronExpr ?? null},
        ${req.nextRunAt ?? null}, ${req.active ?? true}
      )
      RETURNING
        id, task_id as "taskId", schedule_type as "scheduleType",
        cron_expr as "cronExpr", next_run_at as "nextRunAt",
        active, created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create task schedule");
    return row;
  }
);
