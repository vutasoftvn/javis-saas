import { api, Header, APIError } from "encore.dev/api";
import { and, eq, desc } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementChannelEndpoints,
  engagementOutboundDeliveries,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveVerificationConfig } from "../../services/customer-engagement/channel-adapters/verification";
import { assertConnectorGrant } from "../../services/customer-engagement/connector-grant.client";
import {
  ENGAGEMENT_PERMISSIONS,
  requireEngagementPermission,
} from "../../services/customer-engagement/rbac";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";

export interface CreateChannelEndpointParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  inboxId: string;
  providerRef: string;
  connectorKey: string;
  inboundRoutingKey?: string;
  verificationConfigRef?: string;
  autoCreateContact?: boolean;
  skewSeconds?: number;
}

export interface ActivateChannelEndpointParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  id: string;
}

export interface PauseChannelEndpointParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  id: string;
}

export interface ListChannelDeliveriesParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  id?: string;
  status?: string;
}

export interface RetryChannelDeliveryParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
  id: string;
}

export const createChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels" },
  async (params: CreateChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    const wsId = BigInt(params.workspaceId);
    const inboxId = BigInt(params.inboxId);
    const id = generateSnowflake();

    const [row] = await db
      .insert(engagementChannelEndpoints)
      .values({
        id,
        workspaceId: wsId,
        inboxId,
        providerRef: params.providerRef,
        connectorKey: params.connectorKey,
        inboundRoutingKey: params.inboundRoutingKey,
        verificationConfigRef: params.verificationConfigRef,
        autoCreateContact: params.autoCreateContact ?? false,
        skewSeconds: params.skewSeconds ?? 300,
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
);

export const activateChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/:id/activate" },
  async (params: ActivateChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    const wsId = BigInt(params.workspaceId);
    const epId = BigInt(params.id);

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

    // 1. Fail-closed check: verification config resolvable
    if (!endpoint.verificationConfigRef) {
      throw APIError.failedPrecondition("Endpoint missing verificationConfigRef");
    }
    try {
      await resolveVerificationConfig(endpoint.verificationConfigRef);
    } catch (err: any) {
      throw APIError.failedPrecondition(`Cannot activate endpoint: ${err.message}`);
    }

    // 2. Fail-closed check: connector grant active in Control Plane
    if (!endpoint.connectorKey) {
      throw APIError.failedPrecondition("Endpoint missing connectorKey");
    }
    const grantRes = await assertConnectorGrant({
      workspaceId: params.workspaceId,
      conversationId: "system",
      connectorKey: endpoint.connectorKey,
      action: "send",
    });
    if (!grantRes.ok) {
      throw APIError.failedPrecondition(`Cannot activate endpoint: connector grant assertion failed for key ${endpoint.connectorKey}`);
    }

    // 3. Mark active
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
);

export const pauseChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/:id/pause" },
  async (params: PauseChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    const wsId = BigInt(params.workspaceId);
    const epId = BigInt(params.id);

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
);

export const listChannelDeliveriesApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/channels/:id/deliveries" },
  async (params: ListChannelDeliveriesParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);

    const wsId = BigInt(params.workspaceId);

    const conditions = [eq(engagementOutboundDeliveries.workspaceId, wsId)];
    if (params.status) {
      conditions.push(eq(engagementOutboundDeliveries.status, params.status));
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
);

export const retryChannelDeliveryApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/deliveries/:id/retry" },
  async (params: RetryChannelDeliveryParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    const wsId = BigInt(params.workspaceId);
    const deliveryId = BigInt(params.id);

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
);
