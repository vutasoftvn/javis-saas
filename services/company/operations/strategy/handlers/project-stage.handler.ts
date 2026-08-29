import { api, Header, APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db } from "../../models/db";
import { identityWorkspaces } from "../../../shared/db/schema/identity";
import { projects } from "../../../shared/db/schema/operations";
import {
  transitionProjectStage,
  listProjectStageTransitions,
  ProjectLifecycleStage,
  ProjectTransitionResult,
} from "../services/project-stage-lifecycle.service";

// ── GET /operations/strategy/stage-context ──
// M4 §6 — đọc ĐỘC LẬP workspace lifecycle_stage + project lifecycle_stage.
// KHÔNG tự transition — chỉ trả trạng thái để composition/eligibility đọc.

export interface StageContextRequest {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  projectId?: string;
}

export interface StageInfo {
  lifecycleStage: string;
  stageVersion: number;
  stageEnteredAt: string | null;
}

export interface StageContextResponse {
  workspace: StageInfo;
  project: (StageInfo & { id: string }) | null;
}

export const getStageContext = api(
  { method: "GET", path: "/operations/strategy/stage-context", expose: true },
  async (params: StageContextRequest): Promise<StageContextResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [ws] = await db
      .select({
        lifecycleStage: identityWorkspaces.lifecycleStage,
        stageVersion: identityWorkspaces.stageVersion,
        stageEnteredAt: identityWorkspaces.stageEnteredAt,
      })
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId))
      .limit(1);
    if (!ws) throw APIError.notFound("Workspace không tồn tại");

    let project: (StageInfo & { id: string }) | null = null;
    if (params.projectId) {
      const [p] = await db
        .select({
          id: projects.id,
          lifecycleStage: projects.lifecycleStage,
          stageVersion: projects.stageVersion,
          stageEnteredAt: projects.stageEnteredAt,
        })
        .from(projects)
        .where(and(eq(projects.id, BigInt(params.projectId)), eq(projects.workspaceId, wsId)))
        .limit(1);
      if (!p) throw APIError.notFound("Project không tồn tại trong workspace này");
      project = {
        id: p.id.toString(),
        lifecycleStage: p.lifecycleStage,
        stageVersion: p.stageVersion,
        stageEnteredAt: p.stageEnteredAt ? p.stageEnteredAt.toISOString() : null,
      };
    }

    return {
      workspace: {
        lifecycleStage: ws.lifecycleStage,
        stageVersion: ws.stageVersion,
        stageEnteredAt: ws.stageEnteredAt ? ws.stageEnteredAt.toISOString() : null,
      },
      project,
    };
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
