import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  Experiment,
  CreateExperimentInput,
  ListExperimentsInput,
  UpdateExperimentInput,
  createExperimentInWorkspace,
  getExperimentInWorkspace,
  listExperimentsInWorkspace,
  updateExperimentInWorkspace,
  deleteExperimentInWorkspace,
  proposeExperimentsInWorkspace,
} from "../services/experiment-proposal.service";

export type { Experiment };

export interface CreateExperimentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  assumptionId?: string | number;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget?: number;
  ownerMemberId?: string | number;
  status?: string;
}

export interface ListExperimentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  status?: string;
}

export interface UpdateExperimentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  hypothesis?: string;
  method?: string;
  successCriteria?: string;
  budget?: number;
  ownerMemberId?: string | number;
  status?: string;
}

export const createExperiment = api(
  { method: "POST", path: "/operations/strategy/experiments", expose: true },
  async (params: CreateExperimentParams): Promise<Experiment> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createExperimentInWorkspace(ctx, params);
  }
);

export const getExperiment = api(
  { method: "GET", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Experiment> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getExperimentInWorkspace(ctx, id);
  }
);

export const listExperiments = api(
  { method: "GET", path: "/operations/strategy/experiments", expose: true },
  async (params: ListExperimentsParams): Promise<{ items: Experiment[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listExperimentsInWorkspace(ctx, params);
  }
);

export const updateExperiment = api(
  { method: "PATCH", path: "/operations/strategy/experiments/:id", expose: true },
  async (params: UpdateExperimentParams): Promise<Experiment> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateExperimentInWorkspace(ctx, params.id, params);
  }
);

export const deleteExperiment = api(
  { method: "DELETE", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteExperimentInWorkspace(ctx, id);
  }
);

export const proposeExperiments = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/proposed-experiments", expose: true },
  async ({ authorization, workspaceId, projectId }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; projectId: string }) => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return proposeExperimentsInWorkspace(ctx, projectId);
  }
);
