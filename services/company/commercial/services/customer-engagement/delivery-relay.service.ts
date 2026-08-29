import { randomUUID } from "node:crypto";
import { and, eq, or, isNull, lt, sql } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementOutboundDeliveries,
  engagementMessages,
  engagementThreads,
  engagementChannelEndpoints,
} from "../../../shared/db/schema/customer-engagement";
import { getChannelAdapter } from "./channel-adapters/registry";
import { assertConnectorGrant } from "./connector-grant.client";
import { resolveChannelSecret } from "./channel-secret";

export interface DeliveryRelayTickStats {
  processed: number;
  sent: number;
  failed: number;
  dropped: number;
}

export async function deliveryRelayTick(
  workerId: string,
  limit = 10,
  workspaceId?: bigint | string,
): Promise<DeliveryRelayTickStats> {
  const stats: DeliveryRelayTickStats = {
    processed: 0,
    sent: 0,
    failed: 0,
    dropped: 0,
  };

  const claimToken = `${workerId}:${randomUUID().slice(0, 12)}`;
  const lockTimeout = new Date(Date.now() + 60000); // 60s lock
  const workspaceScope = workspaceId === undefined
    ? sql``
    : sql` AND workspace_id = ${typeof workspaceId === "string" ? BigInt(workspaceId) : workspaceId}`;

  // 1. Claim due queued deliveries using raw query with FOR UPDATE SKIP LOCKED
  const claimedRows = await db.execute(sql`
    WITH due AS (
      SELECT id FROM engagement.engagement_outbound_deliveries
      WHERE status = 'queued'
        AND (visibility_timeout_at IS NULL OR visibility_timeout_at < now())
        ${workspaceScope}
      ORDER BY created_at
      FOR UPDATE SKIP LOCKED
      LIMIT ${limit}
    )
    UPDATE engagement.engagement_outbound_deliveries
    SET claim_token = ${claimToken},
        visibility_timeout_at = ${lockTimeout},
        attempt_count = attempt_count + 1
    FROM due
    WHERE engagement.engagement_outbound_deliveries.id = due.id
    RETURNING engagement.engagement_outbound_deliveries.*;
  `);

  const deliveries = claimedRows.rows as any[];
  stats.processed = deliveries.length;

  for (const delivery of deliveries) {
    const deliveryId = BigInt(delivery.id);
    const workspaceId = BigInt(delivery.workspace_id);
    const messageId = BigInt(delivery.message_id);
    const threadId = BigInt(delivery.thread_id);
    const attemptCount = Number(delivery.attempt_count);
    const maxAttempts = Number(delivery.max_attempts);

    // 2. Load message and thread
    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(
        and(
          eq(engagementMessages.id, messageId),
          eq(engagementMessages.workspaceId, workspaceId)
        )
      );

    const threads = await db
      .select()
      .from(engagementThreads)
      .where(
        and(
          eq(engagementThreads.id, threadId),
          eq(engagementThreads.workspaceId, workspaceId)
        )
      );

    if (msgs.length === 0 || threads.length === 0) {
      await db
        .update(engagementOutboundDeliveries)
        .set({ status: "failed", deadLetterReason: "missing_message_or_thread", claimToken: null })
        .where(eq(engagementOutboundDeliveries.id, deliveryId));
      stats.failed++;
      continue;
    }

    const message = msgs[0];
    const thread = threads[0];

    // 3. Ownership / Cancellation re-check
    if (message.deliveryState === "cancelled" || delivery.status === "cancelled") {
      await db
        .update(engagementOutboundDeliveries)
        .set({ status: "failed", deadLetterReason: "ownership_changed", claimToken: null })
        .where(eq(engagementOutboundDeliveries.id, deliveryId));
      stats.dropped++;
      continue;
    }

    const adapter = getChannelAdapter(delivery.channel_type);

    // 4. API channel path (no external connector)
    if (delivery.channel_type === "api") {
      const res = await adapter.sendOutbound(
        {
          deliveryId: deliveryId.toString(),
          threadId: threadId.toString(),
          body: message.body,
        },
        null
      );

      if (res.status === "sent") {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "sent",
            externalMessageId: res.externalMessageId,
            deliveredAt: new Date(),
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        await db
          .update(engagementMessages)
          .set({ deliveryState: "sent", externalMessageId: res.externalMessageId })
          .where(eq(engagementMessages.id, messageId));

        stats.sent++;
      } else {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: (res as any).error || "API send failed",
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      }
      continue;
    }

    // 5. Real provider path (e.g. Zalo OA)
    const endpoints = await db
      .select()
      .from(engagementChannelEndpoints)
      .where(
        and(
          eq(engagementChannelEndpoints.inboxId, thread.inboxId),
          eq(engagementChannelEndpoints.workspaceId, workspaceId),
          eq(engagementChannelEndpoints.status, "active")
        )
      );

    if (endpoints.length === 0 || !endpoints[0].connectorKey) {
      if (attemptCount >= maxAttempts) {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: "no_active_channel_endpoint",
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      } else {
        const backoffMs = Math.min(300000, 5000 * Math.pow(2, attemptCount));
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "queued",
            visibilityTimeoutAt: new Date(Date.now() + backoffMs),
            lastError: "no active channel endpoint for inbox",
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      }
      continue;
    }

    const endpoint = endpoints[0];

    // 5.1 Assert connector grant in Control Plane
    const grantRes = await assertConnectorGrant({
      workspaceId: workspaceId.toString(),
      conversationId: threadId.toString(),
      connectorKey: endpoint.connectorKey,
      action: "send",
    });

    if (!grantRes.ok || !grantRes.secretRef) {
      if (attemptCount >= maxAttempts) {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: "connector_grant_unavailable",
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      } else {
        const backoffMs = Math.min(300000, 5000 * Math.pow(2, attemptCount));
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "queued",
            visibilityTimeoutAt: new Date(Date.now() + backoffMs),
            lastError: "connector grant unavailable",
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      }
      continue;
    }

    // 5.2 Resolve channel secret token
    let token: string;
    try {
      token = await resolveChannelSecret(grantRes.secretRef);
    } catch (err: any) {
      if (attemptCount >= maxAttempts) {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: `secret_resolution_error: ${err.message}`,
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      } else {
        const backoffMs = Math.min(300000, 5000 * Math.pow(2, attemptCount));
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "queued",
            visibilityTimeoutAt: new Date(Date.now() + backoffMs),
            lastError: err.message,
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));
        stats.failed++;
      }
      continue;
    }

    // 5.3 Send outbound via adapter
    const sendResult = await adapter.sendOutbound(
      {
        deliveryId: deliveryId.toString(),
        threadId: threadId.toString(),
        body: message.body,
        externalConversationRef: thread.externalConversationRef,
        endpointProviderRef: endpoint.providerRef,
      },
      token
    );

    if (sendResult.status === "sent") {
      await db
        .update(engagementOutboundDeliveries)
        .set({
          status: "sent",
          externalMessageId: sendResult.externalMessageId,
          deliveredAt: new Date(),
          claimToken: null,
        })
        .where(eq(engagementOutboundDeliveries.id, deliveryId));

      await db
        .update(engagementMessages)
        .set({ deliveryState: "sent", externalMessageId: sendResult.externalMessageId })
        .where(eq(engagementMessages.id, messageId));

      stats.sent++;
    } else if (sendResult.status === "failed") {
      if (sendResult.permanent || attemptCount >= maxAttempts) {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: sendResult.error,
            lastError: sendResult.error,
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        await db
          .update(engagementMessages)
          .set({ deliveryState: "failed" })
          .where(eq(engagementMessages.id, messageId));

        stats.failed++;
      } else {
        const backoffMs = Math.min(300000, 5000 * Math.pow(2, attemptCount));
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "queued",
            visibilityTimeoutAt: new Date(Date.now() + backoffMs),
            lastError: sendResult.error,
            claimToken: null,
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        stats.failed++;
      }
    }
  }

  return stats;
}
