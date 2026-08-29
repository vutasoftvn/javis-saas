import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  assessVentureStage,
  transitionVentureStage,
  listVentureStageTransitions,
  AssessResult,
  TransitionResult,
  VentureStage,
} from "../services/stage-lifecycle.service";

export interface AssessVentureStageRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
}

export interface TransitionVentureStageRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  toStage: VentureStage;
  reason: string;
  override?: boolean;
}

export interface ListVentureStageTransitionsRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
}

export interface ListVentureStageTransitionsResponse {
  transitions: Array<{
    id: string;
    workspaceId: string;
    fromStage: string;
    toStage: string;
    reason: string;
    actorMemberId: string | null;
    overrideFlag: boolean;
    decidedAt: string;
    createdAt: string;
  }>;
}

export const assessVentureStageEndpoint = api(
  { method: "POST", path: "/operations/strategy/venture-stage/assess", expose: true },
  async (params: AssessVentureStageRequest): Promise<AssessResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return assessVentureStage(BigInt(ctx.workspaceId));
  }
);

export const transitionVentureStageEndpoint = api(
  { method: "POST", path: "/operations/strategy/venture-stage/transition", expose: true },
  async (params: TransitionVentureStageRequest): Promise<TransitionResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return transitionVentureStage({
      workspaceId: BigInt(ctx.workspaceId),
      toStage: params.toStage,
      reason: params.reason,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      override: params.override,
    });
  }
);

export const listVentureStageTransitionsEndpoint = api(
  { method: "GET", path: "/operations/strategy/venture-stage/transitions", expose: true },
  async (params: ListVentureStageTransitionsRequest): Promise<ListVentureStageTransitionsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const rows = await listVentureStageTransitions(BigInt(ctx.workspaceId));
    return {
      transitions: rows.map((r) => ({
        id: r.id.toString(),
        workspaceId: r.workspaceId.toString(),
        fromStage: r.fromStage,
        toStage: r.toStage,
        reason: r.reason,
        actorMemberId: r.actorMemberId ? r.actorMemberId.toString() : null,
        overrideFlag: r.overrideFlag,
        decidedAt: r.decidedAt.toISOString(),
        createdAt: r.createdAt.toISOString(),
      })),
    };
  }
);
