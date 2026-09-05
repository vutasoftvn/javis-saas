import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getPermissionsService,
  simulatePermissionsService,
  updatePermissionsService,
  GetPermissionsResponse,
  SimulatePermissionsRequest,
  UpdatePermissionsRequest,
  PermissionMutation,
} from "../services/permissions.service";
import { RuleDecision } from "../services/business-authorization.service";

export interface GetPermissionsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface SimulatePermissionsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  action: string;
  memberId?: string;
  projectId?: string;
  legalEntityId?: string;
  facts?: Record<string, any>;
}

export interface UpdatePermissionsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  expectedVersion: number;
  reason: string;
  mutations: PermissionMutation[];
}

export const getPermissions = api(
  { method: "GET", path: "/identity/permissions", expose: true },
  async (req: GetPermissionsApiRequest): Promise<GetPermissionsResponse> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getPermissionsService(ctx);
  }
);

export const simulatePermissions = api(
  { method: "POST", path: "/identity/permissions/simulate", expose: true },
  async (
    req: SimulatePermissionsApiRequest
  ): Promise<{
    decision: RuleDecision;
    impacts: Array<{
      memberId: string;
      action: string;
      effect: string;
      reason: string;
    }>;
  }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return simulatePermissionsService(ctx, {
      action: req.action,
      memberId: req.memberId,
      scope: {
        workspaceId: ctx.workspaceId,
        projectId: req.projectId,
        legalEntityId: req.legalEntityId,
      },
      facts: req.facts,
    });
  }
);

export const updatePermissions = api(
  { method: "PUT", path: "/identity/permissions", expose: true },
  async (
    req: UpdatePermissionsApiRequest
  ): Promise<{ success: boolean; version: number }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return updatePermissionsService(ctx, {
      expectedVersion: req.expectedVersion,
      reason: req.reason,
      mutations: req.mutations,
    });
  }
);
