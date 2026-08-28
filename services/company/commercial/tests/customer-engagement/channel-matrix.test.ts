import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import crypto from "node:crypto";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementChannelEndpoints,
  engagementThreads,
  engagementMessages,
  engagementOutboundDeliveries,
  engagementChannelInboundEvents,
  engagementIdentityReviewItems,
} from "../../../shared/db/schema/customer-engagement";
import { contacts, accounts } from "../../../shared/db/schema/commercial";
import { eventOutbox } from "../../../shared/db/schema/integration";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { ingestInbound } from "../../services/customer-engagement/channel-inbound.service";
import { deliveryRelayTick } from "../../services/customer-engagement/delivery-relay.service";
import { linkThreadIdentity } from "../../services/customer-engagement/channel-identity-sync.service";
import { runHousekeepingTick } from "../../services/customer-engagement/housekeeping.service";
import { setVerificationConfigResolverForTest } from "../../services/customer-engagement/channel-adapters/verification";
import { setCustomConnectorGrantRunner } from "../../services/customer-engagement/connector-grant.client";
import { setCustomChannelSecretResolver } from "../../services/customer-engagement/channel-secret";
import { registerChannelAdapter } from "../../services/customer-engagement/channel-adapters/registry";
import { ZaloChannelAdapter } from "../../services/customer-engagement/channel-adapters/zalo-channel.adapter";
import { activateChannelEndpointApi } from "../../handlers/customer-engagement/channel-admin.handler";

describe("P2 Customer Engagement Channel Matrix Tests", () => {
  const secretKey = "matrix_secret_key";
  let wsId: bigint;
  let inboxId: bigint;
  let endpointId: bigint;
  let routingKey: string;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();
    endpointId = generateSnowflake();
    routingKey = `oa_matrix_${wsId}`;

    setVerificationConfigResolverForTest(async (ref) => {
      if (ref === "verif_cfg_valid") {
        return {
          scheme: "hmac_sha256",
          secretRef: "sec_matrix",
          header: "X-Zalo-Signature",
          encoding: "hex",
          signedPayload: "raw",
          skewSeconds: 300,
        };
      }
      return null;
    });

    process.env["CHANNEL_SECRET_SEC_MATRIX"] = secretKey;

    setCustomConnectorGrantRunner(async (params) => {
      if (params.connectorKey === "connector_matrix_valid") {
        return { ok: true, secretRef: "sec_matrix" };
      }
      return { ok: false, secretRef: null };
    });

    setCustomChannelSecretResolver(async (ref) => {
      if (ref === "sec_matrix") {
        return "mock_matrix_token_999";
      }
      return null;
    });

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Matrix Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    await db.insert(engagementChannelEndpoints).values({
      id: endpointId,
      workspaceId: wsId,
      inboxId,
      providerRef: routingKey,
      inboundRoutingKey: routingKey,
      connectorKey: "connector_matrix_valid",
      verificationConfigRef: "verif_cfg_valid",
      status: "active",
    });
  });

  function signRequest(bodyStr: string) {
    const rawBody = Buffer.from(bodyStr, "utf-8");
    const sig = crypto.createHmac("sha256", secretKey).update(rawBody).digest("hex");
    return {
      rawBody,
      headers: { "x-zalo-signature": `mac=${sig}` },
    };
  }

  it("Scenario 1: Valid Inbound -> 1 thread + 1 message + 1 outbox event + atomic ack", async () => {
    const msgId = `msg_mat_1_${wsId}`;
    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "user_mat_1" },
      message: { msg_id: msgId, text: "Yêu cầu tư vấn sản phẩm" },
      timestamp: Date.now().toString(),
    });

    const res = await ingestInbound("zalo", signRequest(bodyStr));
    expect(res.status).toBe(200);
    expect(res.outcome).toBe("accepted");

    // 1 Message created
    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(and(eq(engagementMessages.workspaceId, wsId), eq(engagementMessages.externalMessageId, msgId)));
    expect(msgs.length).toBe(1);

    // 1 Outbox Event created
    const outbox = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, res.threadId!));
    expect(outbox.length).toBeGreaterThanOrEqual(1);
    expect(outbox[0].eventType).toBe("engagement.message.received.v1");
  });

  it("Scenario 2: Tampered body or invalid signature -> 401 unauthenticated, 0 message created", async () => {
    const rawBody = Buffer.from(
      JSON.stringify({
        oa_id: routingKey,
        sender: { id: "user_mat_tampered" },
        message: { msg_id: `tampered_${wsId}`, text: "Tampered" },
      }),
      "utf-8"
    );
    const req = {
      rawBody,
      headers: { "x-zalo-signature": "mac=invalid_sig_abc123" },
    };

    const res = await ingestInbound("zalo", req);
    expect(res.status).toBe(401);
    expect(res.outcome).toBe("rejected_signature");

    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(and(eq(engagementMessages.workspaceId, wsId), eq(engagementMessages.externalMessageId, `tampered_${wsId}`)));
    expect(msgs.length).toBe(0);
  });

  it("Scenario 3: Replay duplicate delivery ID -> 0 duplicate message, 0 duplicate outbox event", async () => {
    const msgId = `msg_mat_dup_${wsId}`;
    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "user_mat_dup" },
      message: { msg_id: msgId, text: "Replayed delivery" },
      timestamp: Date.now().toString(),
    });

    const res1 = await ingestInbound("zalo", signRequest(bodyStr));
    expect(res1.outcome).toBe("accepted");

    const res2 = await ingestInbound("zalo", signRequest(bodyStr));
    expect(res2.outcome).toBe("duplicate");

    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(and(eq(engagementMessages.workspaceId, wsId), eq(engagementMessages.externalMessageId, msgId)));
    expect(msgs.length).toBe(1);
  });

  it("Scenario 4: Endpoint paused -> 200 dropped_paused and 0 message created", async () => {
    await db
      .update(engagementChannelEndpoints)
      .set({ status: "paused" })
      .where(eq(engagementChannelEndpoints.id, endpointId));

    const msgId = `msg_mat_paused_${wsId}`;
    const bodyStr = JSON.stringify({
      oa_id: routingKey,
      sender: { id: "user_mat_paused" },
      message: { msg_id: msgId, text: "While paused" },
      timestamp: Date.now().toString(),
    });

    const res = await ingestInbound("zalo", signRequest(bodyStr));
    expect(res.status).toBe(200);
    expect(res.outcome).toBe("dropped_paused");

    const msgs = await db
      .select()
      .from(engagementMessages)
      .where(and(eq(engagementMessages.workspaceId, wsId), eq(engagementMessages.externalMessageId, msgId)));
    expect(msgs.length).toBe(0);
  });

  it("Scenario 5: Fail-closed activation without valid verification config or grant", async () => {
    const user = await createTestSession({ displayName: "Matrix Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const wId = user.workspaceId;

    const userInboxId = generateSnowflake();
    await db.insert(engagementInboxes).values({
      id: userInboxId,
      workspaceId: BigInt(wId),
      channelType: "zalo",
      name: "Matrix User Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    const unverifiedEpId = generateSnowflake();
    await db.insert(engagementChannelEndpoints).values({
      id: unverifiedEpId,
      workspaceId: BigInt(wId),
      inboxId: userInboxId,
      providerRef: "oa_unverified",
      connectorKey: "connector_matrix_valid",
      verificationConfigRef: "invalid_verif_ref",
      status: "pending",
    });

    await expect(
      activateChannelEndpointApi({ id: unverifiedEpId.toString(), workspaceId: wId, authorization })
    ).rejects.toThrow(/verification config/i);
  });

  it("Scenario 6: Outbound happy path -> queued to sent with externalMessageId", async () => {
    registerChannelAdapter(
      "zalo",
      new ZaloChannelAdapter({
        fetchRunner: async () => ({
          status: 200,
          json: async () => ({ error: 0, data: { message_id: "matrix_out_remote_1" } }),
        }),
      })
    );

    const threadId = generateSnowflake();
    const messageId = generateSnowflake();
    const deliveryId = generateSnowflake();

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      externalConversationRef: "user_matrix_out",
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
      body: "Outbound Matrix Test",
      bodyContentHash: "hash_mat",
      deliveryState: "queued",
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_${messageId}`,
    });

    await db.insert(engagementOutboundDeliveries).values({
      id: deliveryId,
      workspaceId: wsId,
      threadId,
      messageId,
      channelType: "zalo",
      status: "queued",
      idempotencyKey: `del_${deliveryId}`,
    });

    const stats = await deliveryRelayTick("worker-mat", 10);
    expect(stats.sent).toBeGreaterThanOrEqual(1);

    const [delivery] = await db
      .select()
      .from(engagementOutboundDeliveries)
      .where(eq(engagementOutboundDeliveries.id, deliveryId));
    expect(delivery.status).toBe("sent");
    expect(delivery.externalMessageId).toBe("matrix_out_remote_1");
  });

  it("Scenario 7: CRM Identity Sync: link exact match vs ambiguous review vs auto-create", async () => {
    const threadId1 = generateSnowflake();
    const threadId2 = generateSnowflake();
    const threadId3 = generateSnowflake();

    await db.insert(engagementThreads).values([
      { id: threadId1, workspaceId: wsId, inboxId, status: "open", correlationId: `corr_${threadId1}` },
      { id: threadId2, workspaceId: wsId, inboxId, status: "open", correlationId: `corr_${threadId2}` },
      { id: threadId3, workspaceId: wsId, inboxId, status: "open", correlationId: `corr_${threadId3}` },
    ]);

    const ctx = {
      workspaceId: wsId.toString(),
      userId: "user_matrix",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_mat_ctx",
    };

    // 1. Exact match
    const contactId = generateSnowflake();
    await db.insert(contacts).values({
      id: contactId,
      workspaceId: wsId,
      name: "Matrix Contact",
      email: "matrix@example.com",
    });

    const linkRes = await linkThreadIdentity(
      threadId1.toString(),
      { email: "matrix@example.com", emailVerified: true },
      ctx,
      { autoCreateContact: false }
    );
    expect(linkRes.contactId).toBe(contactId.toString());
    expect(linkRes.created).toBe(false);

    // 2. Ambiguous match -> review item
    const cA = generateSnowflake();
    const cB = generateSnowflake();
    await db.insert(contacts).values([
      { id: cA, workspaceId: wsId, name: "Dup Phone A", phone: "+84977111222" },
      { id: cB, workspaceId: wsId, name: "Dup Phone B", phone: "+84977111222" },
    ]);

    const ambigRes = await linkThreadIdentity(
      threadId2.toString(),
      { phone: "+84977111222" },
      ctx,
      { autoCreateContact: false }
    );
    expect(ambigRes.contactId).toBeNull();
    expect(ambigRes.reviewItemId).toBeDefined();

    // 3. No match + autoCreateContact: true -> create new Contact without touching others
    const autoRes = await linkThreadIdentity(
      threadId3.toString(),
      { phone: "+84912999888", externalUserName: "New Auto User" },
      ctx,
      { autoCreateContact: true, channelType: "zalo" }
    );
    expect(autoRes.created).toBe(true);
    expect(autoRes.contactId).toBeDefined();

    const [createdContact] = await db
      .select()
      .from(contacts)
      .where(eq(contacts.id, BigInt(autoRes.contactId!)));
    expect(createdContact.name).toBe("New Auto User");
    expect(createdContact.source).toBe("engagement:zalo");
  });
});
