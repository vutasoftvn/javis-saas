import { APIError } from "encore.dev/api";
import type { TenantContext } from "../../../shared/types/tenant_context";

export const ENGAGEMENT_PERMISSIONS = {
  COPILOT_REQUEST: "engagement.copilot.request",
  COPILOT_MANAGE: "engagement.copilot.manage",
  THREAD_READ: "engagement.thread.read",
  THREAD_WRITE: "engagement.thread.write",
  MESSAGE_SEND: "engagement.message.send",
} as const;

export function requireEngagementPermission(ctx: TenantContext, permission: string): void {
  const perms = ctx.permissions || [];
  const role = ctx.membershipRole;

  // Founder, co-founder, or admin has full access
  if (
    role === "founder" ||
    role === "co-founder" ||
    role === "admin" ||
    perms.includes("*") ||
    perms.includes("admin") ||
    perms.includes(permission)
  ) {
    return;
  }

  // Read permission check
  if (permission === ENGAGEMENT_PERMISSIONS.THREAD_READ && (perms.includes("read") || perms.includes("write"))) {
    return;
  }

  // Copilot request permission check
  if (permission === ENGAGEMENT_PERMISSIONS.COPILOT_REQUEST && perms.includes("write")) {
    return;
  }

  throw APIError.permissionDenied(`Missing required engagement permission: ${permission}`);
}
