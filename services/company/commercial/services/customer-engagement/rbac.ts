import { APIError } from "encore.dev/api";
import type { TenantContext } from "../../../shared/types/tenant_context";

export const ENGAGEMENT_PERMISSIONS = {
  COPILOT_REQUEST: "engagement.copilot.request",
  COPILOT_MANAGE: "engagement.copilot.manage",
  CHANNEL_MANAGE: "engagement.channel.manage",
  AUTOMATION_MANAGE: "engagement.automation.manage",
  AUTOPILOT_MANAGE: "engagement.autopilot.manage",
  THREAD_READ: "engagement.thread.read",
  THREAD_WRITE: "engagement.thread.write",
  MESSAGE_SEND: "engagement.message.send",
  // Desk workflow permissions are additive. Keep the established upper-case
  // entries above because copilot/channel handlers already depend on them.
  threadTakeover: "engagement.thread.takeover",
  decisionReview: "engagement.decision_request.review",
  decisionDecide: "engagement.decision_request.decide",
  decisionAuthorityManage: "engagement.decision_authority.manage",
  escalationRouteManage: "engagement.escalation_route.manage",
  dataSubjectRequestManage: "engagement.data_subject_request.manage",
  legalHoldManage: "engagement.legal_hold.manage",
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
