import { APIError } from "encore.dev/api";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  requireBusinessAction,
  ResourceScope,
  RuleDecision,
} from "./business-authorization.service";

/**
 * Guard quyền founder cho các command quản trị (policy/sweep/approval/deployment).
 */
export function requireFounderCommand(ctx: TenantContext, action: string): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  const role = (ctx.membershipRole || "").toLowerCase();
  if (!["founder", "co-founder"].includes(role)) {
    throw APIError.permissionDenied(`Missing authority for ${action}`);
  }
}

/**
 * Evaluator đầy đủ kiểm tra quyền theo catalog và role assignments có version.
 */
export async function requireCommandAuthority(
  ctx: TenantContext,
  action: string,
  scope?: ResourceScope,
  facts?: Record<string, any>
): Promise<RuleDecision> {
  return requireBusinessAction(ctx, action, scope, facts);
}
