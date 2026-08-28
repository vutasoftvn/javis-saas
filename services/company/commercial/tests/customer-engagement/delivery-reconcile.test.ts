import { describe, expect, it, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementMessages,
  engagementOutboundDeliveries,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { runHousekeepingTick } from "../../services/customer-engagement/housekeeping.service";
import { registerChannelAdapter } from "../../services/customer-engagement/channel-adapters/registry";
import { ZaloChannelAdapter } from "../../services/customer-engagement/channel-adapters/zalo-channel.adapter";

describe("Delivery Reconcile Housekeeping Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Reconcile Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  async function createSentDelivery(opts: {
    externalMessageId: string;
    createdAt?: Date;
  }) {
    const threadId = generateSnowflake();
    const messageId = generateSnowflake();
    const deliveryId = generateSnowflake();

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    await db.insert(engagementMessages).values({
      id: messageId,
      workspaceId: wsId,
      threadId,
      direction: "outbound",
      visibility: "customer",
      senderKind: "agent",
      body: "Test outbound message",
      bodyContentHash: "hash_msg",
      deliveryState: "sent",
      externalMessageId: opts.externalMessageId,
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_key_${messageId}`,
      createdAt: opts.createdAt || new Date(Date.now() - 20 * 60 * 1000), // 20m ago
    });

    await db.insert(engagementOutboundDeliveries).values({
      id: deliveryId,
      workspaceId: wsId,
      threadId,
      messageId,
      channelType: "zalo",
      status: "sent",
      externalMessageId: opts.externalMessageId,
      createdAt: opts.createdAt || new Date(Date.now() - 20 * 60 * 1000), // 20m ago
      idempotencyKey: `del_key_${deliveryId}`,
    });

    return { deliveryId, messageId };
  }

  it("should reconcile sent delivery to delivered when provider reports delivered", async () => {
    const fakeExtId = `zmsg_rec_delivered_${generateSnowflake()}`;
    const fixture = await createSentDelivery({ externalMessageId: fakeExtId });

    class MockDeliveredAdapter extends ZaloChannelAdapter {
      override async getDeliveryStatus(id: string): Promise<"delivered" | "failed" | "unknown"> {
        if (id === fakeExtId) return "delivered";
        return "unknown";
      }
    }
    registerChannelAdapter("zalo", new MockDeliveredAdapter());

    const stats = await runHousekeepingTick(10);
    expect(stats.delivered).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture.deliveryId));
    expect(delivery.status).toBe("delivered");
    expect(delivery.deliveredAt).toBeDefined();

    const [msg] = await db
      .select()
      .from(engagementMessages)
      .where(eq(engagementMessages.id, fixture.messageId));
    expect(msg.deliveryState).toBe("delivered");
  });

  it("should reconcile sent delivery to failed with provider_reported_failure when provider reports failed", async () => {
    const fakeExtId = `zmsg_rec_failed_${generateSnowflake()}`;
    const fixture = await createSentDelivery({ externalMessageId: fakeExtId });

    class MockFailedAdapter extends ZaloChannelAdapter {
      override async getDeliveryStatus(id: string): Promise<"delivered" | "failed" | "unknown"> {
        if (id === fakeExtId) return "failed";
        return "unknown";
      }
    }
    registerChannelAdapter("zalo", new MockFailedAdapter());

    const stats = await runHousekeepingTick(10);
    expect(stats.failed).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture.deliveryId));
    expect(delivery.status).toBe("failed");
    expect(delivery.deadLetterReason).toBe("provider_reported_failure");
  });

  it("should assume delivered after 24h when provider delivery status is unknown", async () => {
    const fakeExtId = `zmsg_rec_unknown_24h_${generateSnowflake()}`;
    const createdAt25hAgo = new Date(Date.now() - 25 * 3600 * 1000);
    const fixture = await createSentDelivery({
      externalMessageId: fakeExtId,
      createdAt: createdAt25hAgo,
    });

    class MockUnknownAdapter extends ZaloChannelAdapter {
      override async getDeliveryStatus(_id: string): Promise<"delivered" | "failed" | "unknown"> {
        return "unknown";
      }
    }
    registerChannelAdapter("zalo", new MockUnknownAdapter());

    const stats = await runHousekeepingTick(10);
    expect(stats.assumedDelivered).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture.deliveryId));
    expect(delivery.status).toBe("delivered");
    expect(delivery.deliveredAt).toBeDefined();
    expect(delivery.lastError).toBe("assumed_delivered");
  });
});
