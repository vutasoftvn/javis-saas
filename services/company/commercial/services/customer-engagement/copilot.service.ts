import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import { engagementCopilotInvocations } from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import {
  buildCopilotRequestedEvent,
  buildCopilotFeedbackEvent,
  type Actor,
} from "../../../shared/events/customer-engagement-events";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { ENGAGEMENT_PERMISSIONS, requireEngagementPermission } from "./rbac";
import { assertCopilotUsable } from "./copilot-settings.service";
import { getThreadContextForAgent } from "./thread-context.service";
import { dispatchCopilotRun } from "./copilot-cosa-client";

export interface CopilotInvocationDTO {
  id: string;
  workspaceId: string;
  threadId: string;
  requestedByWorkforceMemberId: string;
  intent: string;
  runId: string;
  agentSpecId: string;
  agentSpecHash: string;
  status: string;
  artifactRef: string | null;
  summaryRef: string | null;
  identityVerified: boolean;
  feedback: string | null;
  feedbackEditedRef: string | null;
  feedbackByWorkforceMemberId: string | null;
  feedbackAt: string | null;
  correlationId: string;
  createdAt: string;
  updatedAt: string;
}

function mapInvocationRowToDTO(row: typeof engagementCopilotInvocations.$inferSelect): CopilotInvocationDTO {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    threadId: row.threadId.toString(),
    requestedByWorkforceMemberId: row.requestedByWorkforceMemberId.toString(),
    intent: row.intent,
    runId: row.runId,
    agentSpecId: row.agentSpecId,
    agentSpecHash: row.agentSpecHash,
    status: row.status,
    artifactRef: row.artifactRef,
    summaryRef: row.summaryRef,
    identityVerified: row.identityVerified,
    feedback: row.feedback,
    feedbackEditedRef: row.feedbackEditedRef,
    feedbackByWorkforceMemberId: row.feedbackByWorkforceMemberId ? row.feedbackByWorkforceMemberId.toString() : null,
    feedbackAt: row.feedbackAt ? row.feedbackAt.toISOString() : null,
    correlationId: row.correlationId,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function requestCopilot(
  threadId: string,
  input: { intent: string },
  ctx: TenantContext
): Promise<{ invocationId: string; runId: string }> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.COPILOT_REQUEST);

  // 1. Fail-closed settings assertion
  const settings = await assertCopilotUsable(input.intent, ctx);

  // 2. Load minimized thread context
  const context = await getThreadContextForAgent(threadId, ctx);

  // 3. Dispatch run to COSA
  const dispatchRes = await dispatchCopilotRun({
    workspaceId: ctx.workspaceId,
    threadRef: {
      threadId,
      contactId: context.contactId,
    },
    intent: input.intent,
    knowledgeScope: settings.knowledgeScope,
    identityVerified: context.identityVerified,
    correlationId: context.thread.correlationId,
  });

  const invocationId = generateSnowflake();
  const wsId = BigInt(ctx.workspaceId);
  const tId = BigInt(threadId);
  const requestedBy = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : 0n;

  const actor: Actor = {
    kind: "user",
    id: ctx.userId || ctx.workforceMemberId || "system",
  };

  // 4. Record invocation and outbox event in transaction
  await db.transaction(async (tx) => {
    await tx.insert(engagementCopilotInvocations).values({
      id: invocationId,
      workspaceId: wsId,
      threadId: tId,
      requestedByWorkforceMemberId: requestedBy,
      intent: input.intent,
      runId: dispatchRes.runId,
      agentSpecId: settings.allowedAgentSpecId!,
      agentSpecHash: settings.allowedAgentSpecHash!,
      status: "dispatched",
      identityVerified: context.identityVerified,
      correlationId: context.thread.correlationId,
    });

    const event = buildCopilotRequestedEvent(
      {
        threadId,
        workspaceId: ctx.workspaceId,
        invocationId: invocationId.toString(),
        runId: dispatchRes.runId,
        intent: input.intent,
        correlationId: context.thread.correlationId,
      },
      actor
    );

    await appendOutboxEvent(tx, event);
  });

  return {
    invocationId: invocationId.toString(),
    runId: dispatchRes.runId,
  };
}

export async function getCopilotInvocation(
  id: string,
  ctx: TenantContext
): Promise<CopilotInvocationDTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.COPILOT_REQUEST);

  const wsId = BigInt(ctx.workspaceId);
  const invId = BigInt(id);

  const rows = await db
    .select()
    .from(engagementCopilotInvocations)
    .where(
      and(
        eq(engagementCopilotInvocations.id, invId),
        eq(engagementCopilotInvocations.workspaceId, wsId)
      )
    )
    .limit(1);

  if (rows.length === 0) {
    throw APIError.notFound(`Copilot invocation ${id} not found`);
  }

  return mapInvocationRowToDTO(rows[0]);
}

export async function applyCopilotResult(input: {
  runId: string;
  status: string;
  artifactRef?: string | null;
  summaryRef?: string | null;
}): Promise<void> {
  const rows = await db
    .select()
    .from(engagementCopilotInvocations)
    .where(eq(engagementCopilotInvocations.runId, input.runId))
    .limit(1);

  if (rows.length === 0) {
    throw APIError.notFound(`Copilot invocation with runId ${input.runId} not found`);
  }

  await db
    .update(engagementCopilotInvocations)
    .set({
      status: input.status,
      artifactRef: input.artifactRef ?? null,
      summaryRef: input.summaryRef ?? null,
      updatedAt: new Date(),
    })
    .where(eq(engagementCopilotInvocations.runId, input.runId));
}

export async function recordCopilotFeedback(
  id: string,
  input: { feedback: "accepted" | "edited" | "rejected"; editedRef?: string },
  ctx: TenantContext
): Promise<CopilotInvocationDTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.COPILOT_REQUEST);

  const wsId = BigInt(ctx.workspaceId);
  const invId = BigInt(id);

  const rows = await db
    .select()
    .from(engagementCopilotInvocations)
    .where(
      and(
        eq(engagementCopilotInvocations.id, invId),
        eq(engagementCopilotInvocations.workspaceId, wsId)
      )
    )
    .limit(1);

  if (rows.length === 0) {
    throw APIError.notFound(`Copilot invocation ${id} not found`);
  }

  const existing = rows[0];
  const now = new Date();
  const feedbackBy = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const actor: Actor = {
    kind: "user",
    id: ctx.userId || ctx.workforceMemberId || "system",
  };

  let updatedRow: typeof engagementCopilotInvocations.$inferSelect;

  await db.transaction(async (tx) => {
    const [u] = await tx
      .update(engagementCopilotInvocations)
      .set({
        feedback: input.feedback,
        feedbackEditedRef: input.editedRef ?? null,
        feedbackByWorkforceMemberId: feedbackBy,
        feedbackAt: now,
        updatedAt: now,
      })
      .where(eq(engagementCopilotInvocations.id, invId))
      .returning();

    updatedRow = u;

    const event = buildCopilotFeedbackEvent(
      {
        threadId: existing.threadId.toString(),
        workspaceId: ctx.workspaceId,
        invocationId: id,
        feedback: input.feedback,
        correlationId: existing.correlationId,
      },
      actor
    );

    await appendOutboxEvent(tx, event);
  });

  return mapInvocationRowToDTO(updatedRow!);
}
