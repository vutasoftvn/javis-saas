import { and, eq, inArray } from "drizzle-orm";
import {
  coreAgentCapabilityGrants,
  coreCapabilityPermissionBindings,
  coreMemberRoleAssignments,
  coreRolePermissions,
  coreWorkspaceRoles,
} from "../../shared/db/schema/identity";
import type { db } from "../models/db";
import {
  appendAuthorizationEvent,
  advanceAuthorizationEpoch,
} from "../../identity/services/authorization.service";

// Spec 2026-09-27-chat-business-actions / ADR-CHAT-ACTIONS-001.
//
// Capability ghi mà founder CẤP cho AI member khi kích hoạt profile trong Project startup team.
// Kích hoạt là hành động của founder; mỗi lần chạy thật vẫn phải qua founder duyệt trong chat
// (T2) và live authorization ticket. Tập này = capability_refs của spec profile ∩ capability
// T1/T2 có AGENT_CAP trong apps/cosa/capabilities/access_matrix.py — test parity
// tests/apps/cosa/test_agent_capability_grants_parity.py chặn lệch.
//
// Cố ý KHÔNG tự cấp `finance.transaction.record`: hạn mức chưa được founder chốt (spec §8.3);
// founder cấp tay qua POST /identity/agent-capability-grants với constraints.maxAmountMinor.
export const AGENT_PROFILE_GRANTED_CAPABILITIES: Readonly<Record<string, readonly string[]>> =
  Object.freeze({
    operations: Object.freeze([
      "operations.task.create_draft",
      "operations.task.advance",
      "okr.key_result.create",
      "okr.key_result.checkin",
      "startup_os.goal.create",
      "startup_os.project.triage",
      "venture.profile.propose_update",
    ]),
    finance: Object.freeze([
      "finance.transaction.classify_propose",
      "finance.accounting_document.create_draft",
    ]),
  });

// Transaction Drizzle của operations (cùng DB workspace với bảng core.* của identity).
type DbLike = Parameters<Parameters<typeof db.transaction>[0]>[0];

// Role workspace gán cho AI member của startup team: live authorization ticket đòi AI member có
// role chứa permission của capability (identity/services/agent-authorization.service.ts bước 6),
// ngoài grant. Chỉ cho AI_AGENT; phạm vi thực tế vẫn do grant theo capability + Project quyết định.
export const STARTUP_TEAM_AGENT_ROLE_KEY = "startup_team_agent";

export interface ProfileGrantInput {
  workspaceId: string;
  projectId: string;
  profileKey: string;
  agentWorkforceMemberId: string;
  founderMemberId: string;
  correlationId?: string;
}

/**
 * Đảm bảo AI member có grant ACTIVE (scope Project) cho mọi capability của profile. Idempotent:
 * bỏ qua capability chưa có binding hoặc đã có grant ACTIVE cùng Project. Trả danh sách
 * capability vừa cấp mới.
 */
export async function ensureProfileCapabilityGrants(
  tx: DbLike,
  input: ProfileGrantInput
): Promise<string[]> {
  const capabilities = AGENT_PROFILE_GRANTED_CAPABILITIES[input.profileKey] ?? [];
  if (capabilities.length === 0) return [];
  const wsId = BigInt(input.workspaceId);
  const projectId = BigInt(input.projectId);
  const memberId = BigInt(input.agentWorkforceMemberId);

  const bound = await tx
    .select({
      capabilityId: coreCapabilityPermissionBindings.capabilityId,
      permissionKey: coreCapabilityPermissionBindings.permissionKey,
    })
    .from(coreCapabilityPermissionBindings)
    .where(inArray(coreCapabilityPermissionBindings.capabilityId, [...capabilities]));
  const boundIds = new Set<string>(bound.map((b) => b.capabilityId));
  await ensureStartupTeamAgentRole(tx, {
    workspaceId: input.workspaceId,
    agentWorkforceMemberId: input.agentWorkforceMemberId,
    permissionKeys: [...new Set(bound.map((b) => b.permissionKey))],
  });

  const existing = await tx
    .select({ capabilityId: coreAgentCapabilityGrants.capabilityId })
    .from(coreAgentCapabilityGrants)
    .where(
      and(
        eq(coreAgentCapabilityGrants.workspaceId, wsId),
        eq(coreAgentCapabilityGrants.agentWorkforceMemberId, memberId),
        eq(coreAgentCapabilityGrants.projectId, projectId),
        eq(coreAgentCapabilityGrants.status, "ACTIVE")
      )
    );
  const granted = new Set<string>(existing.map((g) => g.capabilityId));

  const created: string[] = [];
  for (const capabilityId of capabilities) {
    if (!boundIds.has(capabilityId) || granted.has(capabilityId)) continue;
    const [grant] = await tx
      .insert(coreAgentCapabilityGrants)
      .values({
        workspaceId: wsId,
        agentWorkforceMemberId: memberId,
        capabilityId,
        projectId,
        constraints: {},
        status: "ACTIVE",
        grantedByFounderMemberId: BigInt(input.founderMemberId),
      })
      .returning({ id: coreAgentCapabilityGrants.id });
    await appendAuthorizationEvent(tx, {
      workspaceId: input.workspaceId,
      eventType: "AGENT_CAPABILITY_GRANTED",
      actorMemberId: input.founderMemberId,
      targetMemberId: input.agentWorkforceMemberId,
      capabilityId,
      grantId: grant.id,
      reason: "Startup team activation",
      correlationId: input.correlationId,
      details: { projectId: input.projectId, profileKey: input.profileKey },
    });
    created.push(capabilityId);
  }
  if (created.length > 0) {
    await advanceAuthorizationEpoch(
      tx,
      input.workspaceId,
      input.founderMemberId,
      "Grant startup team capabilities"
    );
  }
  return created;
}

/**
 * Thu hồi grant đã cấp theo profile cho đúng Project khi founder tạm dừng agent. Trả danh sách
 * capability bị thu hồi.
 */
export async function revokeProfileCapabilityGrants(
  tx: DbLike,
  input: Omit<ProfileGrantInput, "founderMemberId"> & { actorMemberId?: string; reason: string }
): Promise<string[]> {
  const capabilities = AGENT_PROFILE_GRANTED_CAPABILITIES[input.profileKey] ?? [];
  if (capabilities.length === 0) return [];
  const revoked = await tx
    .update(coreAgentCapabilityGrants)
    .set({ status: "REVOKED", revokedAt: new Date(), revokeReason: input.reason })
    .where(
      and(
        eq(coreAgentCapabilityGrants.workspaceId, BigInt(input.workspaceId)),
        eq(coreAgentCapabilityGrants.agentWorkforceMemberId, BigInt(input.agentWorkforceMemberId)),
        eq(coreAgentCapabilityGrants.projectId, BigInt(input.projectId)),
        eq(coreAgentCapabilityGrants.status, "ACTIVE"),
        inArray(coreAgentCapabilityGrants.capabilityId, [...capabilities])
      )
    )
    .returning({
      id: coreAgentCapabilityGrants.id,
      capabilityId: coreAgentCapabilityGrants.capabilityId,
    });
  for (const row of revoked) {
    await appendAuthorizationEvent(tx, {
      workspaceId: input.workspaceId,
      eventType: "AGENT_CAPABILITY_REVOKED",
      actorMemberId: input.actorMemberId,
      targetMemberId: input.agentWorkforceMemberId,
      capabilityId: row.capabilityId,
      grantId: row.id,
      reason: input.reason,
      correlationId: input.correlationId,
      details: { projectId: input.projectId, profileKey: input.profileKey },
    });
  }
  if (revoked.length > 0) {
    await advanceAuthorizationEpoch(
      tx,
      input.workspaceId,
      input.actorMemberId,
      "Revoke startup team capabilities"
    );
  }
  return revoked.map((r) => r.capabilityId);
}

/**
 * Đảm bảo role `startup_team_agent` của workspace tồn tại, có ALLOW cho các permission cần và
 * được gán cho AI member. Idempotent.
 */
export async function ensureStartupTeamAgentRole(
  tx: DbLike,
  input: { workspaceId: string; agentWorkforceMemberId: string; permissionKeys: string[] }
): Promise<void> {
  if (input.permissionKeys.length === 0) return;
  const wsId = BigInt(input.workspaceId);
  const memberId = BigInt(input.agentWorkforceMemberId);

  await tx
    .insert(coreWorkspaceRoles)
    .values({
      workspaceId: wsId,
      roleKey: STARTUP_TEAM_AGENT_ROLE_KEY,
      name: "Startup team agent",
      isSystem: true,
      allowedMemberTypes: ["AI_AGENT"],
    })
    .onConflictDoNothing();
  const [role] = await tx
    .select({ id: coreWorkspaceRoles.id })
    .from(coreWorkspaceRoles)
    .where(
      and(
        eq(coreWorkspaceRoles.workspaceId, wsId),
        eq(coreWorkspaceRoles.roleKey, STARTUP_TEAM_AGENT_ROLE_KEY)
      )
    )
    .limit(1);

  await tx
    .insert(coreRolePermissions)
    .values(
      input.permissionKeys.map((permissionKey) => ({
        roleId: role.id,
        permissionKey,
        effect: "ALLOW",
      }))
    )
    .onConflictDoNothing();

  const [assigned] = await tx
    .select({ id: coreMemberRoleAssignments.id })
    .from(coreMemberRoleAssignments)
    .where(
      and(
        eq(coreMemberRoleAssignments.workspaceId, wsId),
        eq(coreMemberRoleAssignments.workforceMemberId, memberId),
        eq(coreMemberRoleAssignments.roleId, role.id)
      )
    )
    .limit(1);
  if (!assigned) {
    await tx
      .insert(coreMemberRoleAssignments)
      .values({ workspaceId: wsId, workforceMemberId: memberId, roleId: role.id });
  }
}
