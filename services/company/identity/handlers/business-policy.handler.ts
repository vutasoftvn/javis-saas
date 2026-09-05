import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { verifyCosaDelegationForCapability } from "../../shared/auth/cosa-delegation.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  evaluateBusinessPolicyService,
  EvaluateBusinessPolicyResult,
} from "../services/business-policy.service";

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
