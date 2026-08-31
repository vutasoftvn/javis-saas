import { api, Header } from "encore.dev/api";
import {
  TaskDependency,
  CreateTaskDependencyRequest,
  TaskSchedule,
  CreateTaskScheduleRequest,
  createTaskDependencyService,
  listTaskDependenciesService,
  createTaskScheduleService,
} from "../services/task-dependency.service";

export { TaskDependency, CreateTaskDependencyRequest, TaskSchedule, CreateTaskScheduleRequest };

type WithAuthHeaders<T> = Omit<T, "authorization" | "workspaceId"> & {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
};

// ─── Task Dependencies Endpoints ───

export const createTaskDependency = api(
  { expose: true, method: "POST", path: "/operations/task-dependencies" },
  async (req: WithAuthHeaders<CreateTaskDependencyRequest>): Promise<TaskDependency> => {
    return createTaskDependencyService(req);
  }
);

export const listTaskDependencies = api(
  { expose: true, method: "GET", path: "/operations/tasks/:taskId/dependencies" },
  async (params: WithAuthHeaders<{ taskId: string }>): Promise<{ dependencies: TaskDependency[] }> => {
    const dependencies = await listTaskDependenciesService(params.taskId, params.workspaceId, params.authorization);
    return { dependencies };
  }
);

// ─── Task Schedules Endpoints ───

export const createTaskSchedule = api(
  { expose: true, method: "POST", path: "/operations/task-schedules" },
  async (req: WithAuthHeaders<CreateTaskScheduleRequest>): Promise<TaskSchedule> => {
    return createTaskScheduleService(req);
  }
);
