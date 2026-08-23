import { api, Header } from "encore.dev/api";
import {
  Task,
  TaskStatus,
  TASK_STATUSES,
  CreateTaskParams as BaseCreateTaskParams,
  createTaskService,
  getTaskService,
  listTasksService,
  updateTaskStatusService,
} from "../services/task.service";

export { Task, TaskStatus, TASK_STATUSES };

export interface CreateTaskParams extends BaseCreateTaskParams {
  authorization?: Header<"Authorization">;
}

export const createTask = api(
  { method: "POST", path: "/operations/tasks", expose: true },
  async (params: CreateTaskParams): Promise<Task> => {
    return createTaskService(params, params.authorization);
  }
);

export const getTask = api(
  { method: "GET", path: "/operations/tasks/:id", expose: true },
  async ({ id, authorization }: { id: number; authorization?: Header<"Authorization"> }): Promise<Task> => {
    return getTaskService(id, authorization);
  }
);

export const listTasks = api(
  { method: "GET", path: "/operations/tasks", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: number;
    authorization?: Header<"Authorization">;
  }): Promise<{ tasks: Task[] }> => {
    const tasks = await listTasksService(workspaceId, authorization);
    return { tasks };
  }
);

export const updateTaskStatus = api(
  { method: "POST", path: "/operations/tasks/:id/status", expose: true },
  async ({
    id,
    status,
    authorization,
  }: {
    id: number;
    status: TaskStatus;
    authorization?: Header<"Authorization">;
  }): Promise<Task> => {
    return updateTaskStatusService(id, status, authorization);
  }
);
