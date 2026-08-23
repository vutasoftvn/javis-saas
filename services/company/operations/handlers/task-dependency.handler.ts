import { api } from "encore.dev/api";
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

// ─── Task Dependencies Endpoints ───

export const createTaskDependency = api(
  { expose: true, method: "POST", path: "/operations/task-dependencies" },
  async (req: CreateTaskDependencyRequest): Promise<TaskDependency> => {
    return createTaskDependencyService(req);
  }
);

export const listTaskDependencies = api(
  { expose: true, method: "GET", path: "/operations/tasks/:taskId/dependencies" },
  async (params: { taskId: number }): Promise<{ dependencies: TaskDependency[] }> => {
    const dependencies = await listTaskDependenciesService(params.taskId);
    return { dependencies };
  }
);

// ─── Task Schedules Endpoints ───

export const createTaskSchedule = api(
  { expose: true, method: "POST", path: "/operations/task-schedules" },
  async (req: CreateTaskScheduleRequest): Promise<TaskSchedule> => {
    return createTaskScheduleService(req);
  }
);
