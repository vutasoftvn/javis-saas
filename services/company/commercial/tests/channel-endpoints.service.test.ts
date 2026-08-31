import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, schema } from "../db";
import {
  createChannelEndpoint,
  activateChannelEndpoint,
  pauseChannelEndpoint,
  listChannelDeliveries,
  retryChannelDelivery,
} from "../services/customer-engagement/channel-endpoints.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { setCustomConnectorGrantRunner } from "../services/customer-engagement/connector-grant.client";

describe("Channel Endpoints Service", () => {
  let wsId: string;
  let inboxId: string;

  beforeEach(async () => {
    const wsIdBig = generateSnowflake();
    wsId = wsIdBig.toString();

    inboxId = generateSnowflake().toString();

    // Setup: Create an inbox for the channel endpoint
    await db
      .insert(schema.engagementInboxes)
      .values({
        id: BigInt(inboxId),
        workspaceId: wsIdBig,
        channelType: "slack",
        name: "Test Inbox",
        slaPolicy: { firstResponseMinutes: 60 },
      });

    // Mock connector grant runner to always return ok
    setCustomConnectorGrantRunner(async () => ({
      ok: true,
      secretRef: "secret_ref_123",
    }));

    await db.delete(schema.engagementOutboundDeliveries);
    await db.delete(schema.engagementChannelEndpoints);
  });

  afterEach(async () => {
    // Clear mock
    setCustomConnectorGrantRunner(null);

    await db.delete(schema.engagementOutboundDeliveries);
    await db.delete(schema.engagementChannelEndpoints);
    await db.delete(schema.engagementInboxes);
  });

  it("createChannelEndpoint inserts row and returns with string IDs", async () => {
    const result = await createChannelEndpoint({
      workspaceId: wsId,
      inboxId,
      providerRef: "slack",
      connectorKey: "key_abc",
      verificationConfigRef: "cfg_001",
      autoCreateContact: false,
      skewSeconds: 300,
    });

    expect(result.id).toBeDefined();
    expect(result.workspaceId).toBe(wsId);
    expect(result.status).toBe("pending");
  });

  it("activateChannelEndpoint throws notFound when endpoint missing", async () => {
    const nonexistentId = generateSnowflake().toString();
    await expect(
      activateChannelEndpoint({
        workspaceId: wsId,
        id: nonexistentId,
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("pauseChannelEndpoint updates status to paused", async () => {
    const created = await createChannelEndpoint({
      workspaceId: wsId,
      inboxId,
      providerRef: "slack",
      connectorKey: "key_abc",
      verificationConfigRef: "cfg_001",
    });

    const result = await pauseChannelEndpoint({
      workspaceId: wsId,
      id: created.id,
    });

    expect(result.status).toBe("paused");
  });

  it("listChannelDeliveries returns empty list when no deliveries", async () => {
    const result = await listChannelDeliveries({
      workspaceId: wsId,
      status: "sent",
    });

    expect(result.deliveries).toBeDefined();
    expect(Array.isArray(result.deliveries)).toBe(true);
  });

  it("retryChannelDelivery throws notFound when delivery missing", async () => {
    const nonexistentDeliveryId = generateSnowflake().toString();
    await expect(
      retryChannelDelivery({
        workspaceId: wsId,
        id: nonexistentDeliveryId,
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
