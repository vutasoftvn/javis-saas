import { APIError } from "encore.dev/api";
import { eq, and, desc, sql, isNull } from "drizzle-orm";
import { db } from "../models/db";
import {
  coreCapabilityPermissionBindings,
  coreAgentCapabilityGrants,
  coreAuthorizationEvents,
  coreWorkspaceRoles,
  coreMemberRoleAssignments,
  coreRolePermissions,
  identityWorkforceMembers,
  coreWorkspaceAuthorizationStates,
} from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  requireFounderAuthorization,
  appendAuthorizationEvent,
  advanceAuthorizationEpoch,
  getWorkspaceAuthorizationState,
} from "./authorization.service";
import {
  getLatestPolicyVersion,
  ResourceScope,
  RuleDecision,
} from "./business-authorization.service";

export type CapabilityRiskClass =
  | "READ"
  | "INTERNAL_WRITE"
  | "EXTERNAL_WRITE"
  | "FINANCIAL"
  | "LEGAL"
  | "AUTHORITY";

export interface CapabilityPermissionBinding {
  capabilityId: string;
  permissionKey: string;
  riskClass: CapabilityRiskClass;
  version: number;
}

export interface EvaluateAgentCapabilityInput {
  workspaceId: string;
  agentWorkforceMemberId: string;
  capabilityId: string;
  scope: ResourceScope;
  facts: Record<string, unknown>;
}

export interface GrantAgentCapabilityInput {
  workspaceId: string;
  agentWorkforceMemberId: string;
  capabilityId: string;
  projectId?: string;
  legalEntityId?: string;
  constraints?: Record<string, unknown>;
  validUntil?: string;
}

export interface RevokeAgentCapabilityInput {
  grantId: string;
  reason: string;
}

export async function evaluateAgentCapabilityAuthority(
  input: EvaluateAgentCapabilityInput
): Promise<RuleDecision & { grantId?: string; riskClass: CapabilityRiskClass }> {
  const wsId = BigInt(input.workspaceId);
  const agentMemberId = BigInt(input.agentWorkforceMemberId);
  const policyVersion = await getLatestPolicyVersion(wsId);

  // 1. Tenancy check
  if (input.scope?.workspaceId && String(input.scope.workspaceId) !== String(input.workspaceId)) {
    return {
      effect: "DENY",
      reasonCodes: ["CROSS_WORKSPACE_ACCESS_DENIED"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
      riskClass: "READ",
    };
  }

  // 2. Target must be active AI_AGENT
  const [member] = await db
    .select({
      id: identityWorkforceMembers.id,
      memberType: identityWorkforceMembers.memberType,
      status: identityWorkforceMembers.status,
    })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, agentMemberId),
        eq(identityWorkforceMembers.workspaceId, wsId)
      )
    )
    .limit(1);

  if (!member || member.status !== "active" || member.memberType !== "AI_AGENT") {
    return {
      effect: "DENY",
      reasonCodes: ["INVALID_OR_INACTIVE_AI_MEMBER"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
      riskClass: "READ",
    };
  }

  // 3. Check capability binding
  const [binding] = await db
    .select()
    .from(coreCapabilityPermissionBindings)
    .where(eq(coreCapabilityPermissionBindings.capabilityId, input.capabilityId))
    .limit(1);

  if (!binding) {
    return {
      effect: "DENY",
      reasonCodes: ["UNKNOWN_CAPABILITY_BINDING"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
      riskClass: "READ",
    };
  }

  const riskClass = binding.riskClass as CapabilityRiskClass;

  // 4. Check agent capability grants
  const grants = await db
    .select()
    .from(coreAgentCapabilityGrants)
    .where(
      and(
        eq(coreAgentCapabilityGrants.workspaceId, wsId),
        eq(coreAgentCapabilityGrants.agentWorkforceMemberId, agentMemberId),
        eq(coreAgentCapabilityGrants.capabilityId, input.capabilityId)
      )
    );

  const now = new Date();
  const activeGrants = grants.filter((g) => {
    if (g.status !== "ACTIVE") return false;
    if (g.validFrom && g.validFrom > now) return false;
    if (g.validUntil && g.validUntil <= now) return false;

    // Scope check: project
    if (g.projectId && input.scope?.projectId) {
      if (String(g.projectId) !== String(input.scope.projectId)) return false;
    }
    // Scope check: legal entity
    if (g.legalEntityId && input.scope?.legalEntityId) {
      if (String(g.legalEntityId) !== String(input.scope.legalEntityId)) return false;
    }

    return true;
  });

  if (activeGrants.length === 0) {
    const hasRevoked = grants.some((g) => g.status === "REVOKED");
    return {
      effect: "DENY",
      reasonCodes: [hasRevoked ? "AGENT_CAPABILITY_GRANT_REVOKED" : "MISSING_AGENT_CAPABILITY_GRANT"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
      riskClass,
    };
  }

  const matchedGrant = activeGrants[0];

  // 5. Constraints validation
  const constraints = (matchedGrant.constraints as Record<string, unknown>) || {};
  if (constraints.maxAmountMinor !== undefined) {
    const factsAmount = input.facts?.amount as any;
    if (!factsAmount || factsAmount.minor === undefined) {
      return {
        effect: "DENY",
        reasonCodes: ["MISSING_REQUIRED_FACT_AMOUNT"],
        policyVersion,
        matchedRuleIds: [matchedGrant.id],
        approvalRequired: false,
        riskClass,
      };
    }
    if (BigInt(factsAmount.minor) > BigInt(constraints.maxAmountMinor as string | number)) {
      return {
        effect: "DENY",
        reasonCodes: ["CONSTRAINT_AMOUNT_EXCEEDED"],
        policyVersion,
        matchedRuleIds: [matchedGrant.id],
        approvalRequired: false,
        riskClass,
      };
    }
  }

  if (constraints.currency !== undefined) {
    const factsAmount = input.facts?.amount as any;
    if (!factsAmount || factsAmount.currency !== constraints.currency) {
      return {
        effect: "DENY",
        reasonCodes: ["CONSTRAINT_CURRENCY_MISMATCH"],
        policyVersion,
        matchedRuleIds: [matchedGrant.id],
        approvalRequired: false,
        riskClass,
      };
    }
  }

  // 6. Role permission check
  const assignments = await db
    .select({
      roleId: coreMemberRoleAssignments.roleId,
      validFrom: coreMemberRoleAssignments.validFrom,
      validUntil: coreMemberRoleAssignments.validUntil,
    })
    .from(coreMemberRoleAssignments)
    .where(
      and(
        eq(coreMemberRoleAssignments.workspaceId, wsId),
        eq(coreMemberRoleAssignments.workforceMemberId, agentMemberId)
      )
    );

  const activeRoleIds = assignments
    .filter((a) => {
      if (a.validFrom && a.validFrom > now) return false;
      if (a.validUntil && a.validUntil <= now) return false;
      return true;
    })
    .map((a) => a.roleId);

  if (activeRoleIds.length === 0) {
    return {
      effect: "DENY",
      reasonCodes: ["ROLE_PERMISSION_DENIED"],
      policyVersion,
      matchedRuleIds: [matchedGrant.id],
      approvalRequired: false,
      riskClass,
    };
  }

  const permissions = await db
    .select()
    .from(coreRolePermissions)
    .where(eq(coreRolePermissions.permissionKey, binding.permissionKey));

  const matchingPermissions = permissions.filter((p) => activeRoleIds.includes(p.roleId));

  if (matchingPermissions.length === 0) {
    return {
      effect: "DENY",
      reasonCodes: ["ROLE_PERMISSION_DENIED"],
      policyVersion,
      matchedRuleIds: [matchedGrant.id],
      approvalRequired: false,
      riskClass,
    };
  }

  const hasDeny = matchingPermissions.some((p) => p.effect === "DENY");
  if (hasDeny) {
    return {
      effect: "DENY",
      reasonCodes: ["ROLE_PERMISSION_DENIED"],
      policyVersion,
      matchedRuleIds: [matchedGrant.id],
      approvalRequired: false,
      riskClass,
    };
  }

  const requiresApproval = matchingPermissions.some((p) => p.effect === "REQUIRE_APPROVAL");

  return {
    effect: requiresApproval ? "REQUIRE_APPROVAL" : "ALLOW",
    reasonCodes: [],
    policyVersion,
    matchedRuleIds: [matchedGrant.id],
    approvalRequired: requiresApproval,
    grantId: matchedGrant.id,
    riskClass,
  };
}

export async function grantAgentCapability(
  ctx: TenantContext,
  input: GrantAgentCapabilityInput
) {
  // Founder guard
  await requireFounderAuthorization(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const agentMemberId = BigInt(input.agentWorkforceMemberId);

  // Validate agent member exists and is AI_AGENT in same workspace
  const [member] = await db
    .select({
      id: identityWorkforceMembers.id,
      memberType: identityWorkforceMembers.memberType,
      status: identityWorkforceMembers.status,
    })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, agentMemberId),
        eq(identityWorkforceMembers.workspaceId, wsId)
      )
    )
    .limit(1);

  if (!member || member.memberType !== "AI_AGENT" || member.status !== "active") {
    throw APIError.invalidArgument("Target must be an active AI_AGENT in this workspace");
  }

  // Validate capability binding exists
  const [binding] = await db
    .select()
    .from(coreCapabilityPermissionBindings)
    .where(eq(coreCapabilityPermissionBindings.capabilityId, input.capabilityId))
    .limit(1);

  if (!binding) {
    throw APIError.invalidArgument(`Unknown capability binding: ${input.capabilityId}`);
  }

  // Verify agent has an active role covering this permission
  const assignments = await db
    .select({ roleId: coreMemberRoleAssignments.roleId })
    .from(coreMemberRoleAssignments)
    .where(
      and(
        eq(coreMemberRoleAssignments.workspaceId, wsId),
        eq(coreMemberRoleAssignments.workforceMemberId, agentMemberId)
      )
    );

  const roleIds = assignments.map((a) => a.roleId);
  if (roleIds.length === 0) {
    throw APIError.failedPrecondition("Agent has no active roles in workspace");
  }

  const permissions = await db
    .select()
    .from(coreRolePermissions)
    .where(eq(coreRolePermissions.permissionKey, binding.permissionKey));

  const hasRolePermission = permissions.some((p) => roleIds.includes(p.roleId) && p.effect !== "DENY");
  if (!hasRolePermission) {
    throw APIError.failedPrecondition(
      `Agent role does not have permission for ${binding.permissionKey} (required by ${input.capabilityId})`
    );
  }

  const founderMemberId = BigInt(ctx.workforceMemberId!);

  return await db.transaction(async (tx) => {
    const [grant] = await tx
      .insert(coreAgentCapabilityGrants)
      .values({
        workspaceId: wsId,
        agentWorkforceMemberId: agentMemberId,
        capabilityId: input.capabilityId,
        projectId: input.projectId ? BigInt(input.projectId) : null,
        legalEntityId: input.legalEntityId ? BigInt(input.legalEntityId) : null,
        constraints: input.constraints ?? {},
        validUntil: input.validUntil ? new Date(input.validUntil) : null,
        status: "ACTIVE",
        grantedByFounderMemberId: founderMemberId,
      })
      .returning();

    await appendAuthorizationEvent(tx, {
      workspaceId: ctx.workspaceId,
      eventType: "AGENT_CAPABILITY_GRANTED",
      actorMemberId: ctx.workforceMemberId,
      targetMemberId: input.agentWorkforceMemberId,
      capabilityId: input.capabilityId,
      grantId: grant.id,
      reason: "Founder grant",
      correlationId: ctx.correlationId,
      details: { constraints: input.constraints, validUntil: input.validUntil },
    });

    await advanceAuthorizationEpoch(tx, ctx.workspaceId, ctx.workforceMemberId, "Grant agent capability");

    return grant;
  });
}

export async function revokeAgentCapability(
  ctx: TenantContext,
  input: RevokeAgentCapabilityInput
) {
  await requireFounderAuthorization(ctx);

  const wsId = BigInt(ctx.workspaceId);

  const [grant] = await db
    .select()
    .from(coreAgentCapabilityGrants)
    .where(
      and(
        eq(coreAgentCapabilityGrants.id, input.grantId),
        eq(coreAgentCapabilityGrants.workspaceId, wsId)
      )
    )
    .limit(1);

  if (!grant) {
    throw APIError.notFound(`Grant ${input.grantId} not found`);
  }

  return await db.transaction(async (tx) => {
    const [revoked] = await tx
      .update(coreAgentCapabilityGrants)
      .set({
        status: "REVOKED",
        revokedAt: new Date(),
        revokeReason: input.reason,
      })
      .where(eq(coreAgentCapabilityGrants.id, input.grantId))
      .returning();

    await appendAuthorizationEvent(tx, {
      workspaceId: ctx.workspaceId,
      eventType: "AGENT_CAPABILITY_REVOKED",
      actorMemberId: ctx.workforceMemberId,
      targetMemberId: String(grant.agentWorkforceMemberId),
      capabilityId: grant.capabilityId,
      grantId: grant.id,
      reason: input.reason,
      correlationId: ctx.correlationId,
    });

    await advanceAuthorizationEpoch(tx, ctx.workspaceId, ctx.workforceMemberId, input.reason);

    return revoked;
  });
}

export async function getAuthorizationOverview(ctx: TenantContext) {
  await requireFounderAuthorization(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const authState = await getWorkspaceAuthorizationState(ctx.workspaceId);
  const latestPolicyVersion = await getLatestPolicyVersion(wsId);

  // 1. Roles
  const roles = await db
    .select()
    .from(coreWorkspaceRoles)
    .where(eq(coreWorkspaceRoles.workspaceId, wsId));

  const roleIds = roles.map((r) => r.id);
  const rolePermissionsMap = new Map<string, Array<{ permissionKey: string; effect: string }>>();
  if (roleIds.length > 0) {
    const permissions = await db.select().from(coreRolePermissions);
    for (const p of permissions) {
      if (roleIds.includes(p.roleId)) {
        if (!rolePermissionsMap.has(p.roleId)) {
          rolePermissionsMap.set(p.roleId, []);
        }
        rolePermissionsMap.get(p.roleId)!.push({
          permissionKey: p.permissionKey,
          effect: p.effect,
        });
      }
    }
  }

  const roleItems = roles.map((r) => ({
    id: r.id,
    roleKey: r.roleKey,
    name: r.name,
    isSystem: r.isSystem,
    allowedMemberTypes: r.allowedMemberTypes || ["HUMAN", "AI_AGENT"],
    permissions: rolePermissionsMap.get(r.id) || [],
  }));

  // 2. Member Assignments
  const assignments = await db
    .select({
      id: coreMemberRoleAssignments.id,
      workforceMemberId: coreMemberRoleAssignments.workforceMemberId,
      roleId: coreMemberRoleAssignments.roleId,
      roleKey: coreWorkspaceRoles.roleKey,
      roleName: coreWorkspaceRoles.name,
      memberType: identityWorkforceMembers.memberType,
      roleTitle: identityWorkforceMembers.roleTitle,
      validFrom: coreMemberRoleAssignments.validFrom,
      validUntil: coreMemberRoleAssignments.validUntil,
    })
    .from(coreMemberRoleAssignments)
    .innerJoin(coreWorkspaceRoles, eq(coreMemberRoleAssignments.roleId, coreWorkspaceRoles.id))
    .innerJoin(identityWorkforceMembers, eq(coreMemberRoleAssignments.workforceMemberId, identityWorkforceMembers.id))
    .where(eq(coreMemberRoleAssignments.workspaceId, wsId));

  const assignmentItems = assignments.map((a) => ({
    id: a.id,
    workforceMemberId: String(a.workforceMemberId),
    roleId: a.roleId,
    roleKey: a.roleKey,
    roleName: a.roleName,
    memberType: a.memberType,
    roleTitle: a.roleTitle,
    validFrom: a.validFrom.toISOString(),
    validUntil: a.validUntil ? a.validUntil.toISOString() : null,
  }));

  // 3. Grants
  const grants = await db
    .select()
    .from(coreAgentCapabilityGrants)
    .where(eq(coreAgentCapabilityGrants.workspaceId, wsId));

  const grantItems = grants.map((g) => ({
    id: g.id,
    agentWorkforceMemberId: String(g.agentWorkforceMemberId),
    capabilityId: g.capabilityId,
    projectId: g.projectId ? String(g.projectId) : null,
    legalEntityId: g.legalEntityId ? String(g.legalEntityId) : null,
    constraints: g.constraints as Record<string, unknown>,
    validFrom: g.validFrom.toISOString(),
    validUntil: g.validUntil ? g.validUntil.toISOString() : null,
    status: g.status,
    grantedByFounderMemberId: String(g.grantedByFounderMemberId),
    revokedAt: g.revokedAt ? g.revokedAt.toISOString() : null,
    revokeReason: g.revokeReason,
  }));

  // 4. Catalog bindings
  const bindings = await db.select().from(coreCapabilityPermissionBindings);
  const bindingItems: CapabilityPermissionBinding[] = bindings.map((b) => ({
    capabilityId: b.capabilityId,
    permissionKey: b.permissionKey,
    riskClass: b.riskClass as CapabilityRiskClass,
    version: b.version,
  }));

  // 5. Workforce members
  const members = await db
    .select({
      id: identityWorkforceMembers.id,
      memberType: identityWorkforceMembers.memberType,
      status: identityWorkforceMembers.status,
      roleTitle: identityWorkforceMembers.roleTitle,
      agentSpecId: identityWorkforceMembers.agentSpecId,
      agentSpecVersion: identityWorkforceMembers.agentSpecVersion,
      humanUserId: identityWorkforceMembers.humanUserId,
      createdAt: identityWorkforceMembers.createdAt,
    })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.workspaceId, wsId),
        isNull(identityWorkforceMembers.deletedAt)
      )
    );

  const memberItems = members.map((m) => ({
    id: String(m.id),
    memberType: m.memberType,
    status: m.status,
    roleTitle: m.roleTitle,
    agentSpecId: m.agentSpecId,
    agentSpecVersion: m.agentSpecVersion,
    humanUserId: m.humanUserId ? String(m.humanUserId) : null,
    createdAt: m.createdAt.toISOString(),
  }));

  // 6. Recent audit events
  const events = await db
    .select()
    .from(coreAuthorizationEvents)
    .where(eq(coreAuthorizationEvents.workspaceId, wsId))
    .orderBy(desc(coreAuthorizationEvents.createdAt))
    .limit(50);

  const eventItems = events.map((e) => ({
    id: e.id,
    eventType: e.eventType,
    actorMemberId: e.actorMemberId ? String(e.actorMemberId) : null,
    targetMemberId: e.targetMemberId ? String(e.targetMemberId) : null,
    capabilityId: e.capabilityId,
    roleId: e.roleId,
    grantId: e.grantId,
    policyVersion: e.policyVersion,
    authorizationEpoch: e.authorizationEpoch,
    reason: e.reason,
    createdAt: e.createdAt.toISOString(),
  }));

  return {
    workspaceId: ctx.workspaceId,
    enforcementMode: authState.enforcementMode,
    authorizationEpoch: authState.authorizationEpoch,
    policyVersion: latestPolicyVersion,
    members: memberItems,
    roles: roleItems,
    assignments: assignmentItems,
    grants: grantItems,
    bindings: bindingItems,
    events: eventItems,
  };
}
