import { APIError } from "encore.dev/api";
import type { TenantContext } from "../../shared/types/tenant_context";

/**
 * Guard quyền founder cho các command quản trị (policy/sweep/approval/deployment).
 * Được A2 thay thế nội bộ bằng evaluator đầy đủ.
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
