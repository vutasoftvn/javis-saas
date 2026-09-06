import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { requireCommandAuthority } from "../../../identity/services/command-authority.service";
import {
  createStrategicObjective,
  getStrategicObjective,
  listStrategicObjectives,
  updateStrategicObjective,
  saveBscFocusScopes,
  StrategicObjective,
  StrategicObjectiveStatus,
  BscFocusScope,
  SaveBscFocusScopeItem,
} from "../services/strategic-objective.service";

export interface ListStrategicObjectivesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
  status?: StrategicObjectiveStatus;
}

export interface CreateStrategicObjectiveParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
  title: string;
  successDefinition?: string;
  timeHorizonEnd?: string;
  status?: StrategicObjectiveStatus;
  ownerMemberId?: string;
}

export interface GetStrategicObjectiveParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface UpdateStrategicObjectiveParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  projectId?: string;
  title?: string;
  successDefinition?: string;
  timeHorizonEnd?: string;
  status?: StrategicObjectiveStatus;
  ownerMemberId?: string;
  expectedRevision?: number;
}

export interface SaveBscFocusParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  scopes: SaveBscFocusScopeItem[];
}

export const listStrategicObjectivesApi = api(
  { method: "GET", path: "/operations/strategy/objectives", expose: true },
  async (params: ListStrategicObjectivesParams): Promise<{ items: StrategicObjective[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listStrategicObjectives({
      workspaceId: ctx.workspaceId,
      projectId: params.projectId,
      status: params.status,
    });
  }
);

export const createStrategicObjectiveApi = api(
  { method: "POST", path: "/operations/strategy/objectives", expose: true },
  async (params: CreateStrategicObjectiveParams): Promise<StrategicObjective> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return createStrategicObjective(ctx, {
      workspaceId: String(ctx.workspaceId),
      projectId: params.projectId,
      title: params.title,
      successDefinition: params.successDefinition,
      timeHorizonEnd: params.timeHorizonEnd,
      status: params.status,
      ownerMemberId: params.ownerMemberId,
    });
  }
);

export const getStrategicObjectiveApi = api(
  { method: "GET", path: "/operations/strategy/objectives/:id", expose: true },
  async (params: GetStrategicObjectiveParams): Promise<StrategicObjective> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getStrategicObjective(ctx.workspaceId, params.id);
  }
);

export const updateStrategicObjectiveApi = api(
  { method: "PUT", path: "/operations/strategy/objectives/:id", expose: true },
  async (params: UpdateStrategicObjectiveParams): Promise<StrategicObjective> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    return updateStrategicObjective(ctx, {
      workspaceId: String(ctx.workspaceId),
      id: params.id,
      projectId: params.projectId,
      title: params.title,
      successDefinition: params.successDefinition,
      timeHorizonEnd: params.timeHorizonEnd,
      status: params.status,
      ownerMemberId: params.ownerMemberId,
      expectedRevision: params.expectedRevision,
    });
  }
);

export const saveBscFocusApi = api(
  { method: "PUT", path: "/operations/strategy/objectives/:id/bsc-focus", expose: true },
  async (params: SaveBscFocusParams): Promise<{ items: BscFocusScope[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", {
      workspaceId: String(ctx.workspaceId),
    });
    const items = await saveBscFocusScopes(ctx, {
      workspaceId: String(ctx.workspaceId),
      strategicObjectiveId: params.id,
      scopes: params.scopes,
    });
    return { items };
  }
);
