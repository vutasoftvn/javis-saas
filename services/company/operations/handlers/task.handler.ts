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
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { linkTaskProjects, listTaskProjects, unlinkTaskProject } from "../services/project-link.service";

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
  async ({ id, authorization }: { id: string; authorization?: Header<"Authorization"> }): Promise<Task> => {
    return getTaskService(id, authorization);
  }
);

export const listTasks = api(
  { method: "GET", path: "/operations/tasks", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: string;
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
    id: string;
    status: TaskStatus;
    authorization?: Header<"Authorization">;
  }): Promise<Task> => {
    return updateTaskStatusService(id, status, authorization);
  }
);

export interface LinkProjectsParams {
  projectIds: string[];
}

export interface TaskProjectsResponse {
  projectIds: string[];
}

export const linkTaskProjects_Endpoint = api(
  { method: "POST", path: "/operations/tasks/:id/projects", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
    projectIds,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectIds: string[];
  }): Promise<TaskProjectsResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    await linkTaskProjects(ctx, id, projectIds);
    const projectIdsList = await listTaskProjects(ctx, id);
    return { projectIds: projectIdsList };
  }
);

export const getTaskProjects = api(
  { method: "GET", path: "/operations/tasks/:id/projects", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<TaskProjectsResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const projectIds = await listTaskProjects(ctx, id);
    return { projectIds };
  }
);

export interface DeleteProjectResponse {
  success: boolean;
}

export const unlinkTaskProject_Endpoint = api(
  { method: "DELETE", path: "/operations/tasks/:id/projects/:projectId", expose: true },
  async ({
    id,
    projectId,
    workspaceId,
    authorization,
  }: {
    id: string;
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<DeleteProjectResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    await unlinkTaskProject(ctx, id, projectId);
    return { success: true };
  }
);
