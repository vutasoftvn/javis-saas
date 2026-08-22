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
