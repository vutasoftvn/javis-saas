import { api, Header } from "encore.dev/api";
import {
  ENGAGEMENT_PERMISSIONS,
  requireEngagementPermission,
} from "../../services/customer-engagement/rbac";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import * as channelEndpointSvc from "../../services/customer-engagement/channel-endpoints.service";

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

    return channelEndpointSvc.createChannelEndpoint({
      workspaceId: params.workspaceId,
      inboxId: params.inboxId,
      providerRef: params.providerRef,
      connectorKey: params.connectorKey,
      inboundRoutingKey: params.inboundRoutingKey,
      verificationConfigRef: params.verificationConfigRef,
      autoCreateContact: params.autoCreateContact,
      skewSeconds: params.skewSeconds,
    });
  }
);

export const activateChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/:id/activate" },
  async (params: ActivateChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.activateChannelEndpoint(
      { workspaceId: params.workspaceId, id: params.id },
      ctx
    );
  }
);

export const pauseChannelEndpointApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/channels/:id/pause" },
  async (params: PauseChannelEndpointParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.pauseChannelEndpoint({
      workspaceId: params.workspaceId,
      id: params.id,
    });
  }
);

export const listChannelDeliveriesApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/channels/:id/deliveries" },
  async (params: ListChannelDeliveriesParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);

    return channelEndpointSvc.listChannelDeliveries({
      workspaceId: params.workspaceId,
      id: params.id,
      status: params.status,
    });
  }
);

export const retryChannelDeliveryApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/deliveries/:id/retry" },
  async (params: RetryChannelDeliveryParams) => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.CHANNEL_MANAGE);

    return channelEndpointSvc.retryChannelDelivery({
      workspaceId: params.workspaceId,
      id: params.id,
    });
  }
);
