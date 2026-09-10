import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  getWorkspaceStrategySettings,
  updateWorkspaceStrategySettings,
  WorkspaceStrategySettings,
  MidCycleReviewPolicy,
  ApprovalPolicy,
} from "../services/workspace-strategy-settings.service";
import {
  requireStrategyGovernanceAuthority,
  canExecuteStrategyGovernance,
} from "../services/strategy-governance-authorization.service";

export interface GetWorkspaceStrategySettingsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface WorkspaceStrategySettingsResponse {
  settings: WorkspaceStrategySettings;
  canEdit: boolean;
  policyRevision: number;
}

export interface UpdateWorkspaceStrategySettingsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  weeklyReviewEnabled?: boolean;
  midCycleReviewPolicy?: MidCycleReviewPolicy;
  endCycleReviewEnabled?: boolean;
  allowedAgentProfiles?: string[];
  approvalPolicy?: ApprovalPolicy;
  expectedRevision?: number;
}

export const getStrategySettings = api(
  { method: "GET", path: "/operations/strategy/settings", expose: true },
  async (
    params: GetWorkspaceStrategySettingsParams
  ): Promise<WorkspaceStrategySettingsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const settings = await getWorkspaceStrategySettings(ctx.workspaceId);
    const canEdit = await canExecuteStrategyGovernance(
      ctx,
      "strategy.framework.manage",
      { workspaceId: String(ctx.workspaceId) },
      settings
    );

    return {
      settings,
      canEdit,
      policyRevision: settings.revision,
    };
  }
);

export const updateStrategySettings = api(
  { method: "PUT", path: "/operations/strategy/settings", expose: true },
  async (
    params: UpdateWorkspaceStrategySettingsParams
  ): Promise<WorkspaceStrategySettingsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsIdStr = String(ctx.workspaceId);

    // Current settings govern whether caller can change settings
    const currentSettings = await getWorkspaceStrategySettings(wsIdStr);
    await requireStrategyGovernanceAuthority(
      ctx,
      "strategy.framework.manage",
      { workspaceId: wsIdStr },
      currentSettings
    );

    const updated = await updateWorkspaceStrategySettings(ctx, {
      workspaceId: wsIdStr,
      weeklyReviewEnabled: params.weeklyReviewEnabled,
      midCycleReviewPolicy: params.midCycleReviewPolicy,
      endCycleReviewEnabled: params.endCycleReviewEnabled,
      allowedAgentProfiles: params.allowedAgentProfiles,
      approvalPolicy: params.approvalPolicy,
      expectedRevision: params.expectedRevision,
    });

    const canEdit = await canExecuteStrategyGovernance(
      ctx,
      "strategy.framework.manage",
      { workspaceId: wsIdStr },
      updated
    );

    return {
      settings: updated,
      canEdit,
      policyRevision: updated.revision,
    };
  }
);
