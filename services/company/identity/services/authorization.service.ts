import { APIError } from "encore.dev/api";
import { eq, and, desc, sql } from "drizzle-orm";
import { db } from "../models/db";
import {
  coreWorkspaceAuthorizationStates,
  coreAuthorizationEvents,
  coreWorkspaceRoles,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
  AuthorizationEnforcementMode,
} from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";

export interface FounderAuthorization {
  workspaceId: string;
  workforceMemberId: string;
  memberType: "HUMAN";
  hasActiveFounderRole: boolean;
  enforcementMode: AuthorizationEnforcementMode;
  authorizationEpoch: number;
}

export interface AuthorizationSubject {
  workforceMemberId: string;
  workspaceId: string;
  memberType: "HUMAN" | "AI_AGENT";
  hasActiveFounderRole: boolean;
  activeRoleKeys: string[];
}

export interface AuthorizationEventInput {
  workspaceId: string;
  eventType: string;
  actorMemberId?: string;
  targetMemberId?: string;
  capabilityId?: string;
  roleId?: string;
  grantId?: string;
  policyVersion?: number;
  authorizationEpoch?: number;
  beforeHash?: string;
  afterHash?: string;
  reason?: string;
  correlationId?: string;
  details?: Record<string, any>;
}

export async function resolveAuthorizationSubject(
  workspaceIdStr: string,
  workforceMemberIdStr?: string
): Promise<AuthorizationSubject> {
  if (!workforceMemberIdStr) {
    throw APIError.permissionDenied("WORKFORCE_MEMBER_REQUIRED: Caller has no workforce member record in workspace");
  }

  const wsId = BigInt(workspaceIdStr);
  const memberId = BigInt(workforceMemberIdStr);

  const [member] = await db
    .select({
      id: identityWorkforceMembers.id,
      workspaceId: identityWorkforceMembers.workspaceId,
      memberType: identityWorkforceMembers.memberType,
      status: identityWorkforceMembers.status,
    })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, memberId),
        eq(identityWorkforceMembers.workspaceId, wsId)
      )
    )
    .limit(1);

  if (!member || member.status !== "active") {
    throw APIError.permissionDenied("ACTIVE_WORKFORCE_MEMBER_REQUIRED");
  }

  const now = new Date();
  const assignments = await db
    .select({
      roleKey: coreWorkspaceRoles.roleKey,
      validFrom: coreMemberRoleAssignments.validFrom,
      validUntil: coreMemberRoleAssignments.validUntil,
    })
    .from(coreMemberRoleAssignments)
    .innerJoin(
      coreWorkspaceRoles,
      eq(coreMemberRoleAssignments.roleId, coreWorkspaceRoles.id)
    )
    .where(
      and(
        eq(coreMemberRoleAssignments.workspaceId, wsId),
        eq(coreMemberRoleAssignments.workforceMemberId, memberId)
      )
    );

  const activeRoles = assignments.filter((a) => {
    if (a.validFrom && a.validFrom > now) return false;
    if (a.validUntil && a.validUntil <= now) return false;
    return true;
  });

  const activeRoleKeys = activeRoles.map((r) => r.roleKey);
  const hasActiveFounderRole = activeRoleKeys.includes("founder");

  return {
    workforceMemberId: workforceMemberIdStr,
    workspaceId: workspaceIdStr,
    memberType: member.memberType as "HUMAN" | "AI_AGENT",
    hasActiveFounderRole,
    activeRoleKeys,
  };
}

export async function appendAuthorizationEvent(
  tx: any,
  event: AuthorizationEventInput
): Promise<void> {
  const client = tx || db;
  await client.insert(coreAuthorizationEvents).values({
    workspaceId: BigInt(event.workspaceId),
    eventType: event.eventType,
    actorMemberId: event.actorMemberId ? BigInt(event.actorMemberId) : null,
    targetMemberId: event.targetMemberId ? BigInt(event.targetMemberId) : null,
    capabilityId: event.capabilityId ?? null,
    roleId: event.roleId ?? null,
    grantId: event.grantId ?? null,
    policyVersion: event.policyVersion ?? null,
    authorizationEpoch: event.authorizationEpoch ?? null,
    beforeHash: event.beforeHash ?? null,
    afterHash: event.afterHash ?? null,
    reason: event.reason ?? null,
    correlationId: event.correlationId ?? null,
    details: event.details ?? {},
  });
}

export async function advanceAuthorizationEpoch(
  tx: any,
  workspaceIdStr: string,
  actorMemberIdStr?: string,
  reason?: string
): Promise<number> {
  const client = tx || db;
  const wsId = BigInt(workspaceIdStr);
  const [updated] = await client
    .update(coreWorkspaceAuthorizationStates)
    .set({
      authorizationEpoch: sql`${coreWorkspaceAuthorizationStates.authorizationEpoch} + 1`,
      updatedAt: new Date(),
    })
    .where(eq(coreWorkspaceAuthorizationStates.workspaceId, wsId))
    .returning({
      epoch: coreWorkspaceAuthorizationStates.authorizationEpoch,
    });

  const nextEpoch = updated ? updated.epoch : 2;

  await appendAuthorizationEvent(client, {
    workspaceId: workspaceIdStr,
    eventType: "AUTHORIZATION_EPOCH_ADVANCED",
    actorMemberId: actorMemberIdStr,
    authorizationEpoch: nextEpoch,
    reason: reason || "Advance authorization epoch",
  });

  return nextEpoch;
}

export async function getWorkspaceAuthorizationState(workspaceIdStr: string) {
  const wsId = BigInt(workspaceIdStr);
  const [state] = await db
    .select()
    .from(coreWorkspaceAuthorizationStates)
    .where(eq(coreWorkspaceAuthorizationStates.workspaceId, wsId))
    .limit(1);

  if (!state) {
    // Default to SHADOW mode epoch 1
    const [inserted] = await db
      .insert(coreWorkspaceAuthorizationStates)
      .values({
        workspaceId: wsId,
        enforcementMode: "SHADOW",
        authorizationEpoch: 1,
      })
      .onConflictDoNothing()
      .returning();

    if (inserted) return inserted;

    const [refetched] = await db
      .select()
      .from(coreWorkspaceAuthorizationStates)
      .where(eq(coreWorkspaceAuthorizationStates.workspaceId, wsId))
      .limit(1);
    return refetched ?? { workspaceId: wsId, enforcementMode: "SHADOW", authorizationEpoch: 1 };
  }

  return state;
}

export async function requireFounderAuthorization(ctx: TenantContext): Promise<FounderAuthorization> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  const subject = await resolveAuthorizationSubject(ctx.workspaceId, ctx.workforceMemberId);

  // Founder authority strictly belongs to HUMAN
  if (subject.memberType !== "HUMAN") {
    throw APIError.permissionDenied("FOUNDER_AUTHORITY_REQUIRED: Only HUMAN members can hold founder authority");
  }

  const state = await getWorkspaceAuthorizationState(ctx.workspaceId);
  const mode = state.enforcementMode as AuthorizationEnforcementMode;

  if (mode === "ENFORCED") {
    if (!subject.hasActiveFounderRole) {
      throw APIError.permissionDenied("FOUNDER_AUTHORITY_REQUIRED: Active human founder role required");
    }
  } else {
    // SHADOW mode: check legacy membershipRole
    const legacyRole = (ctx.membershipRole || "").toLowerCase();
    const legacyAllowed = ["founder", "co-founder"].includes(legacyRole);

    if (!subject.hasActiveFounderRole) {
      if (legacyAllowed) {
        await appendAuthorizationEvent(db, {
          workspaceId: ctx.workspaceId,
          eventType: "DISCREPANCY_LEGACY_VS_AUTHORITY",
          actorMemberId: ctx.workforceMemberId,
          reason: `Legacy role ${legacyRole} permitted mutation in SHADOW mode but subject lacks active founder role`,
          correlationId: ctx.correlationId,
          details: { legacyRole, hasActiveFounderRole: subject.hasActiveFounderRole },
        });
      } else {
        throw APIError.permissionDenied("FOUNDER_AUTHORITY_REQUIRED: Active human founder role required");
      }
    }
  }

  return {
    workspaceId: ctx.workspaceId,
    workforceMemberId: subject.workforceMemberId,
    memberType: "HUMAN",
    hasActiveFounderRole: subject.hasActiveFounderRole,
    enforcementMode: mode,
    authorizationEpoch: state.authorizationEpoch,
  };
}
