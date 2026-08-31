import { APIError } from "encore.dev/api";
import { and, eq, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveVerificationConfig } from "./channel-adapters/verification";
import { assertConnectorGrant } from "./connector-grant.client";

const { engagementChannelEndpoints, engagementOutboundDeliveries } = schema;

export async function createChannelEndpoint(input: {
  workspaceId: string;
  inboxId: string;
  providerRef: string;
  connectorKey: string;
  inboundRoutingKey?: string;
  verificationConfigRef?: string;
  autoCreateContact?: boolean;
  skewSeconds?: number;
}) {
  const wsId = BigInt(input.workspaceId);
  const inboxId = BigInt(input.inboxId);
  const id = generateSnowflake();

  const [row] = await db
    .insert(engagementChannelEndpoints)
    .values({
      id,
      workspaceId: wsId,
      inboxId,
      providerRef: input.providerRef,
      connectorKey: input.connectorKey,
      inboundRoutingKey: input.inboundRoutingKey,
      verificationConfigRef: input.verificationConfigRef,
      autoCreateContact: input.autoCreateContact ?? false,
      skewSeconds: input.skewSeconds ?? 300,
      status: "pending",
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    inboxId: row.inboxId.toString(),
    providerRef: row.providerRef,
    connectorKey: row.connectorKey,
    inboundRoutingKey: row.inboundRoutingKey,
    verificationConfigRef: row.verificationConfigRef,
    status: row.status,
    autoCreateContact: row.autoCreateContact,
    skewSeconds: row.skewSeconds,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export async function activateChannelEndpoint(input: {
  workspaceId: string;
  id: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const epId = BigInt(input.id);

  const rows = await db
    .select()
    .from(engagementChannelEndpoints)
    .where(
      and(
        eq(engagementChannelEndpoints.id, epId),
        eq(engagementChannelEndpoints.workspaceId, wsId)
      )
    );

  if (rows.length === 0) {
    throw APIError.notFound("Channel endpoint not found");
  }

  const endpoint = rows[0];

  if (!endpoint.verificationConfigRef) {
    throw APIError.failedPrecondition("Endpoint missing verificationConfigRef");
  }
  try {
    await resolveVerificationConfig(endpoint.verificationConfigRef);
  } catch (err: any) {
    throw APIError.failedPrecondition(`Cannot activate endpoint: ${err.message}`);
  }

  if (!endpoint.connectorKey) {
    throw APIError.failedPrecondition("Endpoint missing connectorKey");
  }
  const grantRes = await assertConnectorGrant({
    workspaceId: input.workspaceId,
    conversationId: "system",
    connectorKey: endpoint.connectorKey,
    action: "send",
  });
  if (!grantRes.ok) {
    throw APIError.failedPrecondition(`Cannot activate endpoint: connector grant assertion failed for key ${endpoint.connectorKey}`);
  }

  const [updated] = await db
    .update(engagementChannelEndpoints)
    .set({ status: "active", updatedAt: new Date() })
    .where(eq(engagementChannelEndpoints.id, epId))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    inboxId: updated.inboxId.toString(),
    providerRef: updated.providerRef,
    connectorKey: updated.connectorKey,
    inboundRoutingKey: updated.inboundRoutingKey,
    verificationConfigRef: updated.verificationConfigRef,
    status: updated.status,
    updatedAt: updated.updatedAt,
  };
}

export async function pauseChannelEndpoint(input: {
  workspaceId: string;
  id: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const epId = BigInt(input.id);

  const [updated] = await db
    .update(engagementChannelEndpoints)
    .set({ status: "paused", updatedAt: new Date() })
    .where(
      and(
        eq(engagementChannelEndpoints.id, epId),
        eq(engagementChannelEndpoints.workspaceId, wsId)
      )
    )
    .returning();

  if (!updated) {
    throw APIError.notFound("Channel endpoint not found");
  }

  return {
    id: updated.id.toString(),
    status: updated.status,
    updatedAt: updated.updatedAt,
  };
}

export async function listChannelDeliveries(input: {
  workspaceId: string;
  status?: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const conditions = [eq(engagementOutboundDeliveries.workspaceId, wsId)];
  if (input.status) {
    conditions.push(eq(engagementOutboundDeliveries.status, input.status));
  }

  const rows = await db
    .select()
    .from(engagementOutboundDeliveries)
    .where(and(...conditions))
    .orderBy(desc(engagementOutboundDeliveries.createdAt))
    .limit(100);

  return {
    deliveries: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      messageId: r.messageId.toString(),
      channelType: r.channelType,
      status: r.status,
      attemptCount: r.attemptCount,
      maxAttempts: r.maxAttempts,
      lastError: r.lastError,
      deadLetterReason: r.deadLetterReason,
      externalMessageId: r.externalMessageId,
      createdAt: r.createdAt,
    })),
  };
}

export async function retryChannelDelivery(input: {
  workspaceId: string;
  id: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const deliveryId = BigInt(input.id);

  const [updated] = await db
    .update(engagementOutboundDeliveries)
    .set({
      status: "queued",
      deadLetterReason: null,
      visibilityTimeoutAt: new Date(),
      claimToken: null,
    })
    .where(
      and(
        eq(engagementOutboundDeliveries.id, deliveryId),
        eq(engagementOutboundDeliveries.workspaceId, wsId)
      )
    )
    .returning();

  if (!updated) {
    throw APIError.notFound("Delivery not found");
  }

  return {
    id: updated.id.toString(),
    status: updated.status,
    attemptCount: updated.attemptCount,
    deadLetterReason: updated.deadLetterReason,
  };
}
