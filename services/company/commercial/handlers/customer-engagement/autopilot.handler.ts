import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  requireEngagementPermission,
  ENGAGEMENT_PERMISSIONS,
} from "../../services/customer-engagement/rbac";
import {
  AutopilotSettingsService,
  AutopilotSettingsDto,
  UpdateAutopilotSettingsInput,
} from "../../services/customer-engagement/autopilot-settings.service";

const autopilotService = new AutopilotSettingsService();

export interface GetAutopilotSettingsParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
}

export interface GetAutopilotSettingsResponse {
  settings: AutopilotSettingsDto;
}

export interface UpdateAutopilotSettingsParams extends UpdateAutopilotSettingsInput {
  authorization: Header<"Authorization">;
  workspaceId: string;
}

export interface UpdateAutopilotSettingsResponse {
  settings: AutopilotSettingsDto;
}

export interface EmergencyKillSwitchParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
}

export interface EmergencyKillSwitchResponse {
  settings: AutopilotSettingsDto;
  message: string;
}

export interface ThresholdCheckParams {
  authorization: Header<"Authorization">;
  workspaceId: string;
}

export interface ThresholdCheckResponse {
  tripped: boolean;
  reason?: string;
}

// GET /commercial/engagement/autopilot/settings
export const getAutopilotSettings = api(
  { expose: true, method: "GET", path: "/commercial/engagement/autopilot/settings" },
  async (params: GetAutopilotSettingsParams): Promise<GetAutopilotSettingsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOPILOT_MANAGE);

    const settings = await autopilotService.getSettings(ctx.workspaceId);
    return { settings };
  }
);

// PUT /commercial/engagement/autopilot/settings
export const updateAutopilotSettings = api(
  { expose: true, method: "PUT", path: "/commercial/engagement/autopilot/settings" },
  async (
    params: UpdateAutopilotSettingsParams
  ): Promise<UpdateAutopilotSettingsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOPILOT_MANAGE);

    const settings = await autopilotService.updateSettings(
      ctx.workspaceId,
      {
        enabled: params.enabled,
        envAllowlist: params.envAllowlist,
        triggerRuleIds: params.triggerRuleIds,
        containmentMin: params.containmentMin,
        errorMax: params.errorMax,
        takeoverMax: params.takeoverMax,
      },
      ctx.workforceMemberId
    );

    return { settings };
  }
);

// POST /commercial/engagement/autopilot/kill-switch
export const emergencyKillSwitch = api(
  { expose: true, method: "POST", path: "/commercial/engagement/autopilot/kill-switch" },
  async (params: EmergencyKillSwitchParams): Promise<EmergencyKillSwitchResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOPILOT_MANAGE);

    const settings = await autopilotService.emergencyKillSwitch(ctx.workspaceId, ctx.workforceMemberId);
    return {
      settings,
      message: "Autopilot emergency kill switch activated. All automated dispatch stopped immediately.",
    };
  }
);

// POST /commercial/engagement/autopilot/threshold-check
export const checkAutopilotThreshold = api(
  { expose: true, method: "POST", path: "/commercial/engagement/autopilot/threshold-check" },
  async (params: ThresholdCheckParams): Promise<ThresholdCheckResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.AUTOPILOT_MANAGE);

    const res = await autopilotService.checkThresholdBreach(ctx.workspaceId);
    return res;
  }
);
