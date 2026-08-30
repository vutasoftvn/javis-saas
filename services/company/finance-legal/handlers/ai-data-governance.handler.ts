import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  upsertProviderProfile,
  upsertDataProcessingProfile,
  grantProcessingAuthorization,
  withdrawProcessingAuthorization,
  createDataSubjectRequest,
  resolveDataUse,
  type DataUseDecision,
} from "../services/ai-data-governance.service";

export interface UpsertProviderProfileRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  providerKey: string;
  modelKey: string;
  version: string;
  status: "DRAFT" | "APPROVED" | "SUSPENDED" | "REVOKED";
  declaredProcessingRegion: string;
  dpaReference?: string;
  allowedDataCategories: string[];
}

export interface UpsertDataProcessingProfileRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  bindingId?: string;
  purposeId: string;
  dataCategories: string[];
  recipientProviderProfileId: string;
  retentionPolicyId: string;
  transferConditions?: string[];
  minimizationRequired?: boolean;
  version: string;
  status: "DRAFT" | "ACTIVE" | "SUSPENDED" | "RETIRED";
}

export interface GrantProcessingAuthorizationRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  subjectReference: string;
  purposeId: string;
  purposeVersion: string;
  authorityType: "CONSENT" | "CONTRACTUAL_NECESSITY" | "LEGAL_OBLIGATION" | "VITAL_INTERESTS" | "LEGITIMATE_INTERESTS";
  proofReference: string;
}

export interface WithdrawProcessingAuthorizationRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  id: string;
}

export interface CreateDataSubjectRequestRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  subjectReference: string;
  requestType: "ACCESS" | "CORRECTION" | "DELETION" | "RESTRICTION";
  deadline: string;
  legalHold?: boolean;
  legalHoldReason?: string;
}

export interface ResolveDataUseRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  capabilityId?: string;
  purposeId: string;
  dataCategories: string[];
  providerKey: string;
  subjectReference?: string;
}

export const upsertProviderProfileApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/provider-profiles", expose: true },
  async (req: UpsertProviderProfileRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return upsertProviderProfile({
      ...req,
      workspaceId: ctx.workspaceId,
      reviewedByMemberId: ctx.workforceMemberId || ctx.userId,
    });
  }
);

export const upsertDataProcessingProfileApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/data-profiles", expose: true },
  async (req: UpsertDataProcessingProfileRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return upsertDataProcessingProfile({
      ...req,
      workspaceId: ctx.workspaceId,
    });
  }
);

export const grantProcessingAuthorizationApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/authorizations", expose: true },
  async (req: GrantProcessingAuthorizationRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return grantProcessingAuthorization({
      ...req,
      workspaceId: ctx.workspaceId,
    });
  }
);

export const withdrawProcessingAuthorizationApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/authorizations/:id/withdraw", expose: true },
  async (req: WithdrawProcessingAuthorizationRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return withdrawProcessingAuthorization(ctx.workspaceId, req.id, ctx.workforceMemberId || ctx.userId);
  }
);

export const createDataSubjectRequestApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/data-subject-requests", expose: true },
  async (req: CreateDataSubjectRequestRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createDataSubjectRequest({
      ...req,
      workspaceId: ctx.workspaceId,
      handledByMemberId: ctx.workforceMemberId || ctx.userId,
    });
  }
);

export const resolveDataUseApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/resolve-data-use", expose: true },
  async (req: ResolveDataUseRequest): Promise<DataUseDecision> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return resolveDataUse({
      ...req,
      workspaceId: ctx.workspaceId,
    });
  }
);
