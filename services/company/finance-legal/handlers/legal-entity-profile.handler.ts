import { api, Header, Query } from "encore.dev/api";
import {
  listLegalEntityProfiles,
  createLegalEntityProfile,
  requestVerification,
  applyVerification,
  LegalEntityProfileView,
} from "../services/legal-entity-profile.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export interface ListLegalEntityProfilesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface ListLegalEntityProfilesResponse {
  profiles: LegalEntityProfileView[];
}

export interface CreateLegalEntityProfileParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  entityType: string;
  registrationNumber?: string;
  taxId?: string;
}

export interface RequestVerificationParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface ConfirmVerificationParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  approvalId: string;
}

export const getLegalEntityProfiles = api(
  { method: "GET", path: "/legal/legal-entity-profiles", expose: true },
  async (params: ListLegalEntityProfilesParams): Promise<ListLegalEntityProfilesResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const profiles = await listLegalEntityProfiles(BigInt(ctx.workspaceId));
    return { profiles };
  }
);

export const postLegalEntityProfile = api(
  { method: "POST", path: "/legal/legal-entity-profiles", expose: true },
  async (params: CreateLegalEntityProfileParams): Promise<LegalEntityProfileView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createLegalEntityProfile({
      workspaceId: BigInt(ctx.workspaceId),
      entityType: params.entityType,
      registrationNumber: params.registrationNumber,
      taxId: params.taxId,
    });
  }
);

export const postRequestVerification = api(
  { method: "POST", path: "/legal/legal-entity-profiles/:id/verify", expose: true },
  async (params: RequestVerificationParams): Promise<{ approvalId: string; status: "PENDING_APPROVAL" }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return requestVerification({
      profileId: BigInt(params.id),
      actorMemberId: BigInt(ctx.userId || "1"),
    });
  }
);

export const postConfirmVerification = api(
  { method: "POST", path: "/legal/legal-entity-profiles/:id/verify/confirm", expose: true },
  async (params: ConfirmVerificationParams): Promise<LegalEntityProfileView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return applyVerification({
      profileId: BigInt(params.id),
      approvalId: params.approvalId,
      approverMemberId: BigInt(ctx.userId || "1"),
    });
  }
);
