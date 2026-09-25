import { api, Header, APIError } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../../shared/auth/worker-service-auth";
import { requireWorkspaceAccess, requireFounderCommand } from "../../shared/auth/workspace-access";
import {
  commandFounderAsset,
  handleAssetStatusCallback,
  getFounderAssetEvents,
  type AssetKind,
  type AssetOperation,
  type AssetRef,
  type FounderAssetCommandResult,
  type AssetStatusCallbackPayload,
} from "../services/founder-asset-authoring.service";



export interface CommandFounderAssetParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
  assetKind: AssetKind;
  operation: AssetOperation;
  assetRef: AssetRef;
  expectedVersion?: number;
  idempotencyKey: string;
  reason: string;
  metadata?: Record<string, any>;
}

export const commandFounderAssetApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/founder/assets/commands",
  },
  async (params: CommandFounderAssetParams): Promise<FounderAssetCommandResult> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "command_founder_asset");
    if (tenantCtx.isAiAgent) {
      throw APIError.permissionDenied("only human founders may issue asset authoring commands");
    }

    return commandFounderAsset(tenantCtx, params);
  }
);

export interface HandleAssetStatusCallbackParams extends AssetStatusCallbackPayload {
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
}

export const handleAssetStatusCallbackApi = api(
  {
    expose: true,
    method: "POST",
    path: "/internal/operations/founder/assets/status-callback",
  },
  async (params: HandleAssetStatusCallbackParams): Promise<{ success: boolean }> => {
    await requireWorkerServiceAuth({ serviceToken: params.serviceToken, authorization: params.authorization });
    await handleAssetStatusCallback(params);
    return { success: true };
  }
);

export interface GetFounderAssetEventsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  commandId?: string;
}

export const getFounderAssetEventsApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/founder/assets/events",
  },
  async (params: GetFounderAssetEventsParams): Promise<{ events: any[] }> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "get_founder_asset_events");
    const events = await getFounderAssetEvents(tenantCtx.workspaceId, params.commandId);
    return { events };
  }
);
