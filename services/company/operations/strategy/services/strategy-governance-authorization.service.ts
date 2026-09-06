import { APIError } from "encore.dev/api";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  requireCommandAuthority,
} from "../../../identity/services/command-authority.service";
import type {
  ResourceScope,
  RuleDecision,
} from "../../../identity/services/business-authorization.service";
import type { StrategyGovernancePermission } from "../../../identity/services/permission-catalog";
import {
  getWorkspaceStrategySettings,
  WorkspaceStrategySettings,
} from "./workspace-strategy-settings.service";

export type GovernedStrategyPermission =
  | StrategyGovernancePermission
  | "execution.plan.approve";

/**
 * Enforces strategy governance authority based on workspace settings approval policy.
 * - Under FOUNDER_ONLY: only founder / co-founder can execute the command.
 * - Under DELEGATED_APPROVER: delegates to requireCommandAuthority using role assignments & catalog.
 */
export async function requireStrategyGovernanceAuthority(
  ctx: TenantContext,
  permission: GovernedStrategyPermission,
  scope?: ResourceScope,
  settings?: WorkspaceStrategySettings
): Promise<RuleDecision> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  const wsId = String(ctx.workspaceId);
  if (scope?.workspaceId && String(scope.workspaceId) !== wsId) {
    throw APIError.permissionDenied("Cross-workspace access denied");
  }

  const effectiveSettings =
    settings ?? (await getWorkspaceStrategySettings(wsId));

  if (effectiveSettings.approvalPolicy === "FOUNDER_ONLY") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        `Missing authority for ${permission}: founder approval required by workspace policy`
      );
    }

    return {
      effect: "ALLOW",
      reasonCodes: ["FOUNDER_POLICY_ENFORCED"],
      policyVersion: effectiveSettings.revision,
      matchedRuleIds: ["system:founder"],
      approvalRequired: false,
    };
  }

  // Under DELEGATED_APPROVER, check command authority with role assignments
  return requireCommandAuthority(ctx, permission, scope);
}

/**
 * Helper to check if caller has authority without throwing, returning a boolean capability flag.
 */
export async function canExecuteStrategyGovernance(
  ctx: TenantContext,
  permission: GovernedStrategyPermission,
  scope?: ResourceScope,
  settings?: WorkspaceStrategySettings
): Promise<boolean> {

  try {
    await requireStrategyGovernanceAuthority(ctx, permission, scope, settings);
    return true;
  } catch {
    return false;
  }
}
