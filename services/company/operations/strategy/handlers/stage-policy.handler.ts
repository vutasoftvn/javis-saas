import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  StagePolicy,
  CreateStagePolicyInput,
  ListStagePoliciesInput,
  UpdateStagePolicyInput,
  createStagePolicyInWorkspace,
  getStagePolicyInWorkspace,
  listStagePoliciesInWorkspace,
  updateStagePolicyInWorkspace,
  deleteStagePolicyInWorkspace,
} from "../services/stage-policy.service";

export type { StagePolicy };

export interface CreateStagePolicyParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  stageKey: string;
  requirements?: any[];
  minimumEvidenceScore?: string | number;
  blockingRiskRules?: any[];
}

export interface ListStagePoliciesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  stageKey?: string;
}

export interface UpdateStagePolicyParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  requirements?: any[];
  minimumEvidenceScore?: string | number;
  blockingRiskRules?: any[];
}

export const createStagePolicy = api(
  { method: "POST", path: "/operations/strategy/stage-policies", expose: true },
  async (params: CreateStagePolicyParams): Promise<StagePolicy> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createStagePolicyInWorkspace(ctx, params);
  }
);

export const getStagePolicy = api(
  { method: "GET", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<StagePolicy> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getStagePolicyInWorkspace(ctx, id);
  }
);

export const listStagePolicies = api(
  { method: "GET", path: "/operations/strategy/stage-policies", expose: true },
  async (params: ListStagePoliciesParams): Promise<{ items: StagePolicy[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listStagePoliciesInWorkspace(ctx, params);
  }
);

export const updateStagePolicy = api(
  { method: "PATCH", path: "/operations/strategy/stage-policies/:id", expose: true },
  async (params: UpdateStagePolicyParams): Promise<StagePolicy> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateStagePolicyInWorkspace(ctx, params.id, params);
  }
);

export const deleteStagePolicy = api(
  { method: "DELETE", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteStagePolicyInWorkspace(ctx, id);
  }
);
