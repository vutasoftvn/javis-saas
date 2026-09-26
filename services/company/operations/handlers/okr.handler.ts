import { api, Header } from "encore.dev/api";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
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
  listKeyResultsService,
  deleteObjectiveService,
  publishObjectiveService,
  PublishObjectiveParams,
  UpdateObjectiveParams,
  UpdateKeyResultParams,
  DeleteKeyResultParams,
  updateObjectiveService,
  updateKeyResultService,
  deleteKeyResultService,
} from "../services/okr.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export {
  OkrCycle,
  CreateOkrCycleParams,
  Objective,
  CreateObjectiveParams,
  KeyResult,
  AddKeyResultParams,
  PublishObjectiveParams,
  UpdateObjectiveParams,
  UpdateKeyResultParams,
  DeleteKeyResultParams,
};


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

export const updateObjective = api(
  { method: "PUT", path: "/operations/objectives/:id", expose: true },
  async (params: WithAuth<UpdateObjectiveParams>): Promise<Objective> => {
    return updateObjectiveService(params);
  },
);

export const updateKeyResult = api(
  { method: "PUT", path: "/operations/key-results/:id", expose: true },
  async (params: WithAuth<UpdateKeyResultParams>): Promise<KeyResult> => {
    return updateKeyResultService(params);
  },
);

export const deleteKeyResult = api(
  { method: "DELETE", path: "/operations/key-results/:id", expose: true },
  async (params: WithAuth<DeleteKeyResultParams>): Promise<{ success: boolean }> => {
    await deleteKeyResultService(params);
    return { success: true };
  },
);

export const listOkrCycles = api(
  { method: "GET", path: "/operations/okr-cycles", expose: true },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }): Promise<MvpSuccess<readonly OkrCycle[]>> => {
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
  }): Promise<MvpSuccess<readonly Objective[]>> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listObjectivesService(ctx);
  }
);

export const listKeyResults = api(
  { method: "GET", path: "/operations/key-results", expose: true },
  async ({
    authorization,
    workspaceId,
  }: {
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }): Promise<MvpSuccess<readonly KeyResult[]>> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return listKeyResultsService(ctx);
  },
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


export const publishObjective = api(
  { method: "POST", path: "/operations/objectives/:id/publish", expose: true },
  async ({
    id,
    authorization,
    workspaceId,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
  }): Promise<Objective> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return publishObjectiveService({ id }, ctx);
  }
);
