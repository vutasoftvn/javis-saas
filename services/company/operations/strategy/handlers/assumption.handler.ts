import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  Assumption,
  CreateAssumptionInput,
  ListAssumptionsInput,
  UpdateAssumptionInput,
  createAssumptionInWorkspace,
  getAssumptionInWorkspace,
  listAssumptionsInWorkspace,
  updateAssumptionInWorkspace,
  deleteAssumptionInWorkspace,
  getRankedAssumptionsByProjectInWorkspace,
} from "../services/assumption.service";

export type { Assumption };

export interface CreateAssumptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  statement: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export interface ListAssumptionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  status?: string;
}

export interface UpdateAssumptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  statement?: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export const createAssumption = api(
  { method: "POST", path: "/operations/strategy/assumptions", expose: true },
  async (params: CreateAssumptionParams): Promise<Assumption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createAssumptionInWorkspace(ctx, params);
  }
);

export const getAssumption = api(
  { method: "GET", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Assumption> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getAssumptionInWorkspace(ctx, id);
  }
);

export const listAssumptions = api(
  { method: "GET", path: "/operations/strategy/assumptions", expose: true },
  async (params: ListAssumptionsParams): Promise<{ items: Assumption[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listAssumptionsInWorkspace(ctx, params);
  }
);

export const updateAssumption = api(
  { method: "PATCH", path: "/operations/strategy/assumptions/:id", expose: true },
  async (params: UpdateAssumptionParams): Promise<Assumption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateAssumptionInWorkspace(ctx, params.id, params);
  }
);

export const deleteAssumption = api(
  { method: "DELETE", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteAssumptionInWorkspace(ctx, id);
  }
);

export const getRankedAssumptionsByProject = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/ranked-assumptions", expose: true },
  async ({ authorization, workspaceId, projectId }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; projectId: string }) => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getRankedAssumptionsByProjectInWorkspace(ctx, projectId);
  }
);
