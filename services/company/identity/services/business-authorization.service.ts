import { APIError } from "encore.dev/api";
import { eq, and, lte, or, isNull, gt, desc } from "drizzle-orm";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  coreWorkspacePolicyVersions,
  identityWorkspaceMemberships,
} from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";
import { isKnownPermission } from "./permission-catalog";
import {
  combinePermissionRules,
  matchBestRuleInRole,
  PermissionEffect,
  PermissionRule,
} from "./permission-evaluator";

export type Effect = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";

export interface ResourceScope {
  workspaceId: string;
  projectId?: string;
  legalEntityId?: string;
}

export interface RuleDecision {
  effect: Effect;
  reasonCodes: string[];
  policyVersion: number;
  matchedRuleIds: string[];
  approvalRequired: boolean;
}

export async function getLatestPolicyVersion(workspaceId: bigint): Promise<number> {
  const [latest] = await db
    .select({ version: coreWorkspacePolicyVersions.version })
    .from(coreWorkspacePolicyVersions)
    .where(eq(coreWorkspacePolicyVersions.workspaceId, workspaceId))
    .orderBy(desc(coreWorkspacePolicyVersions.version))
    .limit(1);

  return latest?.version ?? 1;
}

export async function authorizeBusinessAction(
  ctx: TenantContext,
  action: string,
  scope?: ResourceScope,
  facts?: Record<string, any>
): Promise<RuleDecision> {
  if (!ctx) {
    throw APIError.unauthenticated("Tenant context is required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const policyVersion = await getLatestPolicyVersion(wsId);

  // Scope tenant isolation check
  if (scope?.workspaceId && String(scope.workspaceId) !== String(ctx.workspaceId)) {
    return {
      effect: "DENY",
      reasonCodes: ["CROSS_WORKSPACE_ACCESS_DENIED"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
    };
  }

  // Catalog validation
  if (!isKnownPermission(action)) {
    return {
      effect: "DENY",
      reasonCodes: ["UNKNOWN_ACTION"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
    };
  }

  const roleName = (ctx.membershipRole || "").toLowerCase();
  const isFounder = ["founder", "co-founder"].includes(roleName);

  // If workforceMemberId is present, query active role assignments
  const applicableRules: PermissionRule[] = [];
  const matchedRuleIds: string[] = [];

  if (ctx.workforceMemberId) {
    const memberId = BigInt(ctx.workforceMemberId);
    const now = new Date();

    const assignments = await db
      .select({
        assignmentId: coreMemberRoleAssignments.id,
        roleId: coreMemberRoleAssignments.roleId,
        projectId: coreMemberRoleAssignments.projectId,
        legalEntityId: coreMemberRoleAssignments.legalEntityId,
      })
      .from(coreMemberRoleAssignments)
      .where(
        and(
          eq(coreMemberRoleAssignments.workspaceId, wsId),
          eq(coreMemberRoleAssignments.workforceMemberId, memberId),
          lte(coreMemberRoleAssignments.validFrom, now),
          or(
            isNull(coreMemberRoleAssignments.validUntil),
            gt(coreMemberRoleAssignments.validUntil, now)
          )
        )
      );

    for (const a of assignments) {
      // Check project scope
      if (a.projectId !== null) {
        if (!scope?.projectId || String(a.projectId) !== String(scope.projectId)) {
          continue; // Scope does not match this assignment
        }
      }

      // Check legal entity scope
      if (a.legalEntityId !== null) {
        if (!scope?.legalEntityId || String(a.legalEntityId) !== String(scope.legalEntityId)) {
          continue; // Scope does not match this assignment
        }
      }

      // Fetch role permissions
      const rolePerms = await db
        .select({
          permissionKey: coreRolePermissions.permissionKey,
          effect: coreRolePermissions.effect,
          conditions: coreRolePermissions.conditions,
        })
        .from(coreRolePermissions)
        .where(eq(coreRolePermissions.roleId, a.roleId));

      const convertedRules: PermissionRule[] = rolePerms.map((rp) => ({
        id: `${a.roleId}:${rp.permissionKey}`,
        effect: rp.effect as PermissionEffect,
        permissionKey: rp.permissionKey,
        conditions: (rp.conditions as any) || {},
      }));

      const bestInRole = matchBestRuleInRole(convertedRules, action, facts);
      if (bestInRole) {
        applicableRules.push(bestInRole);
        matchedRuleIds.push(bestInRole.id);
      }
    }
  }

  if (applicableRules.length > 0) {
    const combinedEffect = combinePermissionRules(applicableRules);
    return {
      effect: combinedEffect,
      reasonCodes: [combinedEffect],
      policyVersion,
      matchedRuleIds,
      approvalRequired: combinedEffect === "REQUIRE_APPROVAL",
    };
  }

  // If no specific role assignments matched:
  // If user is founder/co-founder, grant default ALLOW
  if (isFounder) {
    return {
      effect: "ALLOW",
      reasonCodes: ["FOUNDER_DEFAULT_ALLOW"],
      policyVersion,
      matchedRuleIds: ["system:founder"],
      approvalRequired: false,
    };
  }

  return {
    effect: "DENY",
    reasonCodes: ["NO_MATCHING_RULE"],
    policyVersion,
    matchedRuleIds: [],
    approvalRequired: false,
  };
}

export async function requireBusinessAction(
  ctx: TenantContext,
  action: string,
  scope?: ResourceScope,
  facts?: Record<string, any>
): Promise<RuleDecision> {
  const decision = await authorizeBusinessAction(ctx, action, scope, facts);

  if (decision.effect === "DENY") {
    throw APIError.permissionDenied(
      `Permission denied for action '${action}' (reasons: ${decision.reasonCodes.join(", ")})`
    );
  }

  if (decision.effect === "REQUIRE_APPROVAL") {
    const err = APIError.failedPrecondition(
      `Approval required for action '${action}'`
    );
    (err as any).code = "APPROVAL_REQUIRED";
    throw err;
  }

  return decision;
}
