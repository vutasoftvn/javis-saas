import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import crypto from "node:crypto";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementChannelEndpoints,
  engagementThreads,
  engagementMessages,
  engagementChannelInboundEvents,
} from "../../../shared/db/schema/customer-engagement";
import { eventOutbox } from "../../../shared/db/schema/integration";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { ingestInbound } from "../../services/customer-engagement/channel-inbound.service";
import { setVerificationConfigResolverForTest } from "../../services/customer-engagement/channel-adapters/verification";

describe("Channel Inbound Ingest Service Tests", () => {
  const secretKey = "test_inbound_zalo_secret";
  let wsId: bigint;
  let inboxId: bigint;
  let endpointId: bigint;
  let routingKey: string;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();
    endpointId = generateSnowflake();
    routingKey = `oa_${wsId}`;

    setVerificationConfigResolverForTest(async (ref) => ({
      scheme: "hmac_sha256",
      secretRef: ref,
      header: "X-Zalo-Signature",
      encoding: "hex",
      signedPayload: "raw",
      skewSeconds: 300,
    }));

    process.env["CHANNEL_SECRET_SEC_ZALO_TEST"] = secretKey;

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Zalo OA Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementChannelEndpoints).values({
      id: endpointId,
      workspaceId: wsId,
      inboxId,
      providerRef: routingKey,
      inboundRoutingKey: routingKey,
      connectorKey: "zalo_connector_1",
      verificationConfigRef: "sec_zalo_test",
      status: "active",
    });
  });

  function signPayload(bodyStr: string): { rawBody: Buffer; headers: Record<string, string> } {
    const rawBody = Buffer.from(bodyStr, "utf-8");
    const sig = crypto.createHmac("sha256", secretKey).update(rawBody).digest("hex");
    return {
      rawBody,
      headers: { "x-zalo-signature": `mac=${sig}` },
    };
  }

  it("should atomically create thread, message, outbox event and inbound event on valid inbound", async () => {
    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "customer_user_11" },
      message: { msg_id: "msg_in_101", text: "Tôi cần hỗ trợ đơn hàng" },
      timestamp: Date.now().toString(),
    });
    const req = signPayload(bodyStr);

    const res = await ingestInbound("zalo", req);
    expect(res.status).toBe(200);
    expect(res.outcome).toBe("accepted");
    expect(res.threadId).toBeDefined();
    expect(res.messageId).toBeDefined();

    // 1. Thread created
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, BigInt(res.threadId!)));
    expect(thread.externalConversationRef).toBe("customer_user_11");
    expect(thread.status).toBe("open");

    // 2. Message created
    const [msg] = await db
      .select()
      .from(engagementMessages)
      .where(eq(engagementMessages.id, BigInt(res.messageId!)));
    expect(msg.body).toBe("Tôi cần hỗ trợ đơn hàng");
    expect(msg.direction).toBe("inbound");
    expect(msg.externalMessageId).toBe("msg_in_101");

    // 3. Outbox event created
    const outboxEvents = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, res.threadId!));
    expect(outboxEvents.length).toBeGreaterThanOrEqual(1);
    expect(outboxEvents[0].eventType).toBe("engagement.message.received.v1");

    // 4. Inbound event record
    const [inboundEvt] = await db
      .select()
      .from(engagementChannelInboundEvents)
      .where(eq(engagementChannelInboundEvents.endpointId, endpointId));
    expect(inboundEvt.outcome).toBe("accepted");
    expect(inboundEvt.providerDeliveryId).toBe("msg_in_101");
  });

  it("should deduplicate when duplicate provider delivery id is replayed (0 duplicate message, 0 duplicate outbox)", async () => {
    const msgId = `msg_in_dup_${wsId}`;
    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "customer_user_11" },
      message: { msg_id: msgId, text: "Tin nhắn gửi lặp lại" },
      timestamp: Date.now().toString(),
    });
    const req = signPayload(bodyStr);

    const first = await ingestInbound("zalo", req);
    expect(first.status).toBe(200);
    expect(first.outcome).toBe("accepted");

    // Replay exact same request
    const replay = await ingestInbound("zalo", req);
    expect(replay.status).toBe(200);
    expect(replay.outcome).toBe("duplicate");

    // Message count should still be 1
    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(
        and(
          eq(engagementMessages.workspaceId, wsId),
          eq(engagementMessages.externalMessageId, msgId)
        )
      );
    expect(msgs.length).toBe(1);
  });

  it("should reject invalid signature with status 401 and write rejected_signature event", async () => {
    const msgId = `msg_in_bad_sig_${wsId}`;
    const rawBody = Buffer.from(
      JSON.stringify({
        oa_id: routingKey,
        sender: { id: "customer_user_11" },
        message: { msg_id: msgId, text: "Fake signature" },
      }),
      "utf-8"
    );
    const req = {
      rawBody,
      headers: { "x-zalo-signature": "mac=invalid_signature_hex" },
    };

    const res = await ingestInbound("zalo", req);
    expect(res.status).toBe(401);
    expect(res.outcome).toBe("rejected_signature");

    // 0 messages created
    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(
        and(
          eq(engagementMessages.workspaceId, wsId),
          eq(engagementMessages.externalMessageId, msgId)
        )
      );
    expect(msgs.length).toBe(0);
  });

  it("should drop message and return 200 dropped_paused when endpoint is paused", async () => {
    await db
      .update(engagementChannelEndpoints)
      .set({ status: "paused" })
      .where(eq(engagementChannelEndpoints.id, endpointId));

    const msgId = `msg_in_paused_${wsId}`;
    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "customer_user_11" },
      message: { msg_id: msgId, text: "Tin nhắn khi paused" },
      timestamp: Date.now().toString(),
    });
    const req = signPayload(bodyStr);

    const res = await ingestInbound("zalo", req);
    expect(res.status).toBe(200);
    expect(res.outcome).toBe("dropped_paused");

    // 0 messages created
    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(
        and(
          eq(engagementMessages.workspaceId, wsId),
          eq(engagementMessages.externalMessageId, msgId)
        )
      );
    expect(msgs.length).toBe(0);
  });

  it("should reopen thread if previous status was resolved", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      externalConversationRef: "customer_user_reopen",
      status: "resolved",
      correlationId: "corr-reopen",
    });

    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "customer_user_reopen" },
      message: { msg_id: "msg_in_reopen_1", text: "Cần hỏi thêm" },
      timestamp: Date.now().toString(),
    });
    const req = signPayload(bodyStr);

    const res = await ingestInbound("zalo", req);
    expect(res.status).toBe(200);
    expect(res.threadId).toBe(threadId.toString());

    const [updatedThread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(updatedThread.status).toBe("open");
  });
});
