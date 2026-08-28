import { describe, expect, it, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import crypto from "node:crypto";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementChannelEndpoints,
  engagementThreads,
  engagementOutboundDeliveries,
  engagementMessages,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import {
  createChannelEndpointApi,
  activateChannelEndpointApi,
  pauseChannelEndpointApi,
  listChannelDeliveriesApi,
  retryChannelDeliveryApi,
} from "../../handlers/customer-engagement/channel-admin.handler";
import {
  setVerificationConfigResolverForTest,
} from "../../services/customer-engagement/channel-adapters/verification";
import {
  setCustomConnectorGrantRunner,
} from "../../services/customer-engagement/connector-grant.client";

describe("Channel Webhook & Admin Handler Tests", () => {
  const secretKey = "test_webhook_secret_key";

  beforeEach(() => {
    setVerificationConfigResolverForTest(async (ref) => {
      if (ref === "valid_verification_ref") {
        return {
          scheme: "hmac_sha256",
          secretRef: ref,
          header: "X-Zalo-Signature",
          encoding: "hex",
          signedPayload: "raw",
          skewSeconds: 300,
        };
      }
      return null;
    });

    setCustomConnectorGrantRunner(async (params) => {
      if (params.connectorKey === "valid_connector_key") {
        return { ok: true, secretRef: "sec_connector_ok" };
      }
      return { ok: false, secretRef: null };
    });
  });

  it("should create channel endpoint with status pending", async () => {
    const user = await createTestSession({ displayName: "Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    const inboxId = generateSnowflake();
    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Zalo Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    const ep = await createChannelEndpointApi({
      workspaceId,
      authorization,
      inboxId: inboxId.toString(),
      providerRef: "oa_admin_test_1",
      connectorKey: "valid_connector_key",
      inboundRoutingKey: `oa_admin_test_${workspaceId}`,
      verificationConfigRef: "valid_verification_ref",
      autoCreateContact: false,
    });

    expect(ep.status).toBe("pending");
    expect(ep.connectorKey).toBe("valid_connector_key");
  });

  it("should fail-closed when activating without valid verification config or connector grant", async () => {
    const user = await createTestSession({ displayName: "Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    const inboxId = generateSnowflake();
    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Zalo Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    // 1. Endpoint with invalid verification ref
    const epId1 = generateSnowflake();
    await db.insert(engagementChannelEndpoints).values({
      id: epId1,
      workspaceId: wsId,
      inboxId,
      providerRef: "oa_test_bad_verif",
      connectorKey: "valid_connector_key",
      verificationConfigRef: "non_existent_verif_ref",
      status: "pending",
    });

    await expect(
      activateChannelEndpointApi({ id: epId1.toString(), workspaceId, authorization })
    ).rejects.toThrow(/verification config/i);

    // 2. Endpoint with invalid connector key
    const epId2 = generateSnowflake();
    await db.insert(engagementChannelEndpoints).values({
      id: epId2,
      workspaceId: wsId,
      inboxId,
      providerRef: "oa_test_bad_conn",
      connectorKey: "invalid_connector_key",
      verificationConfigRef: "valid_verification_ref",
      status: "pending",
    });

    await expect(
      activateChannelEndpointApi({ id: epId2.toString(), workspaceId, authorization })
    ).rejects.toThrow(/connector grant/i);

    // 3. Endpoint with both valid -> succeeds and turns active
    const epId3 = generateSnowflake();
    await db.insert(engagementChannelEndpoints).values({
      id: epId3,
      workspaceId: wsId,
      inboxId,
      providerRef: "oa_test_valid",
      connectorKey: "valid_connector_key",
      verificationConfigRef: "valid_verification_ref",
      status: "pending",
    });

    const activeEp = await activateChannelEndpointApi({ id: epId3.toString(), workspaceId, authorization });
    expect(activeEp.status).toBe("active");

    // 4. Pause endpoint
    const pausedEp = await pauseChannelEndpointApi({ id: epId3.toString(), workspaceId, authorization });
    expect(pausedEp.status).toBe("paused");
  });

  it("should list failed deliveries and allow workforce member to retry delivery", async () => {
    const user = await createTestSession({ displayName: "Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    const inboxId = generateSnowflake();
    const threadId = generateSnowflake();
    const messageId = generateSnowflake();
    const deliveryId = generateSnowflake();

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Zalo Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

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
      body: "Test message",
      bodyContentHash: "hash_msg_1",
      retentionUntil: new Date(Date.now() + 365 * 86400000),
      idempotencyKey: `msg_key_${messageId}`,
    });

    await db.insert(engagementOutboundDeliveries).values({
      id: deliveryId,
      workspaceId: wsId,
      threadId,
      messageId,
      channelType: "zalo",
      status: "failed",
      attemptCount: 3,
      maxAttempts: 5,
      lastError: "401 Unauthorized - Invalid access token",
      deadLetterReason: "invalid_token",
      idempotencyKey: `del_key_${deliveryId}`,
    });

    const list = await listChannelDeliveriesApi({
      status: "failed",
      workspaceId,
      authorization,
    });
    expect(list.deliveries.length).toBeGreaterThanOrEqual(1);
    const found = list.deliveries.find((d) => d.id === deliveryId.toString());
    expect(found).toBeDefined();
    expect(found?.lastError).toBe("401 Unauthorized - Invalid access token");
    expect(found?.deadLetterReason).toBe("invalid_token");

    // Retry delivery
    const retried = await retryChannelDeliveryApi({
      id: deliveryId.toString(),
      workspaceId,
      authorization,
    });
    expect(retried.status).toBe("queued");
    expect(retried.deadLetterReason).toBeNull();
  });
});
