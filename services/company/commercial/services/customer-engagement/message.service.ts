import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { createHash } from "node:crypto";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { TenantContext } from "../../../shared/types/tenant_context";
import {
  buildMessageSentEvent,
  buildMessageReceivedEvent,
  buildThreadStatusChangedEvent,
} from "../../../shared/events/customer-engagement-events";
import { RETENTION_TRANSCRIPT_DAYS } from "./sla.service";
import { loadThread } from "./thread.service";

const { engagementMessages, engagementOutboundDeliveries, engagementThreads, engagementInboxes } = schema;

export interface MessageDTO {
  id: string;
  threadId: string;
  direction: string;
  visibility: string;
  senderKind: string;
  body: string;
  deliveryState: string | null;
  idempotencyKey: string;
  createdAt: string;
}

function toMessageDTO(r: typeof engagementMessages.$inferSelect): MessageDTO {
  return {
    id: String(r.id),
    threadId: String(r.threadId),
    direction: r.direction,
    visibility: r.visibility,
    senderKind: r.senderKind,
    body: r.body,
    deliveryState: r.deliveryState,
    idempotencyKey: r.idempotencyKey,
    createdAt: r.createdAt.toISOString(),
  };
}

function actorOf(ctx: TenantContext) {
  return { kind: "user" as const, id: ctx.workforceMemberId ?? ctx.userId };
}

async function findExisting(threadId: string, key: string, ctx: TenantContext) {
  const [row] = await db.select().from(engagementMessages).where(and(
    eq(engagementMessages.threadId, BigInt(threadId)),
    eq(engagementMessages.idempotencyKey, key),
    eq(engagementMessages.workspaceId, BigInt(ctx.workspaceId)),
  )).limit(1);
  return row ? toMessageDTO(row) : null;
}

export async function postInternalNote(
  params: { threadId: string; body: string; idempotencyKey: string },
  ctx: TenantContext,
): Promise<MessageDTO> {
  // Check if already exists
  const existing = await findExisting(params.threadId, params.idempotencyKey, ctx);
  if (existing) return existing;

  // Load thread scoped
  const thread = await loadThread(params.threadId, ctx);

  // Calculate retention
  const createdAt = new Date();
  const retentionUntil = new Date(createdAt.getTime() + RETENTION_TRANSCRIPT_DAYS * 86400000);

  // Create message
  const id = BigInt(generateSnowflake());
  const bodyContentHash = createHash("sha256").update(params.body).digest("hex");

  const [row] = await db.insert(engagementMessages).values({
    id,
    workspaceId: BigInt(ctx.workspaceId),
    threadId: BigInt(params.threadId),
    direction: "system",
    visibility: "internal",
    senderKind: "workforce_member",
    senderRef: ctx.workforceMemberId ?? ctx.userId,
    body: params.body,
    bodyContentHash,
    deliveryState: null,
    idempotencyKey: params.idempotencyKey,
    retentionUntil,
    createdAt,
  }).returning();
  if (!row) throw APIError.internal("failed to create internal note");

  return toMessageDTO(row);
}

export async function sendPublicMessage(
  params: { threadId: string; body: string; idempotencyKey: string },
  ctx: TenantContext,
): Promise<MessageDTO> {
  // Check if already exists
  const existing = await findExisting(params.threadId, params.idempotencyKey, ctx);
  if (existing) return existing;

  // Load thread and inbox scoped
  const thread = await loadThread(params.threadId, ctx);
  const [inbox] = await db.select().from(engagementInboxes).where(and(
    eq(engagementInboxes.id, thread.inboxId),
    eq(engagementInboxes.workspaceId, BigInt(ctx.workspaceId)),
  )).limit(1);
  if (!inbox) throw APIError.notFound("inbox not found");

  // Calculate retention
  const createdAt = new Date();
  const retentionUntil = new Date(createdAt.getTime() + RETENTION_TRANSCRIPT_DAYS * 86400000);

  // Create message and delivery in transaction
  const id = BigInt(generateSnowflake());
  const bodyContentHash = createHash("sha256").update(params.body).digest("hex");

  const row = await db.transaction(async (tx) => {
    const [msg] = await tx.insert(engagementMessages).values({
      id,
      workspaceId: BigInt(ctx.workspaceId),
      threadId: BigInt(params.threadId),
      direction: "outbound",
      visibility: "customer",
      senderKind: "workforce_member",
      senderRef: ctx.workforceMemberId ?? ctx.userId,
      body: params.body,
      bodyContentHash,
      deliveryState: "queued",
      idempotencyKey: params.idempotencyKey,
      retentionUntil,
      createdAt,
    }).returning();
    if (!msg) throw APIError.internal("failed to create message");

    // Create delivery
    await tx.insert(engagementOutboundDeliveries).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      messageId: id,
      threadId: BigInt(params.threadId),
      channelType: inbox.channelType,
      idempotencyKey: `snd_${id}`,
      status: "queued",
    });

    // Emit event
    await appendOutboxEvent(
      tx as any,
      buildMessageSentEvent(
        {
          threadId: params.threadId,
          workspaceId: String(ctx.workspaceId),
          messageId: String(id),
          correlationId: thread.correlationId,
        },
        actorOf(ctx),
      ),
    );

    return msg;
  });

  return toMessageDTO(row);
}

export async function recordInboundMessage(
  params: { threadId: string; body: string; idempotencyKey: string; senderRef?: string; externalMessageId?: string },
  ctx: TenantContext,
): Promise<MessageDTO> {
  // Check if already exists
  const existing = await findExisting(params.threadId, params.idempotencyKey, ctx);
  if (existing) return existing;

  // Load thread scoped
  const thread = await loadThread(params.threadId, ctx);

  // Calculate retention
  const createdAt = new Date();
  const retentionUntil = new Date(createdAt.getTime() + RETENTION_TRANSCRIPT_DAYS * 86400000);

  // Create message in transaction
  const id = BigInt(generateSnowflake());
  const bodyContentHash = createHash("sha256").update(params.body).digest("hex");

  const row = await db.transaction(async (tx) => {
    const [msg] = await tx.insert(engagementMessages).values({
      id,
      workspaceId: BigInt(ctx.workspaceId),
      threadId: BigInt(params.threadId),
      direction: "inbound",
      visibility: "customer",
      senderKind: "customer",
      senderRef: params.senderRef ?? null,
      body: params.body,
      bodyContentHash,
      deliveryState: null,
      idempotencyKey: params.idempotencyKey,
      externalMessageId: params.externalMessageId ?? null,
      retentionUntil,
      createdAt,
    }).returning();
    if (!msg) throw APIError.internal("failed to create inbound message");

    // Update thread last_customer_msg_at
    await tx.update(engagementThreads).set({
      lastCustomerMsgAt: createdAt,
      updatedAt: createdAt,
    }).where(and(
      eq(engagementThreads.id, BigInt(params.threadId)),
      eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
    ));

    // If thread is resolved, reopen it
    if (thread.status === "resolved") {
      const { engagementThreadTransitions, engagementThreadOutcomes } = schema;

      // Update status
      await tx.update(engagementThreads).set({
        status: "open",
        updatedAt: createdAt,
      }).where(and(
        eq(engagementThreads.id, BigInt(params.threadId)),
        eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
      ));

      // Record transition
      await tx.insert(engagementThreadTransitions).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ctx.workspaceId),
        threadId: BigInt(params.threadId),
        actor: actorOf(ctx),
        reasonCode: "reopened_by_inbound",
        previousState: "resolved",
        currentState: "open",
        correlationId: thread.correlationId,
      });

      // Record outcome
      await tx.insert(engagementThreadOutcomes).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ctx.workspaceId),
        threadId: BigInt(params.threadId),
        intent: null,
        resolutionCode: null,
        escalationReason: "reopened",
      });

      // Emit status changed event
      await appendOutboxEvent(
        tx as any,
        buildThreadStatusChangedEvent(
          {
            threadId: params.threadId,
            workspaceId: String(ctx.workspaceId),
            previousState: "resolved",
            currentState: "open",
            correlationId: thread.correlationId,
          },
          actorOf(ctx),
        ),
      );
    }

    // Emit message received event
    await appendOutboxEvent(
      tx as any,
      buildMessageReceivedEvent(
        {
          threadId: params.threadId,
          workspaceId: String(ctx.workspaceId),
          messageId: String(id),
          correlationId: thread.correlationId,
        },
        actorOf(ctx),
      ),
    );

    return msg;
  });

  return toMessageDTO(row);
}
