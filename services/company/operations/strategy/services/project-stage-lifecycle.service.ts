import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";
import { identityWorkspaces } from "../../../shared/db/schema/identity";
import { TenantContext } from "../../../shared/types/tenant_context";
import {
  projectStageTransitionPolicies,
  projectStageTransitions,
} from "../../../shared/db/schema/strategy";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { buildProjectPhaseChangedEvent } from "../events/venture-stage-events";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { PROJECT_STAGES } from "./stage-assessment.service";

import { isLifecyclePrivileged } from "./lifecycle-authorization.service";

export type ProjectLifecycleStage =
  | "P0_DISCOVERY"
  | "P1_PROBLEM_VALIDATION"
  | "P2_SOLUTION_VALIDATION"
  | "P3_BUILD_VALIDATE"
  | "P4_GO_TO_MARKET"
  | "P5_OPERATE_GROWTH"
  | "P6_SCALE_GOVERN";

export interface ProjectTransitionParams {
  workspaceId: bigint;
  projectId: bigint;
  toStage: ProjectLifecycleStage;
  reason: string;
  actorMemberId?: bigint;
  actorRole?: string;
  isAutonomous?: boolean;
  override?: boolean;
  source?: "manual" | "autonomous" | "api" | "system";
  overrideApprovalRef?: string;
}

export interface ProjectTransitionResult {
  projectId: string;
  fromStage: ProjectLifecycleStage;
  toStage: ProjectLifecycleStage;
  enteredAt: string;
  overrideApplied: boolean;
  noop: boolean;
  stageVersion: number;
}

export async function transitionProjectStageInTransaction(
  tx: Parameters<Parameters<typeof db.transaction>[0]>[0],
  p: ProjectTransitionParams
): Promise<ProjectTransitionResult> {
  if (p.override) {
    if (!p.overrideApprovalRef || !p.overrideApprovalRef.trim()) {
      throw APIError.invalidArgument("overrideApprovalRef is required when override=true");
    }
  }

  const [proj] = await tx
    .select({
      id: projects.id,
      lifecycleStage: projects.lifecycleStage,
      stageVersion: projects.stageVersion,
      stageEnteredAt: projects.stageEnteredAt,
    })
    .from(projects)
    .where(and(eq(projects.id, p.projectId), eq(projects.workspaceId, p.workspaceId)))
    .limit(1);

  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  const currentStage = (proj.lifecycleStage as ProjectLifecycleStage) || "P0_DISCOVERY";
  const currentIndex = PROJECT_STAGES.indexOf(currentStage);
  const toIndex = PROJECT_STAGES.indexOf(p.toStage);

  if (toIndex === -1) {
    throw APIError.invalidArgument(`Project stage đích '${p.toStage}' không hợp lệ`);
  }

  // Same-stage ⇒ no-op tường minh, KHÔNG ghi history row.
  if (toIndex === currentIndex) {
    return {
      projectId: p.projectId.toString(),
      fromStage: currentStage,
      toStage: p.toStage,
      enteredAt: (proj.stageEnteredAt ?? new Date()).toISOString(),
      overrideApplied: false,
      noop: true,
      stageVersion: proj.stageVersion,
    };
  }

  if (toIndex > currentIndex + 1) {
    throw APIError.invalidArgument("Project chỉ được tiến tối đa 1 bậc stage");
  }
  if (toIndex < currentIndex && (!p.reason || !p.reason.trim())) {
    throw APIError.invalidArgument("Lùi project stage bắt buộc phải cung cấp lý do");
  }

  // Policy edge (currentStage -> toStage). Ưu tiên policy theo project, fallback theo workspace.
  const [edge] = await tx
    .select({
      allowed: projectStageTransitionPolicies.allowed,
      policyVersion: projectStageTransitionPolicies.policyVersion,
      projectId: projectStageTransitionPolicies.projectId,
    })
    .from(projectStageTransitionPolicies)
    .where(
      and(
        eq(projectStageTransitionPolicies.workspaceId, p.workspaceId),
        eq(projectStageTransitionPolicies.fromStage, currentStage),
        eq(projectStageTransitionPolicies.toStage, p.toStage)
      )
    )
    .orderBy(desc(projectStageTransitionPolicies.projectId))
    .limit(1);

  const privileged = isLifecyclePrivileged(p.actorRole);
  const isForward = toIndex === currentIndex + 1;

  if (isForward) {
    if (!edge) {
      // Fail-closed cho autonomous; người thường bị chặn; founder/admin đi tiếp.
      if (p.isAutonomous) {
        throw APIError.failedPrecondition(
          `Không có project stage transition policy cho ${currentStage} → ${p.toStage} — chặn tự động (fail-closed)`
        );
      }
      if (!privileged) {
        throw APIError.permissionDenied(
          "Chỉ founder/admin mới chuyển project stage khi chưa cấu hình policy"
        );
      }
    } else if (!edge.allowed) {
      if (!p.override) {
        throw APIError.failedPrecondition(
          `Policy chặn transition ${currentStage} → ${p.toStage}`
        );
      }
      if (p.isAutonomous) {
        throw APIError.permissionDenied("Agent tự động không được tự override project gate");
      }
      if (!privileged) {
        throw APIError.permissionDenied("Override project gate chỉ dành cho founder/admin");
      }
    }
  }

  const now = new Date();
  const transitionId = generateSnowflake();
  const fromVersion = proj.stageVersion;
  const nextVersion = fromVersion + 1;
  const source: "manual" | "autonomous" | "api" | "system" =
    p.source ?? (p.isAutonomous ? "autonomous" : "manual");

  const updated = await tx
    .update(projects)
    .set({
      lifecycleStage: p.toStage,
      stageVersion: nextVersion,
      stageEnteredAt: now,
      updatedAt: now,
    })
    .where(and(eq(projects.id, p.projectId), eq(projects.stageVersion, fromVersion)))
    .returning({ id: projects.id });

  if (updated.length === 0) {
    throw APIError.aborted(
      "project stage_version đã thay đổi (transition đồng thời) — hãy re-evaluate rồi thử lại"
    );
  }

  await tx.insert(projectStageTransitions).values({
    id: transitionId,
    workspaceId: p.workspaceId,
    projectId: p.projectId,
    fromStage: currentStage,
    toStage: p.toStage,
    reason: p.reason,
    actorMemberId: p.actorMemberId || null,
    actorRole: p.actorRole ?? null,
    overrideFlag: !!p.override,
    overrideApprovalRef: p.overrideApprovalRef ?? null,
    source,
    stageVersionFrom: fromVersion,
    policyVersion: edge?.policyVersion ?? null,
    evidenceSnapshot: { capturedAt: now.toISOString() },
    evaluationResult: edge ? { allowed: edge.allowed } : null,
    decidedAt: now,
    createdAt: now,
  });

  const event = buildProjectPhaseChangedEvent({
    projectId: p.projectId.toString(),
    workspaceId: p.workspaceId.toString(),
    fromPhase: currentStage,
    toPhase: p.toStage,
    actorMemberId: p.actorMemberId ? p.actorMemberId.toString() : null,
  });
  await appendOutboxEvent(tx, event);

  return {
    projectId: p.projectId.toString(),
    fromStage: currentStage,
    toStage: p.toStage,
    enteredAt: now.toISOString(),
    overrideApplied: !!p.override,
    noop: false,
    stageVersion: nextVersion,
  };
}

export async function transitionProjectStage(
  p: ProjectTransitionParams
): Promise<ProjectTransitionResult> {
  return db.transaction((tx) => transitionProjectStageInTransaction(tx, p));
}

export async function listProjectStageTransitions(workspaceId: bigint, projectId: bigint) {
  return db
    .select()
    .from(projectStageTransitions)
    .where(
      and(
        eq(projectStageTransitions.workspaceId, workspaceId),
        eq(projectStageTransitions.projectId, projectId)
      )
    )
    .orderBy(desc(projectStageTransitions.decidedAt));
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

export async function getStageContextInWorkspace(
  ctx: TenantContext,
  projectId?: string | number
): Promise<StageContextResponse> {
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
  if (projectId) {
    const [p] = await db
      .select({
        id: projects.id,
        lifecycleStage: projects.lifecycleStage,
        stageVersion: projects.stageVersion,
        stageEnteredAt: projects.stageEnteredAt,
      })
      .from(projects)
      .where(and(eq(projects.id, BigInt(projectId)), eq(projects.workspaceId, wsId)))
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
