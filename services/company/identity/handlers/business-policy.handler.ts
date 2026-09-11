import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { verifyCosaDelegationForCapability } from "../../shared/auth/cosa-delegation.service";
import { CAP_BUSINESS_POLICY_RULES_READ } from "../../shared/auth/cosa-task-delegation";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  evaluateBusinessPolicyService,
  EvaluateBusinessPolicyResult,
} from "../services/business-policy.service";
import {
  getBusinessPolicyRulesForMemberService,
  BusinessPolicyRuleSet,
} from "../services/business-authorization.service";

export interface EvaluateBusinessPolicyRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  action: string;
  resourceRef?: string;
  version?: number;
  runRef?: string;
  projectId?: string;
  legalEntityId?: string;
}

export const evaluateBusinessPolicy = api(
  { method: "POST", path: "/identity/business-policy/evaluate", expose: true },
  async (req: EvaluateBusinessPolicyRequest): Promise<EvaluateBusinessPolicyResult> => {
    let ctx: TenantContext;
    const rawAuth = req.authorization || "";
    const token = rawAuth.startsWith("Bearer ") ? rawAuth.slice(7).trim() : rawAuth.trim();

    try {
      ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    } catch (primaryErr) {
      if (token) {
        try {
          const claims = verifyCosaDelegationForCapability(token, {
            workspaceId: String(req.workspaceId),
            capabilityId: req.action,
          });
          ctx = {
            workspaceId: String(req.workspaceId),
            userId: claims.sub,
            workforceMemberId: claims.principal_id,
            membershipRole: "member",
            permissions: ["read"],
            correlationId: claims.jti,
          };
        } catch {
          throw primaryErr;
        }
      } else {
        throw primaryErr;
      }
    }

    return evaluateBusinessPolicyService({
      ctx,
      action: req.action,
      resourceRef: req.resourceRef,
      version: req.version,
      runRef: req.runRef,
      scope: {
        workspaceId: ctx.workspaceId,
        projectId: req.projectId,
        legalEntityId: req.legalEntityId,
      },
    });
  }
);

export interface GetBusinessPolicyRulesRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  workforceMemberId?: string;
  projectId?: string;
  legalEntityId?: string;
}

// Encore không hỗ trợ type literal vừa có named field vừa có index signature
// ("index signature with additional fields is not supported") — PermissionRule
// nội bộ (permission-evaluator.ts) có conditions?: {maxAmountMinor?; currency?;
// [key: string]: any} nên không dùng trực tiếp làm response type được. Định
// nghĩa view type riêng cho response (conditions: Record<string, any> thuần,
// giống pattern đã dùng ở GetPermissionsResponse).
export interface BusinessPolicyRuleView {
  id: string;
  permissionKey: string;
  effect: string;
  conditions: Record<string, any>;
}

export interface CapabilityBindingView {
  capabilityId: string;
  permissionKey: string;
  riskClass: string;
  version: number;
}

export interface AgentCapabilityAuthorityView {
  capabilityId: string;
  permissionKey: string;
  riskClass: string;
  grantId: string;
  constraints: Record<string, any>;
}

export interface GetBusinessPolicyRulesResponse {
  isFounder: boolean;
  policyVersion: number;
  authorizationEpoch: number;
  ruleGroups: Array<{ rules: BusinessPolicyRuleView[] }>;
  capabilityBindings: CapabilityBindingView[];
  agentCapabilities: AgentCapabilityAuthorityView[];
}

/**
 * IA02 phần 2 — route THUẦN delegation (không session fallback, giống
 * advanceTask): CapabilityGateway phía Python (apps/cosa) gọi route này ở
 * boundary resolve-snapshot (run-start/trước resume, CÙNG lúc với
 * get_snapshot control-plane) để nhúng raw business-policy rules vào
 * context — evaluate() trong gateway chạy đồng bộ nên KHÔNG thể gọi HTTP
 * tại thời điểm thực thi từng capability.
 */
export const getBusinessPolicyRules = api(
  { method: "GET", path: "/identity/business-policy/rules", expose: true },
  async (req: GetBusinessPolicyRulesRequest): Promise<GetBusinessPolicyRulesResponse> => {
    const rawAuth = req.authorization || "";
    const token = rawAuth.startsWith("Bearer ") ? rawAuth.slice(7).trim() : rawAuth.trim();
    if (!token) {
      throw APIError.unauthenticated("missing cosa delegation bearer token");
    }
    try {
      verifyCosaDelegationForCapability(token, {
        workspaceId: String(req.workspaceId),
        capabilityId: CAP_BUSINESS_POLICY_RULES_READ,
      });
    } catch (err) {
      throw APIError.permissionDenied(`cosa delegation rejected: ${(err as Error).message}`);
    }

    const ruleSet: BusinessPolicyRuleSet = await getBusinessPolicyRulesForMemberService({
      workspaceId: BigInt(req.workspaceId),
      workforceMemberId: req.workforceMemberId ? BigInt(req.workforceMemberId) : undefined,
      projectId: req.projectId ? BigInt(req.projectId) : undefined,
      legalEntityId: req.legalEntityId ? BigInt(req.legalEntityId) : undefined,
    });

    return {
      isFounder: ruleSet.isFounder,
      policyVersion: ruleSet.policyVersion,
      authorizationEpoch: ruleSet.authorizationEpoch,
      ruleGroups: ruleSet.ruleGroups.map((g) => ({
        rules: g.rules.map((r) => ({
          id: r.id,
          permissionKey: r.permissionKey ?? "",
          effect: r.effect,
          conditions: r.conditions ?? {},
        })),
      })),
      capabilityBindings: ruleSet.capabilityBindings.map((b) => ({
        capabilityId: b.capabilityId,
        permissionKey: b.permissionKey,
        riskClass: b.riskClass,
        version: b.version,
      })),
      agentCapabilities: ruleSet.agentCapabilities.map((a) => ({
        capabilityId: a.capabilityId,
        permissionKey: a.permissionKey,
        riskClass: a.riskClass,
        grantId: a.grantId,
        constraints: a.constraints,
      })),
    };
  }
);
