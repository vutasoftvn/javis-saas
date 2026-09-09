import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const {
  taskResults,
  taskOutcomeReviews,
  outcomeAssessments,
  krContributionAssessments,
  keyResults,
} = schema;

export interface TaskOutcomeReviewView {
  id: string;
  taskResultId: string;
  decision: "ACCEPT" | "REWORK" | "REJECT";
  createdAt: string;
}

export interface KrContributionView {
  id: string;
  state: "PROPOSED" | "VERIFIED" | "REJECTED" | "INSUFFICIENT_EVIDENCE";
  version: number;
}

/**
 * Manager/founder review outcome ở tầng task. ACCEPT chỉ hợp lệ khi
 * assessment tham chiếu đang READY và result revision khớp expected. Không ghi
 * KR actual. Review là bản ghi bất biến, bản mới links supersedes_review_id.
 */
export async function reviewTaskOutcome(
  input: {
    taskResultId: string;
    assessmentId: string;
    decision: "ACCEPT" | "REWORK" | "REJECT";
    expectedResultRevision: number;
    reasonCode: string;
    narrative?: string;
  },
  ctx: TenantContext
): Promise<TaskOutcomeReviewView> {
  if (!input.reasonCode?.trim()) throw APIError.invalidArgument("reasonCode is required");
  const wsId = BigInt(ctx.workspaceId);

  const [result] = await db
    .select()
    .from(taskResults)
    .where(and(eq(taskResults.id, BigInt(input.taskResultId)), eq(taskResults.workspaceId, wsId)))
    .limit(1);
  if (!result) throw APIError.notFound("task result not found in workspace");
  if (result.resultRevision !== input.expectedResultRevision) {
    throw APIError.aborted(
      `stale result revision: expected ${input.expectedResultRevision}, got ${result.resultRevision}`
    );
  }

  const [assessment] = await db
    .select()
    .from(outcomeAssessments)
    .where(
      and(
        eq(outcomeAssessments.id, BigInt(input.assessmentId)),
        eq(outcomeAssessments.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!assessment || assessment.taskResultId.toString() !== input.taskResultId) {
    throw APIError.invalidArgument("assessment does not belong to this task result");
  }
  if (input.decision === "ACCEPT" && assessment.status !== "READY") {
    throw APIError.failedPrecondition(
      `latest assessment must be READY to accept (current: ${assessment.status})`
    );
  }

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: taskOutcomeReviews.id })
      .from(taskOutcomeReviews)
      .where(eq(taskOutcomeReviews.taskResultId, result.id))
      .orderBy(desc(taskOutcomeReviews.createdAt))
      .limit(1);

    const [row] = await tx
      .insert(taskOutcomeReviews)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        taskResultId: result.id,
        assessmentId: assessment.id,
        expectedResultRevision: input.expectedResultRevision,
        reviewerMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        decision: input.decision,
        reasonCode: input.reasonCode,
        narrative: input.narrative ?? null,
        supersedesReviewId: prior?.id ?? null,
      })
      .returning();
    if (!row) throw APIError.internal("failed to record task outcome review");

    return {
      id: row.id.toString(),
      taskResultId: result.id.toString(),
      decision: input.decision,
      createdAt: row.createdAt.toISOString(),
    };
  });
}

/**
 * Reviewer xác minh một KR contribution. Ghi state VERIFIED / REJECTED /
 * INSUFFICIENT_EVIDENCE (append qua version bump). KHÔNG BAO GIỜ ghi
 * KR.currentValue / actualValue.
 */
export async function verifyKrContribution(
  input: {
    contributionId: string;
    decision: "VERIFIED" | "REJECTED" | "INSUFFICIENT_EVIDENCE";
    reason: string;
    expectedVersion: number;
  },
  ctx: TenantContext
): Promise<KrContributionView> {
  if (!input.reason?.trim()) throw APIError.invalidArgument("reason is required");
  const wsId = BigInt(ctx.workspaceId);

  const [contribution] = await db
    .select()
    .from(krContributionAssessments)
    .where(
      and(
        eq(krContributionAssessments.id, BigInt(input.contributionId)),
        eq(krContributionAssessments.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!contribution) throw APIError.notFound("KR contribution not found in workspace");
  if (contribution.version !== input.expectedVersion) {
    throw APIError.aborted(
      `stale contribution version: expected ${input.expectedVersion}, got ${contribution.version}`
    );
  }

  const [updated] = await db
    .update(krContributionAssessments)
    .set({
      state: input.decision,
      verifiedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      verifiedAt: new Date(),
      reason: input.reason,
      version: contribution.version + 1,
    })
    .where(
      and(
        eq(krContributionAssessments.id, contribution.id),
        eq(krContributionAssessments.version, contribution.version)
      )
    )
    .returning();
  if (!updated) throw APIError.aborted("contribution changed concurrently");

  // Guard rõ ràng: endpoint này KHÔNG chạm keyResults.
  void keyResults;

  return {
    id: updated.id.toString(),
    state: updated.state as KrContributionView["state"],
    version: updated.version,
  };
}
