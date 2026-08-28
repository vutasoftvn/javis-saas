import crypto from "node:crypto";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementChannelEndpoints,
  engagementThreads,
  engagementMessages,
  engagementChannelInboundEvents,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { buildMessageReceivedEvent } from "../../../shared/events/customer-engagement-events";
import { getChannelAdapter } from "./channel-adapters/registry";
import { resolveVerificationConfig } from "./channel-adapters/verification";
import { evaluateRulesSafe } from "./automation/evaluator";

export interface IngestInboundResult {
  status: 200 | 401;
  threadId?: string;
  messageId?: string;
  outcome: "accepted" | "duplicate" | "rejected_signature" | "dropped_paused" | "error";
  error?: string;
}

export async function ingestInbound(
  channelType: string,
  ctxReq: { rawBody: Buffer; headers: Record<string, string | undefined> }
): Promise<IngestInboundResult> {
  const rawHash = crypto.createHash("sha256").update(ctxReq.rawBody).digest("hex");
  const adapter = getChannelAdapter(channelType);

  // 1. Peek routing key
  const routingKey = adapter.peekRoutingKey ? adapter.peekRoutingKey(ctxReq.rawBody, ctxReq.headers) : null;

  // 2. Find matching endpoint
  const endpoints = await db
    .select()
    .from(engagementChannelEndpoints)
    .where(
      routingKey
        ? eq(engagementChannelEndpoints.inboundRoutingKey, routingKey)
        : eq(engagementChannelEndpoints.providerRef, "default")
    );

  if (endpoints.length === 0) {
    // Endpoint not found — return 200 error so provider doesn't spin retry loop
    return { status: 200, outcome: "error", error: `no endpoint matching routing key: ${routingKey}` };
  }

  const endpoint = endpoints[0];

  // 3. Status check
  if (endpoint.status !== "active") {
    const inboundEventId = generateSnowflake();
    await db.insert(engagementChannelInboundEvents).values({
      id: inboundEventId,
      workspaceId: endpoint.workspaceId,
      endpointId: endpoint.id,
      providerDeliveryId: `dropped_${Date.now()}`,
      outcome: "dropped_paused",
      rawHash,
    });
    return { status: 200, outcome: "dropped_paused" };
  }

  // 4. Verify signature
  let verified;
  try {
    const config = await resolveVerificationConfig(endpoint.verificationConfigRef || "default");
    verified = await adapter.verifyInbound(ctxReq, config);
  } catch (err: any) {
    const inboundEventId = generateSnowflake();
    await db.insert(engagementChannelInboundEvents).values({
      id: inboundEventId,
      workspaceId: endpoint.workspaceId,
      endpointId: endpoint.id,
      providerDeliveryId: `failed_sig_${Date.now()}`,
      outcome: "rejected_signature",
      error: err.message || "Invalid signature",
      rawHash,
    });
    return { status: 401, outcome: "rejected_signature", error: err.message };
  }

  // 5. Dedupe check at raw inbound event level
  const providerDeliveryId = verified.externalMessageId || `del_${Date.now()}`;
  const inboundEventId = generateSnowflake();

  try {
    await db.insert(engagementChannelInboundEvents).values({
      id: inboundEventId,
      workspaceId: endpoint.workspaceId,
      endpointId: endpoint.id,
      providerDeliveryId,
      providerMessageId: verified.externalMessageId,
      outcome: "accepted",
      rawHash,
    });
  } catch {
    // Duplicate provider delivery ID conflict
    const existing = await db
      .select()
      .from(engagementChannelInboundEvents)
      .where(
        and(
          eq(engagementChannelInboundEvents.endpointId, endpoint.id),
          eq(engagementChannelInboundEvents.providerDeliveryId, providerDeliveryId)
        )
      );

    const existingRow = existing[0];
    return {
      status: 200,
      outcome: "duplicate",
      threadId: existingRow?.threadId?.toString(),
      messageId: existingRow?.messageId?.toString(),
    };
  }

  // 6. Atomic transaction: Thread + Message + Outbox
  const norm = await adapter.normalizeInbound(verified);
  const actor = { kind: "system" as const, id: `channel:${channelType}` };

  let finalThreadId: bigint;
  let finalMessageId: bigint;

  await db.transaction(async (tx) => {
    // 6.1 Find or open thread
    const threads = await tx
      .select()
      .from(engagementThreads)
      .where(
        and(
          eq(engagementThreads.inboxId, endpoint.inboxId),
          eq(engagementThreads.externalConversationRef, norm.externalConversationRef)
        )
      );

    if (threads.length === 0) {
      finalThreadId = generateSnowflake();
      await tx.insert(engagementThreads).values({
        id: finalThreadId,
        workspaceId: endpoint.workspaceId,
        inboxId: endpoint.inboxId,
        externalConversationRef: norm.externalConversationRef,
        status: "open",
        priority: "normal",
        activeMode: "team_queue",
        correlationId: `corr_${finalThreadId}`,
      });
    } else {
      const existingThread = threads[0];
      finalThreadId = existingThread.id;
      if (existingThread.status === "resolved") {
        await tx
          .update(engagementThreads)
          .set({ status: "open", updatedAt: new Date() })
          .where(eq(engagementThreads.id, finalThreadId));
      }
    }

    // 6.2 Check layer-2 duplicate message
    const existingMsgs = await tx
      .select()
      .from(engagementMessages)
      .where(
        and(
          eq(engagementMessages.workspaceId, endpoint.workspaceId),
          eq(engagementMessages.externalMessageId, norm.externalMessageId)
        )
      );

    if (existingMsgs.length > 0) {
      finalMessageId = existingMsgs[0].id;
    } else {
      finalMessageId = generateSnowflake();
      const bodyContentHash = crypto.createHash("sha256").update(norm.body).digest("hex");

      await tx.insert(engagementMessages).values({
        id: finalMessageId,
        workspaceId: endpoint.workspaceId,
        threadId: finalThreadId,
        direction: "inbound",
        visibility: "customer",
        senderKind: "customer",
        senderRef: norm.senderRef,
        body: norm.body,
        bodyContentHash,
        retentionUntil: new Date(Date.now() + 365 * 86400000),
        idempotencyKey: `inbound_${finalMessageId}`,
        externalMessageId: norm.externalMessageId,
      });

      // 6.3 Append Outbox Event
      const outboxEvt = buildMessageReceivedEvent(
        {
          threadId: finalThreadId.toString(),
          workspaceId: endpoint.workspaceId.toString(),
          messageId: finalMessageId.toString(),
          correlationId: `corr_${finalThreadId}`,
        },
        actor
      );
      await appendOutboxEvent(tx, outboxEvt);
    }

    // 6.4 Update inbound event row with threadId and messageId
    await tx
      .update(engagementChannelInboundEvents)
      .set({
        threadId: finalThreadId,
        messageId: finalMessageId,
        outcome: "accepted",
      })
      .where(eq(engagementChannelInboundEvents.id, inboundEventId));
  });

  // 7. Trigger automation rules safely
  await evaluateRulesSafe(
    { trigger: "message_received", threadId: finalThreadId!.toString() },
    {
      workspaceId: endpoint.workspaceId.toString(),
      userId: "system",
      membershipRole: "system",
      permissions: ["*"],
      correlationId: `corr_${finalThreadId!}`,
    }
  );

  return {
    status: 200,
    outcome: "accepted",
    threadId: finalThreadId!.toString(),
    messageId: finalMessageId!.toString(),
  };
}
