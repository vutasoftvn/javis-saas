import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  StageTransition,
  CreateStageTransitionInput,
  createStageTransitionInWorkspace,
  getStageTransitionInWorkspace,
  listStageTransitionsInWorkspace,
  deleteStageTransitionInWorkspace,
} from "../services/stage-transition-config.service";

export type { StageTransition };

export interface CreateStageTransitionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  fromStage: string;
  toStage: string;
  policyId?: string | number;
  allowed?: boolean;
}

export interface ListStageTransitionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const createStageTransition = api(
  { method: "POST", path: "/operations/strategy/stage-transitions", expose: true },
  async (params: CreateStageTransitionParams): Promise<StageTransition> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createStageTransitionInWorkspace(ctx, params);
  }
);

export const getStageTransition = api(
  { method: "GET", path: "/operations/strategy/stage-transitions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<StageTransition> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getStageTransitionInWorkspace(ctx, id);
  }
);

export const listStageTransitions = api(
  { method: "GET", path: "/operations/strategy/stage-transitions", expose: true },
  async (params: ListStageTransitionsParams): Promise<{ items: StageTransition[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listStageTransitionsInWorkspace(ctx);
  }
);

export const deleteStageTransition = api(
  { method: "DELETE", path: "/operations/strategy/stage-transitions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteStageTransitionInWorkspace(ctx, id);
  }
);
