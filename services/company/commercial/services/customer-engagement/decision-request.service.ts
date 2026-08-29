import { APIError } from "encore.dev/api";
import { and, eq, inArray, lt, sql } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { ENGAGEMENT_PERMISSIONS, requireEngagementPermission } from "./rbac";
import { assertDRTransition, DRStatus } from "./decision-request-state";
import {
  resolveEnabledAuthority,
  memberCoversCapability,
  assertApprovalPolicySatisfied,
  ApprovalPolicy,
} from "./decision-authority.service";
import { buildDecisionRequestSubmittedEvent, buildDecisionRequestDecidedEvent } from "../../../shared/events/customer-engagement-events";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";

export interface DR_DTO {
  id: string;
  workspaceId: string;
  threadId?: string | null;
  requestType: string;
  status: DRStatus;
  contactId?: string | null;
  accountId?: string | null;
  leadId?: string | null;
  opportunityId?: string | null;
  customerId?: string | null;
  policySnapshotRef?: string | null;
  factsRef?: string | null;
  evidenceRefs?: unknown[];
  options?: unknown[];
  recommendationRef?: string | null;
  requestedByWorkforceMemberId: string;
  authorityKey: string;
  authorityVersion: number;
  approvalPolicySnapshot: ApprovalPolicy;
  approvalDeadline?: string | null;
  decision?: string | null;
  decisionReason?: string | null;
  approvedAt?: string | null;
  executedByWorkforceMemberId?: string | null;
  executionRef?: string | null;
  correlationId: string;
  approvals: Array<{
    workforceMemberId: string;
    capability: string;
    decision: string;
    decidedAt: string;
  }>;
}

export async function createDecisionRequest(
  {
    threadId,
    requestType,
    contactId,
    accountId,
    leadId,
    opportunityId,
    customerId,
    options = [],
    factsRef,
    recommendationRef,
    authorityKey,
  }: {
    threadId?: string;
    requestType: string;
    contactId?: string;
    accountId?: string;
    leadId?: string;
    opportunityId?: string;
    customerId?: string;
    options?: unknown[];
    factsRef?: string;
    recommendationRef?: string;
    authorityKey: string;
  },
  ctx: TenantContext,
): Promise<DR_DTO> {
  // Fail-closed: verify authority is enabled
  const { authority, approvalPolicy } = await resolveEnabledAuthority(authorityKey, ctx);

  // Requester must be workforce member
  if (!ctx.workforceMemberId) {
    throw APIError.permissionDenied("requester must be a workforce member");
  }

  const id = BigInt(generateSnowflake());
  const correlationId = threadId ? `th_${threadId}` : `dr_${id}`;

  const [row] = await db
    .insert(schema.engagementDecisionRequests)
    .values({
      id,
      workspaceId: BigInt(ctx.workspaceId),
      threadId: threadId ? BigInt(threadId) : null,
      requestType,
      status: "draft" as DRStatus,
      contactId: contactId ? BigInt(contactId) : null,
      accountId: accountId ? BigInt(accountId) : null,
      leadId: leadId ? BigInt(leadId) : null,
      opportunityId: opportunityId ? BigInt(opportunityId) : null,
      customerId: customerId ? BigInt(customerId) : null,
      factsRef,
      evidenceRefs: [],
      options,
      recommendationRef,
      requestedByActor: { kind: "user", id: ctx.workforceMemberId },
      requestedByWorkforceMemberId: BigInt(ctx.workforceMemberId),
      authorityKey,
      authorityVersion: authority.version,
      approvalPolicySnapshot: approvalPolicy,
      correlationId,
    })
    .returning();

  if (!row) {
    throw APIError.internal("failed to create decision request");
  }

  return rowToDTO(row, []);
}

export async function submitDecisionRequest(
  id: string | bigint,
  {
    policyId,
    policyVersion,
    policySnapshotRef,
  }: {
    policyId?: string;
    policyVersion?: string;
    policySnapshotRef: string;
  },
  ctx: TenantContext,
): Promise<DR_DTO> {
  // Validate required policySnapshotRef
  if (!policySnapshotRef) {
    throw APIError.invalidArgument("policySnapshotRef is required");
  }

  const drId = typeof id === "string" ? BigInt(id) : id;
  const dr = await getDecisionRequestInternal(drId, ctx);

  // Fail-closed: re-verify authority is enabled
  await resolveEnabledAuthority(dr.authorityKey, ctx);

  // Enforce transition
  assertDRTransition(dr.status as DRStatus, "submitted");

  // Update and emit event in transaction
  const [updated] = await db.transaction(async (tx) => {
    const [u] = await tx
      .update(schema.engagementDecisionRequests)
      .set({
        status: "submitted" as any,
        policyId,
        policyVersion,
        policySnapshotRef,
      })
      .where(eq(schema.engagementDecisionRequests.id, drId))
      .returning();

    // Add event
    await tx.insert(schema.engagementDecisionRequestEvents).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      decisionRequestId: drId,
      eventType: "submitted",
      actor: { kind: "user", id: ctx.workforceMemberId },
    });

    // Append outbox event
    await appendOutboxEvent(
      tx as any,
      buildDecisionRequestSubmittedEvent(
        {
          decisionRequestId: String(drId),
          workspaceId: String(ctx.workspaceId),
          requestType: dr.requestType,
          correlationId: dr.correlationId,
        },
        { kind: "user", id: ctx.workforceMemberId ?? ctx.userId },
      ),
    );

    // If thread, update to awaiting_decision
    if (dr.threadId) {
      await tx
        .update(schema.engagementThreads)
        .set({ activeMode: "awaiting_decision" })
        .where(eq(schema.engagementThreads.id, dr.threadId));
    }

    return [u];
  });

  const approvals = await db.query.engagementDecisionRequestApprovals.findMany({
    where: eq(schema.engagementDecisionRequestApprovals.decisionRequestId, drId),
  });

  return rowToDTO(updated, approvals);
}

export async function startReview(id: string | bigint, ctx: TenantContext): Promise<DR_DTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.decisionReview);

  const drId = typeof id === "string" ? BigInt(id) : id;
  const dr = await getDecisionRequestInternal(drId, ctx);

  assertDRTransition(dr.status as DRStatus, "under_review");

  const [updated] = await db.transaction(async (tx) => {
    const [u] = await tx
      .update(schema.engagementDecisionRequests)
      .set({ status: "under_review" as any })
      .where(eq(schema.engagementDecisionRequests.id, drId))
      .returning();

    await tx.insert(schema.engagementDecisionRequestEvents).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      decisionRequestId: drId,
      eventType: "review_started",
      actor: { kind: "user", id: ctx.workforceMemberId },
    });

    return [u];
  });

  const approvals = await db.query.engagementDecisionRequestApprovals.findMany({
    where: eq(schema.engagementDecisionRequestApprovals.decisionRequestId, drId),
  });

  return rowToDTO(updated, approvals);
}

export async function recordApproval(
  id: string | bigint,
  {
    decision,
    reason,
  }: {
    decision: "approve" | "reject" | "needs_information";
    reason?: string;
  },
  ctx: TenantContext,
): Promise<DR_DTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.decisionDecide);

  const drId = typeof id === "string" ? BigInt(id) : id;
  const dr = await getDecisionRequestInternal(drId, ctx);

  // A requester is never an approver, regardless of the request's current
  // lifecycle state or any authority grant they happen to hold.
  if (ctx.workforceMemberId === String(dr.requestedByWorkforceMemberId)) {
    throw APIError.permissionDenied("requester cannot approve");
  }

  if (dr.status !== "submitted" && dr.status !== "under_review") {
    throw APIError.failedPrecondition(
      `decision request status is ${dr.status}, not ready for approval`,
    );
  }

  // Fail-closed: member must have active grant for this authority
  const cap = await memberCoversCapability(ctx.workforceMemberId!, dr.authorityKey, ctx);
  if (!cap) {
    throw APIError.permissionDenied("no active grant for this authority");
  }

  // Insert approval (unique constraint on (dr_id, member_id) will prevent double approval)
  try {
    await db.insert(schema.engagementDecisionRequestApprovals).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      decisionRequestId: drId,
      workforceMemberId: BigInt(ctx.workforceMemberId!),
      capability: cap,
      decision,
      reason: reason ?? null,
    });
  } catch (err: any) {
    // Check for unique constraint violation
    if (err.cause?.code === "23505" || err.code === "23505") {
      throw APIError.alreadyExists("already recorded an approval");
    }
    throw err;
  }

  const allApprovals = await db.query.engagementDecisionRequestApprovals.findMany({
    where: eq(schema.engagementDecisionRequestApprovals.decisionRequestId, drId),
  });

  // Update decision request status based on decision type
  // The first recorded approval starts review. A policy that is immediately
  // satisfied may complete in the same transaction, but an incomplete one
  // must never remain in the ambiguous submitted state.
  let newStatus: DRStatus | null = dr.status === "submitted" ? "under_review" : null;
  let newDecision: string | null = null;
  let approvedAt: Date | null = null;
  let shouldEmitDecidedEvent = false;

  if (decision === "reject") {
    newStatus = "rejected";
    newDecision = "rejected";
    shouldEmitDecidedEvent = true;
  } else if (decision === "needs_information") {
    newStatus = "needs_information";
  } else if (decision === "approve") {
    // Check if policy is satisfied after adding this approval
    try {
      assertApprovalPolicySatisfied(
        dr.approvalPolicySnapshot as ApprovalPolicy,
        allApprovals.map((a) => ({
          workforceMemberId: a.workforceMemberId,
          capability: a.capability,
          decision: a.decision,
        })),
      );
      // Policy satisfied: move to approved
      newStatus = "approved";
      newDecision = "approved";
      approvedAt = new Date();
      shouldEmitDecidedEvent = true;
    } catch (e) {
      // Not enough approvals yet: stay in under_review
      // Do NOT throw the error - just stay in current state
    }
  }

  const [updated] = await db.transaction(async (tx) => {
    if (newStatus) {
      const [u] = await tx
        .update(schema.engagementDecisionRequests)
        .set({
          status: newStatus as any,
          ...(newDecision && { decision: newDecision }),
          ...(approvedAt && { approvedAt }),
        })
        .where(eq(schema.engagementDecisionRequests.id, drId))
        .returning();

      // Add event for status change
      const eventType = decision === "approve" && newStatus === "approved" ? "approved" :
                       decision === "reject" ? "rejected" :
                       decision === "needs_information" ? "needs_information" :
                       "approval_recorded";

      await tx.insert(schema.engagementDecisionRequestEvents).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ctx.workspaceId),
        decisionRequestId: drId,
        eventType,
        actor: { kind: "user", id: ctx.workforceMemberId },
      });

      // Emit decided event if terminal state
      if (shouldEmitDecidedEvent) {
        await appendOutboxEvent(
          tx as any,
          buildDecisionRequestDecidedEvent(
            {
              decisionRequestId: String(drId),
              workspaceId: String(ctx.workspaceId),
              decision: newDecision!,
              correlationId: dr.correlationId,
            },
            { kind: "user", id: ctx.workforceMemberId ?? ctx.userId },
          ),
        );
      }

      return [u];
    } else {
      // No state change, just add event
      await tx.insert(schema.engagementDecisionRequestEvents).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ctx.workspaceId),
        decisionRequestId: drId,
        eventType: "approval_recorded",
        actor: { kind: "user", id: ctx.workforceMemberId },
      });

      // Return unchanged row
      const [u] = await tx
        .select()
        .from(schema.engagementDecisionRequests)
        .where(eq(schema.engagementDecisionRequests.id, drId));
      return [u];
    }
  });

  return rowToDTO(updated, allApprovals);
}

export async function executeDecisionRequest(id: string | bigint, ctx: TenantContext): Promise<DR_DTO> {
  const drId = typeof id === "string" ? BigInt(id) : id;
  const dr = await getDecisionRequestInternal(drId, ctx);

  // EXECUTION GUARD (fail-closed) - check ALL conditions

  // 1. Status must be approved
  if (dr.status !== "approved") {
    throw APIError.failedPrecondition(`decision request status is ${dr.status}, not approved`);
  }

  // 2. Check deadline
  if (dr.approvalDeadline && new Date(dr.approvalDeadline) < new Date()) {
    // Mark as expired and throw
    await db.transaction(async (tx) => {
      await tx
        .update(schema.engagementDecisionRequests)
        .set({ status: "expired" as any })
        .where(eq(schema.engagementDecisionRequests.id, drId));

      await tx.insert(schema.engagementDecisionRequestEvents).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ctx.workspaceId),
        decisionRequestId: drId,
        eventType: "expired",
        actor: { kind: "user", id: ctx.workforceMemberId },
      });
    });
    throw APIError.invalidArgument("decision request expired");
  }

  // 3. Authority must still be enabled
  await resolveEnabledAuthority(dr.authorityKey, ctx);

  // 4. Executor must have permission and active grant
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.decisionDecide);
  const cap = await memberCoversCapability(ctx.workforceMemberId!, dr.authorityKey, ctx);
  if (!cap) {
    throw APIError.permissionDenied("executor does not have active grant for this authority");
  }

  // 5. Requester cannot execute
  if ((dr.approvalPolicySnapshot as ApprovalPolicy).requester_cannot_execute && ctx.workforceMemberId === String(dr.requestedByWorkforceMemberId)) {
    throw APIError.permissionDenied("requester cannot execute this decision");
  }

  // 6. Re-check approval policy (grants may have expired)
  const allApprovals = await db.query.engagementDecisionRequestApprovals.findMany({
    where: eq(schema.engagementDecisionRequestApprovals.decisionRequestId, drId),
  });
  assertApprovalPolicySatisfied(
    dr.approvalPolicySnapshot as ApprovalPolicy,
    allApprovals.map((a) => ({
      workforceMemberId: a.workforceMemberId,
      capability: a.capability,
      decision: a.decision,
    })),
  );

  // All guards passed: execute
  const executionRef = `noop_${drId}`;

  const [updated] = await db.transaction(async (tx) => {
    // approved -> execution_pending -> executed
    const [pending] = await tx
      .update(schema.engagementDecisionRequests)
      .set({ status: "execution_pending" as any })
      .where(eq(schema.engagementDecisionRequests.id, drId))
      .returning();

    await tx.insert(schema.engagementDecisionRequestEvents).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      decisionRequestId: drId,
      eventType: "execution_started",
      actor: { kind: "user", id: ctx.workforceMemberId },
    });

    const [executed] = await tx
      .update(schema.engagementDecisionRequests)
      .set({
        status: "executed" as any,
        executionRef,
        executedByWorkforceMemberId: BigInt(ctx.workforceMemberId!),
      })
      .where(eq(schema.engagementDecisionRequests.id, drId))
      .returning();

    await tx.insert(schema.engagementDecisionRequestEvents).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      decisionRequestId: drId,
      eventType: "executed",
      actor: { kind: "user", id: ctx.workforceMemberId },
    });

    return [executed];
  });

  return rowToDTO(updated, allApprovals);
}

export async function expireDueDecisionRequests(): Promise<number> {
  const now = new Date();

  const dueRequests = await db.query.engagementDecisionRequests.findMany({
    where: and(
      inArray(schema.engagementDecisionRequests.status, ["submitted", "under_review", "needs_information", "approved", "execution_pending"]),
      lt(schema.engagementDecisionRequests.approvalDeadline, now),
    ),
  });

  if (dueRequests.length === 0) {
    return 0;
  }

  const ids = dueRequests.map((r) => r.id);

  await db.transaction(async (tx) => {
    await tx
      .update(schema.engagementDecisionRequests)
      .set({ status: "expired" as any })
      .where(inArray(schema.engagementDecisionRequests.id, ids));

    for (const dr of dueRequests) {
      await tx.insert(schema.engagementDecisionRequestEvents).values({
        id: BigInt(generateSnowflake()),
        workspaceId: dr.workspaceId,
        decisionRequestId: dr.id,
        eventType: "expired",
        actor: { kind: "system", id: "engagement-housekeeping" },
      });
    }
  });

  return ids.length;
}

async function getDecisionRequestInternal(id: bigint, ctx: TenantContext): Promise<any> {
  const dr = await db.query.engagementDecisionRequests.findFirst({
    where: and(eq(schema.engagementDecisionRequests.workspaceId, BigInt(ctx.workspaceId)), eq(schema.engagementDecisionRequests.id, id)),
  });

  if (!dr) {
    throw APIError.notFound(`decision request ${id} not found`);
  }

  return dr;
}

function rowToDTO(row: any, approvals: any[]): DR_DTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    threadId: row.threadId ? String(row.threadId) : null,
    requestType: row.requestType,
    status: row.status as DRStatus,
    contactId: row.contactId ? String(row.contactId) : null,
    accountId: row.accountId ? String(row.accountId) : null,
    leadId: row.leadId ? String(row.leadId) : null,
    opportunityId: row.opportunityId ? String(row.opportunityId) : null,
    customerId: row.customerId ? String(row.customerId) : null,
    policySnapshotRef: row.policySnapshotRef,
    factsRef: row.factsRef,
    evidenceRefs: row.evidenceRefs || [],
    options: row.options || [],
    recommendationRef: row.recommendationRef,
    requestedByWorkforceMemberId: String(row.requestedByWorkforceMemberId),
    authorityKey: row.authorityKey,
    authorityVersion: row.authorityVersion,
    approvalPolicySnapshot: row.approvalPolicySnapshot as ApprovalPolicy,
    approvalDeadline: row.approvalDeadline ? (row.approvalDeadline instanceof Date ? row.approvalDeadline.toISOString() : row.approvalDeadline) : null,
    decision: row.decision,
    decisionReason: row.decisionReason,
    approvedAt: row.approvedAt ? (row.approvedAt instanceof Date ? row.approvedAt.toISOString() : row.approvedAt) : null,
    executedByWorkforceMemberId: row.executedByWorkforceMemberId ? String(row.executedByWorkforceMemberId) : null,
    executionRef: row.executionRef,
    correlationId: row.correlationId,
    approvals: approvals.map((a: any) => ({
      workforceMemberId: String(a.workforceMemberId),
      capability: a.capability,
      decision: a.decision,
      decidedAt: a.decidedAt instanceof Date ? a.decidedAt.toISOString() : a.decidedAt,
    })),
  };
}
