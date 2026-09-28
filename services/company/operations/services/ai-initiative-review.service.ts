import { APIError } from "encore.dev/api";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { initiatives, aiInitiativeDecisions } = schema;

export interface RecordAiInitiativeReviewParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  reviewCadenceDays?: number;
  findings: string;
  recommendation: "CONTINUE" | "PAUSE" | "REVISE_BUDGET" | "REVISE_METRIC" | "SCALE_UP" | "RETIRE";
}

export interface AiInitiativeReviewSummary {
  initiativeId: string;
  recommendation: string;
  reviewedAt: string;
  nextReviewDueAt: string;
  findings: string;
}

export interface PauseAiInitiativeParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  reasonCode: string;
  reason?: string;
}

export interface PauseAiInitiativeResult {
  status: "PAUSED";
  initiativeId: string;
  message?: string;
}

export async function recordAiInitiativeReview(
  ctx: TenantContext,
  params: RecordAiInitiativeReviewParams
): Promise<AiInitiativeReviewSummary> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  const [row] = await db
    .select()
    .from(initiatives)
    .where(
      and(
        eq(initiatives.id, initId),
        eq(initiatives.workspaceId, wsId),
        eq(initiatives.projectId, projId),
        isNull(initiatives.deletedAt)
      )
    );

  if (!row) {
    throw APIError.notFound("AI initiative not found");
  }

  const now = new Date();
  const cadenceDays = params.reviewCadenceDays ?? 14;
  const nextDue = new Date(now.getTime() + cadenceDays * 24 * 60 * 60 * 1000);

  const decisionId = generateSnowflake();
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  await db.insert(aiInitiativeDecisions).values({
    id: decisionId,
    workspaceId: wsId,
    projectId: projId,
    initiativeId: initId,
    revision: row.revision,
    decision: "REVIEW",
    fromState: row.lifecycleState,
    toState: row.lifecycleState,
    actorMemberId,
    reasonCode: params.recommendation,
    reason: params.findings,
    gateSnapshot: {
      recommendation: params.recommendation,
      cadenceDays,
      reviewedAt: now.toISOString(),
      nextReviewDueAt: nextDue.toISOString(),
    },
    decidedAt: now,
  });

  return {
    initiativeId: params.initiativeId,
    recommendation: params.recommendation,
    reviewedAt: now.toISOString(),
    nextReviewDueAt: nextDue.toISOString(),
    findings: params.findings,
  };
}

export async function pauseAiInitiative(
  ctx: TenantContext,
  params: PauseAiInitiativeParams
): Promise<PauseAiInitiativeResult> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  const [row] = await db
    .select()
    .from(initiatives)
    .where(
      and(
        eq(initiatives.id, initId),
        eq(initiatives.workspaceId, wsId),
        eq(initiatives.projectId, projId),
        isNull(initiatives.deletedAt)
      )
    );

  if (!row) {
    throw APIError.notFound("AI initiative not found");
  }

  // Idempotency: if already paused, return success without mutating
  if (row.lifecycleState === "PAUSED") {
    return {
      status: "PAUSED",
      initiativeId: params.initiativeId,
      message: "Initiative is already paused",
    };
  }

  const now = new Date();
  const newRevision = row.revision + 1;
  const decisionId = generateSnowflake();
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  await db.transaction(async (tx) => {
    await tx
      .update(initiatives)
      .set({
        lifecycleState: "PAUSED",
        revision: newRevision,
        updatedAt: now,
      })
      .where(eq(initiatives.id, initId));

    await tx.insert(aiInitiativeDecisions).values({
      id: decisionId,
      workspaceId: wsId,
      projectId: projId,
      initiativeId: initId,
      revision: newRevision,
      decision: "PAUSE",
      fromState: row.lifecycleState,
      toState: "PAUSED",
      actorMemberId,
      reasonCode: params.reasonCode,
      reason: params.reason,
      gateSnapshot: {
        pausedAt: now.toISOString(),
        previousState: row.lifecycleState,
      },
      decidedAt: now,
    });
  });

  return {
    status: "PAUSED",
    initiativeId: params.initiativeId,
  };
}
