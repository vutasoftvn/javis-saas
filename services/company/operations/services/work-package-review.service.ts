import { APIError } from "encore.dev/api";
import { and, desc, eq, isNull, lt } from "drizzle-orm";
import { db, schema } from "../models/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireFounderCommand } from "../../shared/auth/workspace-access";
import { TenantContext } from "../../shared/types/tenant_context";
import { Priority, WorkPackageView, openAttempt } from "./work-package.service";

const {
  taskWorkPackages,
  workPackageAttempts,
  workPackageEvents,
  workPackageReviews,
  workPackagePriorityEvents,
} = schema;

const PRIORITIES: readonly Priority[] = ["P0", "P1", "P2", "P3"];
const REVIEWABLE_STATUSES = ["VALIDATION_PASSED", "PENDING_MANAGER_REVIEW", "ESCALATED_TO_FOUNDER"];

export const OPERATING_WORK_PACKAGE_REVIEW_OVERDUE_V1 = "operating.work_package.review_overdue.v1";

export interface WorkPackageReviewView {
  id: string;
  workPackageId: string;
  decision: "ACCEPT" | "REWORK" | "REJECT";
  packageStatus: string;
  createdAt: string;
}

async function loadPackageForActor(workPackageId: string, ctx: TenantContext) {
  const wsId = BigInt(ctx.workspaceId);
  const [wp] = await db
    .select()
    .from(taskWorkPackages)
    .where(and(eq(taskWorkPackages.id, BigInt(workPackageId)), eq(taskWorkPackages.workspaceId, wsId)))
    .limit(1);
  if (!wp) throw APIError.notFound("work package not found in workspace");
  return wp;
}

function isFounder(ctx: TenantContext): boolean {
  const role = (ctx.membershipRole || "").toLowerCase();
  return role === "founder" || role === "co-founder";
}

function assertOwningManagerOrFounder(
  wp: typeof taskWorkPackages.$inferSelect,
  ctx: TenantContext
): void {
  if (isFounder(ctx)) return;
  if (
    wp.requestedByManagerId &&
    ctx.workforceMemberId &&
    wp.requestedByManagerId.toString() === ctx.workforceMemberId
  ) {
    return;
  }
  throw APIError.permissionDenied("only the owning manager or a founder may review this package");
}

async function appendWpEvent(
  tx: Parameters<Parameters<typeof db.transaction>[0]>[0],
  wsId: bigint,
  workPackageId: bigint,
  eventType: string,
  actor: { kind: string; id?: string },
  before: unknown,
  after: unknown,
  reason?: string
): Promise<void> {
  await tx.insert(workPackageEvents).values({
    id: generateSnowflake(),
    workspaceId: wsId,
    workPackageId,
    eventType,
    actorKind: actor.kind,
    actorId: actor.id ?? null,
    beforeJson: before ?? null,
    afterJson: after ?? null,
    reason: reason ?? null,
  });
}

/**
 * Manager/founder review một work package. ACCEPT chỉ đổi trạng thái nghiệp vụ
 * qua đây (không auto-accept). REWORK kết thúc attempt + queue attempt mới cho
 * employee do manager chọn. REJECT đóng package. Review là bản ghi bất biến,
 * bản mới links supersedes_review_id. CAS theo version.
 */
export async function reviewWorkPackage(
  input: {
    workPackageId: string;
    workAttemptId?: string;
    artifactVersionRef: string;
    decision: "ACCEPT" | "REWORK" | "REJECT";
    rubricScores: Record<string, number>;
    reasonCode: string;
    narrative?: string;
    expectedVersion: number;
    reworkTargetAgentInstanceId?: string;
  },
  ctx: TenantContext
): Promise<WorkPackageReviewView> {
  if (!input.reasonCode?.trim()) throw APIError.invalidArgument("reasonCode is required");
  if (!input.rubricScores || Object.keys(input.rubricScores).length === 0) {
    throw APIError.invalidArgument("rubricScores are required");
  }
  if (!input.artifactVersionRef?.trim()) {
    throw APIError.invalidArgument("artifactVersionRef is required");
  }

  const wp = await loadPackageForActor(input.workPackageId, ctx);
  assertOwningManagerOrFounder(wp, ctx);
  if (!REVIEWABLE_STATUSES.includes(wp.status)) {
    throw APIError.failedPrecondition(`work package is ${wp.status}, not reviewable`);
  }
  if (wp.version !== input.expectedVersion) {
    throw APIError.aborted(
      `stale work package version: expected ${input.expectedVersion}, got ${wp.version}`
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const actor = { kind: ctx.userId ? "user" : "system", id: ctx.userId };

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: workPackageReviews.id })
      .from(workPackageReviews)
      .where(eq(workPackageReviews.workPackageId, wp.id))
      .orderBy(desc(workPackageReviews.createdAt))
      .limit(1);

    const [review] = await tx
      .insert(workPackageReviews)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        workPackageId: wp.id,
        workAttemptId: input.workAttemptId ? BigInt(input.workAttemptId) : null,
        reviewerMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        reviewerKind: isFounder(ctx) ? "founder" : "manager",
        artifactVersionRef: input.artifactVersionRef,
        decision: input.decision,
        rubricScores: input.rubricScores,
        reasonCode: input.reasonCode,
        narrative: input.narrative ?? null,
        supersedesReviewId: prior?.id ?? null,
      })
      .returning();
    if (!review) throw APIError.internal("failed to record review");

    let nextStatus = wp.status;
    if (input.decision === "ACCEPT") {
      nextStatus = "ACCEPTED";
    } else if (input.decision === "REJECT") {
      nextStatus = "REJECTED";
    } else {
      nextStatus = "REWORK";
    }

    await tx
      .update(taskWorkPackages)
      .set({ status: nextStatus, version: wp.version + 1, updatedAt: new Date() })
      .where(and(eq(taskWorkPackages.id, wp.id), eq(taskWorkPackages.version, wp.version)));

    await appendWpEvent(
      tx,
      wsId,
      wp.id,
      `work_package.review_${input.decision.toLowerCase()}`,
      actor,
      { status: wp.status, version: wp.version },
      { status: nextStatus, reviewId: review.id.toString() },
      input.reasonCode
    );

    if (input.decision === "REWORK") {
      // Kết thúc attempt hiện tại, mở attempt mới -> QUEUED.
      const [active] = await tx
        .select()
        .from(workPackageAttempts)
        .where(
          and(
            eq(workPackageAttempts.workPackageId, wp.id),
            isNull(workPackageAttempts.endedAt)
          )
        )
        .limit(1);
      if (active) {
        await tx
          .update(workPackageAttempts)
          .set({ endedAt: new Date(), status: "REWORKED", endedReason: input.reasonCode })
          .where(eq(workPackageAttempts.id, active.id));
      }
      const target = input.reworkTargetAgentInstanceId || wp.assignedAgentInstanceId;
      await openAttempt(tx, {
        workspaceId: ctx.workspaceId,
        workPackageId: wp.id.toString(),
        assignedAgentInstanceId: target,
      });
      await tx
        .update(taskWorkPackages)
        .set({
          status: "QUEUED",
          assignedAgentInstanceId: target,
          version: wp.version + 2,
          updatedAt: new Date(),
        })
        .where(eq(taskWorkPackages.id, wp.id));
      nextStatus = "QUEUED";
    }

    return {
      id: review.id.toString(),
      workPackageId: wp.id.toString(),
      decision: input.decision,
      packageStatus: nextStatus,
      createdAt: review.createdAt.toISOString(),
    };
  });
}

/**
 * Founder override effective priority. Ghi event bất biến {requested, prior
 * effective, new effective}; KHÔNG ghi đè requested_priority.
 */
export async function overrideWorkPackagePriority(
  input: {
    workPackageId: string;
    effectivePriority: Priority;
    reason: string;
    expectedVersion: number;
  },
  ctx: TenantContext
): Promise<WorkPackageView> {
  requireFounderCommand(ctx, "workforce.priority.override");
  if (!PRIORITIES.includes(input.effectivePriority)) {
    throw APIError.invalidArgument(`effectivePriority must be one of ${PRIORITIES.join(", ")}`);
  }
  if (!input.reason?.trim()) throw APIError.invalidArgument("reason is required for a priority override");

  const wp = await loadPackageForActor(input.workPackageId, ctx);
  if (wp.version !== input.expectedVersion) {
    throw APIError.aborted(
      `stale work package version: expected ${input.expectedVersion}, got ${wp.version}`
    );
  }
  const wsId = BigInt(ctx.workspaceId);

  return db.transaction(async (tx) => {
    await tx.insert(workPackagePriorityEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      workPackageId: wp.id,
      actorMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      requestedPriority: wp.requestedPriority,
      priorEffectivePriority: wp.effectivePriority,
      newEffectivePriority: input.effectivePriority,
      reason: input.reason,
    });

    const [updated] = await tx
      .update(taskWorkPackages)
      .set({
        effectivePriority: input.effectivePriority,
        priorityReason: input.reason,
        version: wp.version + 1,
        updatedAt: new Date(),
      })
      .where(and(eq(taskWorkPackages.id, wp.id), eq(taskWorkPackages.version, wp.version)))
      .returning();
    if (!updated) throw APIError.aborted("work package changed concurrently");

    await appendWpEvent(
      tx,
      wsId,
      wp.id,
      "work_package.reprioritized",
      { kind: ctx.userId ? "user" : "system", id: ctx.userId },
      { effectivePriority: wp.effectivePriority },
      {
        requestedPriority: wp.requestedPriority,
        priorEffective: wp.effectivePriority,
        newEffective: input.effectivePriority,
      },
      input.reason
    );

    return {
      workPackageId: updated.id.toString(),
      workspaceId: updated.workspaceId.toString(),
      taskId: updated.taskId.toString(),
      outcomeContractId: updated.outcomeContractId.toString(),
      objective: updated.objective,
      outputContract: (updated.outputContract ?? {}) as Record<string, unknown>,
      acceptanceRubric: (updated.acceptanceRubric ?? {}) as Record<string, number>,
      assignedAgentInstanceId: updated.assignedAgentInstanceId,
      requestedPriority: updated.requestedPriority as Priority,
      effectivePriority: updated.effectivePriority as Priority,
      priorityReason: updated.priorityReason ?? null,
      status: updated.status as WorkPackageView["status"],
      dependencyIds: Array.isArray(updated.dependencyIds) ? (updated.dependencyIds as string[]) : [],
      version: updated.version,
      queuedAt: updated.queuedAt.toISOString(),
      createdAt: updated.createdAt.toISOString(),
    };
  });
}

/**
 * Sweep deterministic: PENDING_MANAGER_REVIEW quá review_due_at ->
 * ESCALATED_TO_FOUNDER + event `review.overdue` + outbox signal. KHÔNG
 * auto-accept ở bất kỳ deadline nào. Trả về số package đã escalate.
 */
export async function runReviewEscalationSweep(now: Date, workspaceId?: string): Promise<number> {
  const conds = [
    eq(taskWorkPackages.status, "PENDING_MANAGER_REVIEW"),
    lt(taskWorkPackages.reviewDueAt, now),
  ];
  if (workspaceId) conds.push(eq(taskWorkPackages.workspaceId, BigInt(workspaceId)));

  const overdue = await db
    .select()
    .from(taskWorkPackages)
    .where(and(...conds));
  if (overdue.length === 0) return 0;

  return db.transaction(async (tx) => {
    let n = 0;
    for (const wp of overdue) {
      const [updated] = await tx
        .update(taskWorkPackages)
        .set({ status: "ESCALATED_TO_FOUNDER", version: wp.version + 1, updatedAt: new Date() })
        .where(and(eq(taskWorkPackages.id, wp.id), eq(taskWorkPackages.version, wp.version)))
        .returning();
      if (!updated) continue;
      n += 1;
      await appendWpEvent(
        tx,
        wp.workspaceId,
        wp.id,
        "review.overdue",
        { kind: "system", id: "review-sweep" },
        { status: "PENDING_MANAGER_REVIEW" },
        { status: "ESCALATED_TO_FOUNDER", reviewDueAt: wp.reviewDueAt?.toISOString() }
      );
      await appendOutboxEvent(
        tx,
        makeBusinessEvent({
          eventType: OPERATING_WORK_PACKAGE_REVIEW_OVERDUE_V1,
          workspaceId: wp.workspaceId.toString(),
          aggregateType: "work_package",
          aggregateId: wp.id.toString(),
          correlationId: generateSnowflake().toString(),
          actor: { kind: "system", id: "review-sweep" },
          classification: "internal",
          payload: {
            workspaceId: wp.workspaceId.toString(),
            workPackageId: wp.id.toString(),
            escalatedTo: "founder",
          },
        })
      );
    }
    return n;
  });
}

/** Test helper: đưa package vào PENDING_MANAGER_REVIEW với review_due_at. */
export async function markValidationPassed(
  workPackageId: string,
  reviewDueAt: Date,
  ctx: TenantContext
): Promise<void> {
  await db
    .update(taskWorkPackages)
    .set({ status: "PENDING_MANAGER_REVIEW", reviewDueAt, updatedAt: new Date() })
    .where(
      and(
        eq(taskWorkPackages.id, BigInt(workPackageId)),
        eq(taskWorkPackages.workspaceId, BigInt(ctx.workspaceId))
      )
    );
}

export async function listWorkPackageReviews(
  workPackageId: string,
  ctx: TenantContext
): Promise<Array<{ id: string; decision: string; supersedesReviewId: string | null }>> {
  const rows = await db
    .select()
    .from(workPackageReviews)
    .where(
      and(
        eq(workPackageReviews.workPackageId, BigInt(workPackageId)),
        eq(workPackageReviews.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .orderBy(workPackageReviews.createdAt);
  return rows.map((r) => ({
    id: r.id.toString(),
    decision: r.decision,
    supersedesReviewId: r.supersedesReviewId ? r.supersedesReviewId.toString() : null,
  }));
}
