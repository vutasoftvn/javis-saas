import { and, eq, isNull, lt, sql } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementOutboundDeliveries,
  engagementMessages,
} from "../../../shared/db/schema/customer-engagement";
import { getChannelAdapter } from "./channel-adapters/registry";

export interface HousekeepingTickStats {
  reconciled: number;
  delivered: number;
  failed: number;
  assumedDelivered: number;
}

export async function runHousekeepingTick(limit = 20): Promise<HousekeepingTickStats> {
  const stats: HousekeepingTickStats = {
    reconciled: 0,
    delivered: 0,
    failed: 0,
    assumedDelivered: 0,
  };

  // Find deliveries in sent state without delivered_at older than 10 minutes
  const rows = await db.execute(sql`
    SELECT * FROM engagement.engagement_outbound_deliveries
    WHERE status = 'sent'
      AND delivered_at IS NULL
      AND created_at < now() - interval '10 minutes'
    ORDER BY created_at ASC
    LIMIT ${limit};
  `);

  const deliveries = rows.rows as any[];
  stats.reconciled = deliveries.length;

  for (const delivery of deliveries) {
    const deliveryId = BigInt(delivery.id);
    const messageId = BigInt(delivery.message_id);
    const externalMessageId = delivery.external_message_id;
    const createdAt = new Date(delivery.created_at);

    if (!externalMessageId) continue;

    try {
      const adapter = getChannelAdapter(delivery.channel_type);
      const status = await adapter.getDeliveryStatus(externalMessageId);

      if (status === "delivered") {
        await db
          .update(engagementOutboundDeliveries)
          .set({ status: "delivered", deliveredAt: new Date() })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        await db
          .update(engagementMessages)
          .set({ deliveryState: "delivered" })
          .where(eq(engagementMessages.id, messageId));

        stats.delivered++;
      } else if (status === "failed") {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: "provider_reported_failure",
            lastError: "provider reported failure during reconcile",
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        await db
          .update(engagementMessages)
          .set({ deliveryState: "failed" })
          .where(eq(engagementMessages.id, messageId));

        stats.failed++;
      } else {
        // Status is unknown — if older than 24h, assume delivered best effort
        const ageHours = (Date.now() - createdAt.getTime()) / (1000 * 3600);
        if (ageHours >= 24) {
          await db
            .update(engagementOutboundDeliveries)
            .set({
              status: "delivered",
              deliveredAt: new Date(),
              lastError: "assumed_delivered",
            })
            .where(eq(engagementOutboundDeliveries.id, deliveryId));

          await db
            .update(engagementMessages)
            .set({ deliveryState: "delivered" })
            .where(eq(engagementMessages.id, messageId));

          stats.assumedDelivered++;
        }
      }
    } catch {
      // Ignore provider query failure during housekeeping tick; will retry next tick
    }
  }

  return stats;
}
