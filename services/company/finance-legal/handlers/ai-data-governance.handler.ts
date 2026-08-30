import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { verifyCosaDelegationForCapability } from "../../shared/auth/cosa-delegation.service";
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
  modelKey?: string;
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

/**
 * Task 10 (audit fix) — CHẤP NHẬN CẢ 2 loại caller cho route này:
 *   1. Delegation JWT COSA→Company có capability_ids chứa `req.capabilityId`
 *      (đúng chiều runtime kernel thật gọi qua
 *      `CosaDataModelGate`/`AiComplianceClient.resolve_data_use` —
 *      xem `verifyCosaDelegationForCapability`). Đây là caller thật DUY
 *      NHẤT của route này tính đến audit 2026-08-30 (không frontend nào gọi
 *      route này) — trước fix này route CHỈ chấp nhận (2), nên mọi lần gọi
 *      thật ở (1) đều bị 401, một gap phát hiện lần đầu khi Task 10 test
 *      round-trip HTTP thật.
 *   2. Session người dùng thật qua `requireWorkspaceAccess` (giữ nguyên
 *      hành vi cũ — phòng khi có caller UI/API công khai trong tương lai,
 *      route khai báo `expose: true`).
 * Thử (1) trước NẾU có `capabilityId` (bắt buộc để so khớp scope delegation).
 * Nếu (1) không áp dụng được (thiếu capabilityId, hoặc token không verify
 * được ở nhánh delegation) thì rơi về (2) — vẫn an toàn: token delegation
 * hỏng/không đúng shape cũng sẽ không verify được như 1 session token thật ở
 * (2), nên kết quả cuối cùng vẫn là `unauthenticated`, không có đường nào
 * "mượn" 1 nhánh để qua mặt nhánh kia.
 */
export const resolveDataUseApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/resolve-data-use", expose: true },
  async (req: ResolveDataUseRequest): Promise<DataUseDecision> => {
    const bearerMatch = /^Bearer\s+(.+)$/i.exec((req.authorization ?? "").trim());

    if (bearerMatch && req.capabilityId) {
      let claims;
      try {
        claims = verifyCosaDelegationForCapability(bearerMatch[1], {
          workspaceId: req.workspaceId,
          capabilityId: req.capabilityId,
        });
      } catch {
        claims = null;
      }
      if (claims) {
        return resolveDataUse({
          ...req,
          workspaceId: claims.workspace_id,
        });
      }
    }

    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return resolveDataUse({
      ...req,
      workspaceId: ctx.workspaceId,
    });
  }
);
