import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  getOrganizationOverview,
  listOrganizationWorkforce,
  type OrganizationOverviewResponse,
  type WorkforceListResponse,
} from "../services/organization-overview.service";

export interface OrganizationScopedParams {
  organizationId: string;
  authorization?: Header<"Authorization">;
  workspaceId?: Header<"X-Workspace-Id">;
}

// Path organizationId là scope; header X-Workspace-Id (nếu gửi) phải khớp —
// không header nào tự cấp quyền (spec 2026-09-25 §7).
export async function requireOrganizationAccess(
  params: OrganizationScopedParams
): Promise<TenantContext> {
  if (!/^\d{1,19}$/.test(params.organizationId ?? "")) {
    throw APIError.invalidArgument("organizationId must be a numeric id");
  }
  if (params.workspaceId && params.workspaceId !== params.organizationId) {
    throw APIError.invalidArgument("X-Workspace-Id does not match organizationId");
  }
  return requireWorkspaceAccess(params.authorization, params.organizationId);
}

export const getOrganizationOverviewApi = api(
  { method: "GET", path: "/operations/organizations/:organizationId/overview", expose: true },
  async (params: OrganizationScopedParams): Promise<OrganizationOverviewResponse> => {
    const ctx = await requireOrganizationAccess(params);
    return getOrganizationOverview(ctx);
  }
);

export const listOrganizationWorkforceApi = api(
  { method: "GET", path: "/operations/organizations/:organizationId/workforce", expose: true },
  async (params: OrganizationScopedParams): Promise<WorkforceListResponse> => {
    const ctx = await requireOrganizationAccess(params);
    return listOrganizationWorkforce(ctx);
  }
);
