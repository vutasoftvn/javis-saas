import { api, APIError } from "encore.dev/api";
import { resolveAuthData } from "./auth.handler";
import { authorizeAndProjectCoreAccess } from "../services/core-access.service";
import {
  listMembershipsForToken,
  resolveIdentityForToken,
  validateMembershipForToken,
  type TokenIdentity,
} from "../services/workspace-access.service";
import {
  getWorkspaceEntitlement,
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
  { method: "GET", path: "/platform/organizations/:id/entitlement", expose: true, auth: true },
  async ({ id }: { id: string }): Promise<WorkspaceEntitlementView> => {
    const authData = await resolveAuthData();
    const userId = BigInt(authData.userID);
    const workspaceId = BigInt(id);

    // Core quyết định thành viên và bản chiếu được cập nhật trước khi đọc bảng cục bộ.
    await authorizeAndProjectCoreAccess(authData.accessToken, id, "cosa.workspace.read");

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
    // Token JWT platform cũ hoặc access token OIDC của core (core là nguồn sự thật).
    const memberships = await listMembershipsForToken(params.platformToken);
    return { memberships };
  }
);

export const validateWorkspaceMembershipEndpoint = api(
  { method: "POST", path: "/platform/internal/validate-workspace-membership", expose: true, auth: false },
  async (params: ValidateWorkspaceMembershipRequest): Promise<ValidateWorkspaceMembershipResponse> => {
    const { membership } = await validateMembershipForToken(params.platformToken, params.platformWorkspaceId);
    if (!membership) {
      return { valid: false };
    }
    return { valid: true, membership };
  }
);

export interface ResolveIdentityRequest {
  platformToken: string;
}

/** Nội bộ cho services/company: danh tính của người giữ token (JWT platform cũ hoặc token OIDC của core). */
export const resolveIdentityEndpoint = api(
  { method: "POST", path: "/platform/internal/resolve-identity", expose: true, auth: false },
  async (params: ResolveIdentityRequest): Promise<TokenIdentity> => {
    return resolveIdentityForToken(params.platformToken);
  }
);

export const markWorkspaceSyncedEndpoint = api(
  { method: "POST", path: "/platform/internal/mark-workspace-synced", expose: true, auth: false },
  async (params: MarkWorkspaceSyncedRequest): Promise<MarkWorkspaceSyncedResponse> => {
    // M1 §4 — trước đây không xác thực gì (chỉ nhận platformWorkspaceId). Yêu cầu
    // platform token hợp lệ + caller là thành viên workspace đó.
    const { membership } = await validateMembershipForToken(params.platformToken, params.platformWorkspaceId);
    if (!membership) {
      throw APIError.permissionDenied("not a member of this workspace");
    }
    await markWorkspaceSynced(BigInt(params.platformWorkspaceId));
    return { success: true };
  }
);
