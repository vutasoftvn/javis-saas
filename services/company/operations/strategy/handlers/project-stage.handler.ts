import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  transitionProjectStage,
  listProjectStageTransitions,
  getStageContextInWorkspace,
  ProjectLifecycleStage,
  ProjectTransitionResult,
  StageContextResponse,
  StageInfo,
} from "../services/project-stage-lifecycle.service";

export type { ProjectLifecycleStage, ProjectTransitionResult, StageContextResponse, StageInfo };

// ── GET /operations/strategy/stage-context ──
// M4 §6 — đọc ĐỘC LẬP workspace lifecycle_stage + project lifecycle_stage.
// KHÔNG tự transition — chỉ trả trạng thái để composition/eligibility đọc.

export interface StageContextRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  projectId?: string;
}

export const getStageContext = api(
  { method: "GET", path: "/operations/strategy/stage-context", expose: true },
  async (params: StageContextRequest): Promise<StageContextResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getStageContextInWorkspace(ctx, params.projectId);
  }
);

// ── POST /operations/strategy/projects/:id/stage ──

export interface TransitionProjectStageRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  id: string;
  toStage: ProjectLifecycleStage;
  reason: string;
  override?: boolean;
  overrideApprovalRef?: string;
}

export const transitionProjectStageEndpoint = api(
  { method: "POST", path: "/operations/strategy/projects/:id/stage", expose: true },
  async (params: TransitionProjectStageRequest): Promise<ProjectTransitionResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return transitionProjectStage({
      workspaceId: BigInt(ctx.workspaceId),
      projectId: BigInt(params.id),
      toStage: params.toStage,
      reason: params.reason,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
      isAutonomous: false, // endpoint HTTP = người thao tác
      override: params.override,
      overrideApprovalRef: params.overrideApprovalRef,
    });
  }
);

// ── GET /operations/strategy/projects/:id/stage/transitions ──

export interface ListProjectStageTransitionsRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  id: string;
}

export interface ListProjectStageTransitionsResponse {
  transitions: Array<{
    id: string;
    projectId: string;
    fromStage: string;
    toStage: string;
    reason: string;
    source: string;
    overrideFlag: boolean;
    stageVersionFrom: number | null;
    decidedAt: string;
  }>;
}

export const listProjectStageTransitionsEndpoint = api(
  { method: "GET", path: "/operations/strategy/projects/:id/stage/transitions", expose: true },
  async (
    params: ListProjectStageTransitionsRequest
  ): Promise<ListProjectStageTransitionsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const rows = await listProjectStageTransitions(BigInt(ctx.workspaceId), BigInt(params.id));
    return {
      transitions: rows.map((r) => ({
        id: r.id.toString(),
        projectId: r.projectId.toString(),
        fromStage: r.fromStage,
        toStage: r.toStage,
        reason: r.reason,
        source: r.source,
        overrideFlag: r.overrideFlag,
        stageVersionFrom: r.stageVersionFrom,
        decidedAt: r.decidedAt.toISOString(),
      })),
    };
  }
);
