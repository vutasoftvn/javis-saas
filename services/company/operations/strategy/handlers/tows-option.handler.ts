import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { requireCommandAuthority } from "../../../identity/services/command-authority.service";
import {
  createTowsOption,
  updateTowsOption,
  createTowsOptionEvaluation,
  getTowsOption,
  listTowsOptions,
  selectTowsOption,
  rejectTowsOption,
  TowsOption,
  TowsOptionEvaluation,
  TowsQuadrant,
  TowsOptionStatus,
  TowsScorerKind,
} from "../services/tows-option.service";

export interface CreateTowsOptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  quadrant: TowsQuadrant;
  title: string;
  rationale?: string;
  swotItemIds?: string[];
  status?: "DRAFT" | "PROPOSED";
  aiProvenance?: Record<string, any>;
}

export interface UpdateTowsOptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  quadrant?: TowsQuadrant;
  title?: string;
  rationale?: string;
  swotItemIds?: string[];
  expectedRevision?: number;
}

export interface CreateTowsOptionEvaluationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  impactScore: number;
  difficultyScore: number;
  rationale?: string;
  scorerKind?: TowsScorerKind;
}

export interface SelectTowsOptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  strategicObjectiveId?: string;
  reason?: string;
  supersedeOptionId?: string;
}

export interface RejectTowsOptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  reason?: string;
}

export interface ListTowsOptionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  quadrant?: TowsQuadrant;
  status?: TowsOptionStatus;
}

export interface GetTowsOptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export const createTowsOptionApi = api(
  { method: "POST", path: "/operations/strategy/objectives/:objectiveId/tows-options", expose: true },
  async (params: CreateTowsOptionParams): Promise<TowsOption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", { workspaceId: ctx.workspaceId });
    return createTowsOption({
      workspaceId: ctx.workspaceId,
      strategicObjectiveId: params.objectiveId,
      quadrant: params.quadrant,
      title: params.title,
      rationale: params.rationale,
      swotItemIds: params.swotItemIds,
      status: params.status,
      aiProvenance: params.aiProvenance,
      createdByMemberId: ctx.workforceMemberId ?? ctx.userId,
    });
  }
);

export const updateTowsOptionApi = api(
  { method: "PUT", path: "/operations/strategy/tows-options/:id", expose: true },
  async (params: UpdateTowsOptionParams): Promise<TowsOption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", { workspaceId: ctx.workspaceId });
    return updateTowsOption({
      id: params.id,
      workspaceId: ctx.workspaceId,
      quadrant: params.quadrant,
      title: params.title,
      rationale: params.rationale,
      swotItemIds: params.swotItemIds,
      expectedRevision: params.expectedRevision,
      updatedByMemberId: ctx.workforceMemberId ?? ctx.userId,
    });
  }
);

export const createTowsOptionEvaluationApi = api(
  { method: "POST", path: "/operations/strategy/tows-options/:id/evaluations", expose: true },
  async (params: CreateTowsOptionEvaluationParams): Promise<TowsOptionEvaluation> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await requireCommandAuthority(ctx, "strategy.analysis.write", { workspaceId: ctx.workspaceId });
    return createTowsOptionEvaluation({
      workspaceId: ctx.workspaceId,
      towsOptionId: params.id,
      impactScore: params.impactScore,
      difficultyScore: params.difficultyScore,
      rationale: params.rationale,
      scorerKind: params.scorerKind,
      scoredByMemberId: ctx.workforceMemberId ?? ctx.userId,
    });
  }
);

export const selectTowsOptionApi = api(
  { method: "POST", path: "/operations/strategy/tows-options/:id/select", expose: true },
  async (params: SelectTowsOptionParams): Promise<TowsOption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return selectTowsOption(
      {
        id: params.id,
        strategicObjectiveId: params.strategicObjectiveId,
        reason: params.reason,
        supersedeOptionId: params.supersedeOptionId,
      },
      ctx
    );
  }
);

export const rejectTowsOptionApi = api(
  { method: "POST", path: "/operations/strategy/tows-options/:id/reject", expose: true },
  async (params: RejectTowsOptionParams): Promise<TowsOption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return rejectTowsOption(
      {
        id: params.id,
        reason: params.reason,
      },
      ctx
    );
  }
);

export const listTowsOptionsApi = api(
  { method: "GET", path: "/operations/strategy/objectives/:objectiveId/tows-options", expose: true },
  async (params: ListTowsOptionsParams): Promise<{ items: TowsOption[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listTowsOptions({
      workspaceId: ctx.workspaceId,
      strategicObjectiveId: params.objectiveId,
      quadrant: params.quadrant,
      status: params.status,
    });
  }
);

export const getTowsOptionApi = api(
  { method: "GET", path: "/operations/strategy/tows-options/:id", expose: true },
  async (params: GetTowsOptionParams): Promise<TowsOption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getTowsOption(params.id, ctx.workspaceId);
  }
);
