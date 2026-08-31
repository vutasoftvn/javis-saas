import { api, Header } from "encore.dev/api";
import {
  OkrCycle,
  CreateOkrCycleParams,
  Objective,
  CreateObjectiveParams,
  KeyResult,
  AddKeyResultParams,
  ObjectiveProgress,
  createOkrCycleService,
  createObjectiveService,
  addKeyResultService,
  checkinService,
  getObjectiveService,
  getObjectiveProgressService,
  listOkrCyclesService,
  listObjectivesService,
  deleteObjectiveService,
} from "../services/okr.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { linkObjectiveProjects, listObjectiveProjects, unlinkObjectiveProject } from "../services/project-link.service";

export { OkrCycle, CreateOkrCycleParams, Objective, CreateObjectiveParams, KeyResult, AddKeyResultParams };

// M1 §4 — các endpoint OKR create/checkin trước đây không xác thực caller.
type WithAuth<T> = Omit<T, "authorization"> & { authorization?: Header<"Authorization"> };

export const createOkrCycle = api(
  { method: "POST", path: "/operations/okr-cycles", expose: true },
  async (params: WithAuth<CreateOkrCycleParams>): Promise<OkrCycle> => {
    return createOkrCycleService(params);
  }
);

export const createObjective = api(
  { method: "POST", path: "/operations/objectives", expose: true },
  async (params: WithAuth<CreateObjectiveParams>): Promise<Objective> => {
    return createObjectiveService(params);
  }
);

export const addKeyResult = api(
  { method: "POST", path: "/operations/objectives/:objectiveId/key-results", expose: true },
  async (params: WithAuth<AddKeyResultParams>): Promise<KeyResult> => {
    return addKeyResultService(params);
  }
);

export const checkin = api(
  { method: "POST", path: "/operations/key-results/:id/checkin", expose: true },
  async ({
    id,
    value,
    authorization,
  }: {
    id: string;
    value: number;
    authorization?: Header<"Authorization">;
  }): Promise<KeyResult> => {
    return checkinService(id, value, authorization);
  }
);

export const getObjective = api(
  { method: "GET", path: "/operations/objectives/:id", expose: true },
  async ({ id, authorization }: { id: string; authorization?: Header<"Authorization"> }): Promise<Objective> => {
    return getObjectiveService(id, authorization);
  }
);

export const listOkrCycles = api(
  { method: "GET", path: "/operations/okr-cycles", expose: true },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }) => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listOkrCyclesService(ctx);
  }
);

export const listObjectives = api(
  { method: "GET", path: "/operations/objectives", expose: true },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }) => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listObjectivesService(ctx);
  }
);

export const deleteObjective = api(
  { method: "DELETE", path: "/operations/objectives/:id", expose: true },
  async ({
    id,
    authorization,
    workspaceId,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    await deleteObjectiveService(ctx, id);
    return { success: true };
  }
);

export const getObjectiveProgress = api(
  { method: "GET", path: "/operations/objectives/:id/progress", expose: true },
  async ({
    id,
    authorization,
    workspaceId,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    workspaceId?: Header<"X-Workspace-Id">;
  }): Promise<ObjectiveProgress> => {
    const ctx = workspaceId ? await requireWorkspaceAccess(authorization, workspaceId) : undefined;
    return getObjectiveProgressService(id, ctx);
  }
);


export interface ObjectiveProjectsResponse {
  projectIds: string[];
}

export const linkObjectiveProjects_Endpoint = api(
  { method: "POST", path: "/operations/objectives/:id/projects", expose: true },
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
  }): Promise<ObjectiveProjectsResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    await linkObjectiveProjects(ctx, id, projectIds);
    const projectIdsList = await listObjectiveProjects(ctx, id);
    return { projectIds: projectIdsList };
  }
);

export const getObjectiveProjects = api(
  { method: "GET", path: "/operations/objectives/:id/projects", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<ObjectiveProjectsResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const projectIds = await listObjectiveProjects(ctx, id);
    return { projectIds };
  }
);

export interface ObjectiveDeleteProjectResponse {
  success: boolean;
}

export const unlinkObjectiveProject_Endpoint = api(
  { method: "DELETE", path: "/operations/objectives/:id/projects/:projectId", expose: true },
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
  }): Promise<ObjectiveDeleteProjectResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    await unlinkObjectiveProject(ctx, id, projectId);
    return { success: true };
  }
);
