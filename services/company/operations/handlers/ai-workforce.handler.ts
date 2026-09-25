import { api, APIError } from "encore.dev/api";
import {
  createAiWorkforceMember,
  type CreateAiWorkforceResponse,
} from "../services/organization-overview.service";
import {
  requireOrganizationAccess,
  type OrganizationScopedParams,
} from "./organization-overview.handler";

export interface CreateAiWorkforceParams extends OrganizationScopedParams {
  roleTitle: string;
  workspaceAgentId: string;
  managerMemberId?: string;
  idempotencyKey: string;
}

export const createAiWorkforceApi = api(
  { method: "POST", path: "/operations/organizations/:organizationId/ai-workforce", expose: true },
  async (params: CreateAiWorkforceParams): Promise<CreateAiWorkforceResponse> => {
    const ctx = await requireOrganizationAccess(params);
    if (ctx.workspaceId !== params.organizationId) {
      throw APIError.permissionDenied("organization scope mismatch");
    }
    return createAiWorkforceMember(ctx, {
      organizationId: params.organizationId,
      roleTitle: params.roleTitle,
      workspaceAgentId: params.workspaceAgentId,
      managerMemberId: params.managerMemberId,
      idempotencyKey: params.idempotencyKey,
    });
  }
);
