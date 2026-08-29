import { api, APIError } from "encore.dev/api";
import { resolveAuthData } from "./auth.handler";
import { verifyPlatformToken } from "../services/token.service";
import {
  getWorkspaceEntitlement,
  listWorkspaceMembershipsForUser,
  validateWorkspaceMembership,
  markWorkspaceSynced,
  WorkspaceEntitlementView,
  WorkspaceMembershipInfo,
} from "../services/venture-workspace.service";

export interface ListWorkspaceMembershipsRequest {
  platformToken: string;
}

export interface ListWorkspaceMembershipsResponse {
  memberships: WorkspaceMembershipInfo[];
}

export interface ValidateWorkspaceMembershipRequest {
  platformToken: string;
  platformWorkspaceId: string;
}

export interface ValidateWorkspaceMembershipResponse {
  valid: boolean;
  membership?: WorkspaceMembershipInfo;
}

export interface MarkWorkspaceSyncedRequest {
  platformWorkspaceId: string;
  platformToken: string;
}

export interface MarkWorkspaceSyncedResponse {
  success: boolean;
}

export const getWorkspaceEntitlementEndpoint = api(
  { method: "GET", path: "/platform/workspaces/:id/entitlement", expose: true, auth: true },
  async ({ id }: { id: string }): Promise<WorkspaceEntitlementView> => {
    const authData = await resolveAuthData();
    const userId = BigInt(authData.userID);
    const workspaceId = BigInt(id);

    const membership = await validateWorkspaceMembership(userId, workspaceId);
    if (!membership) {
      throw APIError.permissionDenied("Không có quyền truy cập entitlement của workspace này");
    }

    return getWorkspaceEntitlement(workspaceId);
  }
);

export const listWorkspaceMembershipsEndpoint = api(
  { method: "POST", path: "/platform/internal/list-workspace-memberships", expose: true, auth: false },
  async (params: ListWorkspaceMembershipsRequest): Promise<ListWorkspaceMembershipsResponse> => {
    let userIdStr: string;
    try {
      const claims = verifyPlatformToken(params.platformToken);
      userIdStr = claims.sub;
    } catch {
      throw APIError.unauthenticated("invalid or expired platform token");
    }

    const memberships = await listWorkspaceMembershipsForUser(BigInt(userIdStr));
    return { memberships };
  }
);

export const validateWorkspaceMembershipEndpoint = api(
  { method: "POST", path: "/platform/internal/validate-workspace-membership", expose: true, auth: false },
  async (params: ValidateWorkspaceMembershipRequest): Promise<ValidateWorkspaceMembershipResponse> => {
    let userIdStr: string;
    try {
      const claims = verifyPlatformToken(params.platformToken);
      userIdStr = claims.sub;
    } catch {
      throw APIError.unauthenticated("invalid or expired platform token");
    }

    const membership = await validateWorkspaceMembership(BigInt(userIdStr), BigInt(params.platformWorkspaceId));
    if (!membership) {
      return { valid: false };
    }
    return { valid: true, membership };
  }
);

export const markWorkspaceSyncedEndpoint = api(
  { method: "POST", path: "/platform/internal/mark-workspace-synced", expose: true, auth: false },
  async (params: MarkWorkspaceSyncedRequest): Promise<MarkWorkspaceSyncedResponse> => {
    // M1 §4 — trước đây không xác thực gì (chỉ nhận platformWorkspaceId). Yêu cầu
    // platform token hợp lệ + caller là thành viên workspace đó.
    let userIdStr: string;
    try {
      userIdStr = verifyPlatformToken(params.platformToken).sub;
    } catch {
      throw APIError.unauthenticated("invalid or expired platform token");
    }
    const membership = await validateWorkspaceMembership(
      BigInt(userIdStr),
      BigInt(params.platformWorkspaceId)
    );
    if (!membership) {
      throw APIError.permissionDenied("not a member of this workspace");
    }
    await markWorkspaceSynced(BigInt(params.platformWorkspaceId));
    return { success: true };
  }
);
