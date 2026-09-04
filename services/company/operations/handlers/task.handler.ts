import { api, APIError, Header } from "encore.dev/api";
import {
  Task,
  TaskStatus,
  TASK_STATUSES,
  CreateTaskParams as BaseCreateTaskParams,
  AgentAdvanceStatus,
  createTaskService,
  getTaskService,
  listTasksService,
  updateTaskStatusService,
  updateTaskScheduleService,
  advanceTaskByAgentService,
  listAgentClaimableTasksService,
  AgentClaimableTask,
  getWorkspaceExecutionSettingsService,
  setWorkspaceExecutionSettingsService,
  WorkspaceExecutionSettingsView,
} from "../services/task.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  resolveCosaTaskContext,
  WGA_CAP_TASK_ADVANCE,
  WGA_CAP_TASK_LIST,
} from "../../shared/auth/cosa-task-delegation";
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
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Task> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getTaskService(id, ctx);
  }
);

export const listTasks = api(
  { method: "GET", path: "/operations/tasks", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<{ tasks: Task[] }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const tasks = await listTasksService(ctx.workspaceId, authorization);
    return { tasks };
  }
);


export const updateTaskStatus = api(
  { method: "POST", path: "/operations/tasks/:id/status", expose: true },
  async ({
    id,
    status,
    workspaceId,
    authorization,
  }: {
    id: string;
    status: TaskStatus;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Task> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateTaskStatusService(id, status, ctx);
  }
);

export const updateTaskSchedule = api(
  { method: "POST", path: "/operations/tasks/:id/schedule", expose: true },
  async ({
    id,
    plannedStartAt,
    workspaceId,
    authorization,
  }: {
    id: string;
    plannedStartAt: string | null;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Task> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateTaskScheduleService(id, plannedStartAt, ctx);
  }
);

// Gọi bởi background run của apps/cosa (workspace_task_sweep / task_execution) —
// xác thực bằng cosa company-delegation token khớp run_id + capability.
export const advanceTask = api(
  { method: "POST", path: "/operations/tasks/:id/advance", expose: true },
  async ({
    id,
    toStatus,
    runId,
    note,
    workspaceId,
    authorization,
  }: {
    id: string;
    toStatus: AgentAdvanceStatus;
    runId: string;
    note?: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<Task> => {
    if (!runId || !runId.trim()) throw APIError.invalidArgument("runId required");
    const ctx = resolveCosaTaskContext(authorization, {
      workspaceId,
      capabilityId: WGA_CAP_TASK_ADVANCE,
      runId,
    });
    return advanceTaskByAgentService({ taskId: id, toStatus, runId, note }, ctx);
  }
);

// Gọi bởi workspace_task_sweep của apps/cosa — cosa delegation (workspace + cap,
// không khớp run_id vì sweep không phải 1 run cụ thể).
export const listAgentClaimableTasks = api(
  { method: "GET", path: "/operations/tasks/agent-claimable", expose: true },
  async ({
    workspaceId,
    limit,
    authorization,
  }: {
    workspaceId: Header<"X-Workspace-Id">;
    limit?: number;
    authorization?: Header<"Authorization">;
  }): Promise<{ tasks: AgentClaimableTask[] }> => {
    const ctx = resolveCosaTaskContext(authorization, {
      workspaceId,
      capabilityId: WGA_CAP_TASK_LIST,
    });
    const tasks = await listAgentClaimableTasksService(
      workspaceId,
      limit ?? 5,
      authorization,
      ctx
    );
    return { tasks };
  }
);

// WGA #2 — kill-switch per-workspace cho vòng thực thi tự động.
export const getExecutionSettings = api(
  { method: "GET", path: "/operations/execution-settings", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<WorkspaceExecutionSettingsView> => {
    return getWorkspaceExecutionSettingsService(workspaceId, authorization);
  }
);

export const setExecutionSettings = api(
  { method: "POST", path: "/operations/execution-settings", expose: true },
  async ({
    sweepEnabled,
    workspaceId,
    authorization,
  }: {
    sweepEnabled: boolean;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<WorkspaceExecutionSettingsView> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return setWorkspaceExecutionSettingsService(workspaceId, sweepEnabled, ctx);
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
