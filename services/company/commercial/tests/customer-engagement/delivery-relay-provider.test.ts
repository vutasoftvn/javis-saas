import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementChannelEndpoints,
  engagementThreads,
  engagementMessages,
  engagementOutboundDeliveries,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { deliveryRelayTick } from "../../services/customer-engagement/delivery-relay.service";
import { setCustomConnectorGrantRunner } from "../../services/customer-engagement/connector-grant.client";
import { setCustomChannelSecretResolver } from "../../services/customer-engagement/channel-secret";
import {
  registerChannelAdapter,
  resetChannelAdapterRegistryForTest,
} from "../../services/customer-engagement/channel-adapters/registry";
import { ZaloChannelAdapter } from "../../services/customer-engagement/channel-adapters/zalo-channel.adapter";

describe("Delivery Relay Real Provider Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let endpointId: bigint;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();
    endpointId = generateSnowflake();

    setCustomConnectorGrantRunner(async (params) => {
      if (params.connectorKey === "zalo_key_valid") {
        return { ok: true, secretRef: "sec_zalo_grant_ok" };
      }
      return { ok: false, secretRef: null };
    });

    setCustomChannelSecretResolver(async (ref) => {
      if (ref === "sec_zalo_grant_ok") {
        return "mock_access_token_secret_123";
      }
      return null;
    });

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Outbound Zalo Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementChannelEndpoints).values({
      id: endpointId,
      workspaceId: wsId,
      inboxId,
      providerRef: "oa_outbound_test",
      connectorKey: "zalo_key_valid",
      verificationConfigRef: "verif_ref_1",
      status: "active",
    });
  });

  // Dọn dẹp các double mutable module-level (registry adapter, connector-grant runner, secret resolver)
  // để test case này không rò rỉ trạng thái sang test case/khác file chạy sau — đây chính là nguồn gây
  // flakiness của bộ test outbound relay khi các fixture khác workspace vô tình bị ảnh hưởng.
  afterEach(() => {
    resetChannelAdapterRegistryForTest();
    setCustomConnectorGrantRunner(null);
    setCustomChannelSecretResolver(null);
  });

  async function createFixture(opts?: {
    body?: string;
    status?: string;
    deliveryStatus?: string;
    messageDeliveryState?: string;
    connectorKey?: string;
    attemptCount?: number;
    maxAttempts?: number;
  }) {
    const threadId = generateSnowflake();
    const messageId = generateSnowflake();
    const deliveryId = generateSnowflake();
    const userRef = `zalo_user_${threadId}`;

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      externalConversationRef: userRef,
      status: opts?.status || "open",
      correlationId: `corr_${threadId}`,
    });

    await db.insert(engagementMessages).values({
      id: messageId,
      workspaceId: wsId,
      threadId,
      direction: "outbound",
      visibility: "customer",
      senderKind: "agent",
      body: opts?.body || "Xin chào quý khách!",
      bodyContentHash: "hash_msg",
      deliveryState: opts?.messageDeliveryState || "queued",
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_key_${messageId}`,
    });

    await db.insert(engagementOutboundDeliveries).values({
      id: deliveryId,
      workspaceId: wsId,
      threadId,
      messageId,
      channelType: "zalo",
      status: opts?.deliveryStatus || "queued",
      attemptCount: opts?.attemptCount ?? 0,
      maxAttempts: opts?.maxAttempts ?? 3,
      idempotencyKey: `del_key_${deliveryId}`,
    });

    return { threadId, messageId, deliveryId };
  }

  it("should process queued delivery, assert grant, call adapter and mark sent", async () => {
    registerChannelAdapter(
      "zalo",
      new ZaloChannelAdapter({
        fetchRunner: async () => ({
          status: 200,
          json: async () => ({ error: 0, data: { message_id: "zalo_msg_remote_99" } }),
        }),
      })
    );

    const fixture = await createFixture();

    const stats = await deliveryRelayTick("worker-1", 10, wsId);
    expect(stats.sent).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture.deliveryId));
    expect(delivery.status).toBe("sent");
    expect(delivery.externalMessageId).toBe("zalo_msg_remote_99");
    expect(delivery.deliveredAt).toBeDefined();

    const [msg] = await db
      .select()
      .from(engagementMessages)
      .where(eq(engagementMessages.id, fixture.messageId));
    expect(msg.deliveryState).toBe("sent");
    expect(msg.externalMessageId).toBe("zalo_msg_remote_99");
  });

  it("should fail immediately on permanent 401 error and record deadLetterReason", async () => {
    registerChannelAdapter(
      "zalo",
      new ZaloChannelAdapter({
        fetchRunner: async () => ({
          status: 401,
          json: async () => ({ error: -216, message: "Invalid Access Token" }),
        }),
      })
    );

    const fixture = await createFixture();

    const stats = await deliveryRelayTick("worker-1", 10, wsId);
    expect(stats.failed).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture.deliveryId));
    expect(delivery.status).toBe("failed");
    expect(delivery.deadLetterReason).toContain("Invalid Access Token");
  });

  it("should retry transient error with backoff and mark failed only after max_attempts", async () => {
    registerChannelAdapter(
      "zalo",
      new ZaloChannelAdapter({
        fetchRunner: async () => ({
          status: 429,
          json: async () => ({ error: -32, message: "Rate limit exceeded" }),
        }),
      })
    );

    // 1. Attempt 1/3 -> still queued with visibilityTimeoutAt in future
    const fixture1 = await createFixture({ attemptCount: 0, maxAttempts: 3 });
    await deliveryRelayTick("worker-1", 10, wsId);

    const [d1] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture1.deliveryId));
    expect(d1.status).toBe("queued");
    expect(d1.attemptCount).toBe(1);
    expect(d1.visibilityTimeoutAt).toBeDefined();

    // 2. Final attempt (already at max_attempts) -> mark failed
    const fixture2 = await createFixture({ attemptCount: 2, maxAttempts: 3 });
    await deliveryRelayTick("worker-1", 10, wsId);

    const [d2] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture2.deliveryId));
    expect(d2.status).toBe("failed");
    expect(d2.deadLetterReason).toContain("Rate limit");
  });

  it("should drop cancelled delivery on takeover before tick", async () => {
    const fixture = await createFixture({ messageDeliveryState: "cancelled" });

    const stats = await deliveryRelayTick("worker-1", 10, wsId);
    expect(stats.dropped).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixture.deliveryId));
    expect(delivery.status).toBe("failed");
    expect(delivery.deadLetterReason).toBe("ownership_changed");
  });

  it("should only dispatch deliveries scoped to the requested workspace, leaving other workspaces queued", async () => {
    registerChannelAdapter(
      "zalo",
      new ZaloChannelAdapter({
        fetchRunner: async () => ({
          status: 200,
          json: async () => ({ error: 0, data: { message_id: "iso_remote_1" } }),
        }),
      })
    );

    // Workspace A: dùng inbox/endpoint zalo do beforeEach tạo sẵn cho wsId.
    const workspaceA = wsId;
    const fixtureA = await createFixture();

    // Workspace B: workspace hoàn toàn độc lập, dùng channel "api" để không cần
    // connector grant / secret resolver riêng — chỉ cần đảm bảo delivery của B
    // không bị relay tick của A đụng vào.
    const workspaceB = generateSnowflake();
    const inboxB = generateSnowflake();
    const threadB = generateSnowflake();
    const messageB = generateSnowflake();
    const deliveryB = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxB,
      workspaceId: workspaceB,
      channelType: "api",
      name: "Isolation Workspace B Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementThreads).values({
      id: threadB,
      workspaceId: workspaceB,
      inboxId: inboxB,
      status: "open",
      correlationId: `corr_${threadB}`,
    });

    await db.insert(engagementMessages).values({
      id: messageB,
      workspaceId: workspaceB,
      threadId: threadB,
      direction: "outbound",
      visibility: "customer",
      senderKind: "agent",
      body: "Workspace B outbound message",
      bodyContentHash: "hash_ws_b",
      deliveryState: "queued",
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_key_${messageB}`,
    });

    await db.insert(engagementOutboundDeliveries).values({
      id: deliveryB,
      workspaceId: workspaceB,
      threadId: threadB,
      messageId: messageB,
      channelType: "api",
      status: "queued",
      attemptCount: 0,
      maxAttempts: 3,
      idempotencyKey: `del_key_${deliveryB}`,
    });

    const result = await deliveryRelayTick("test-worker", 1, workspaceA);
    expect(result.processed).toBe(1);

    const [deliveryAAfter] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, fixtureA.deliveryId));
    expect(deliveryAAfter.status).toBe("sent");

    const [deliveryBAfter] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, deliveryB));
    expect(deliveryBAfter.status).toBe("queued");
  });
});
