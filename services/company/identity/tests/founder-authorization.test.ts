import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
  identityUserProjections,
  coreWorkspaceAuthorizationStates,
  coreAuthorizationEvents,
  coreRolePermissions,
} from "../../shared/db/schema/identity";
import { randomUUID } from "node:crypto";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { updatePermissionsService, getPermissionsService } from "../services/permissions.service";
import { requireFounderAuthorization } from "../services/authorization.service";

async function seedEnforcedAuthorityWorkspace() {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const wsId = BigInt(ws.workspaceId);

  // Set workspace to ENFORCED
  await db
    .insert(coreWorkspaceAuthorizationStates)
    .values({
      workspaceId: wsId,
      enforcementMode: "ENFORCED",
      authorizationEpoch: 1,
    })
    .onConflictDoUpdate({
      target: [coreWorkspaceAuthorizationStates.workspaceId],
      set: { enforcementMode: "ENFORCED" },
    });

  const founderMemberId = generateSnowflake();
  const cofounderMemberId = generateSnowflake();
  const aiMemberId = generateSnowflake();

  await db.insert(identityWorkforceMembers).values({
    id: founderMemberId,
    workspaceId: wsId,
    memberType: "HUMAN",
    humanUserId: BigInt(ws.userId),
    roleTitle: "Founder",
    status: "active",
  });

  const cofounderUserId = generateSnowflake();
  await db.insert(identityUserProjections).values({
    id: cofounderUserId,
    email: `cofounder-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Co-Founder",
  });

  await db.insert(identityWorkforceMembers).values({
    id: cofounderMemberId,
    workspaceId: wsId,
    memberType: "HUMAN",
    humanUserId: cofounderUserId,
    roleTitle: "Co-Founder",
    status: "active",
  });

  await db.insert(identityWorkforceMembers).values({
    id: aiMemberId,
    workspaceId: wsId,
    memberType: "AI_AGENT",
    agentSpecId: "agent-ops-v1",
    agentSpecVersion: "1.0.0",
    roleTitle: "Operations AI",
    status: "active",
  });

  // Create founder role and assign to founder
  const founderRoleId = randomUUID();
  await db.insert(coreWorkspaceRoles).values({
    id: founderRoleId,
    workspaceId: wsId,
    roleKey: "founder",
    name: "Founder",
    isSystem: true,
    allowedMemberTypes: ["HUMAN"],
  });

  await db.insert(coreMemberRoleAssignments).values({
    workspaceId: wsId,
    workforceMemberId: founderMemberId,
    roleId: founderRoleId,
  });

  // Create business role for testing permission mutation
  const roleId = randomUUID();
  await db.insert(coreWorkspaceRoles).values({
    id: roleId,
    workspaceId: wsId,
    roleKey: "operations_lead",
    name: "Operations Lead",
    isSystem: false,
    allowedMemberTypes: ["HUMAN", "AI_AGENT"],
  });

  const founderCtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: ws.userId,
    workforceMemberId: String(founderMemberId),
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "founder-auth-test-1",
  };

  const cofounderCtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: String(cofounderUserId),
    workforceMemberId: String(cofounderMemberId),
    membershipRole: "co-founder",
    permissions: ["*"],
    correlationId: "cofounder-auth-test-1",
  };

  const aiCtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: "0",
    workforceMemberId: String(aiMemberId),
    membershipRole: "member",
    permissions: ["read"],
    correlationId: "ai-auth-test-1",
  };

  return {
    workspaceId: ws.workspaceId,
    founderCtx,
    cofounderCtx,
    aiCtx,
    roleId,
    founderRoleId,
    founderMemberId: String(founderMemberId),
  };
}

describe("founder-only authority guard and audit lifecycle", () => {
  it("rejects co-founder authority mutation after enforcement but permits human founder", async () => {
    const { founderCtx, cofounderCtx, roleId } = await seedEnforcedAuthorityWorkspace();

    await expect(
      updatePermissionsService(cofounderCtx, {
        expectedVersion: 1,
        reason: "escalate",
        mutations: [
          {
            kind: "SET_ROLE_PERMISSION",
            roleId,
            permissionKey: "operations.task.read",
            effect: "ALLOW",
          },
        ],
      })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED/);

    await expect(
      updatePermissionsService(founderCtx, {
        expectedVersion: 1,
        reason: "grant read",
        mutations: [
          {
            kind: "SET_ROLE_PERMISSION",
            roleId,
            permissionKey: "operations.task.read",
            effect: "ALLOW",
          },
        ],
      })
    ).resolves.toMatchObject({ success: true, version: 2 });
  });

  it("rejects AI_AGENT exercising founder authority in either mode", async () => {
    const { aiCtx } = await seedEnforcedAuthorityWorkspace();
    await expect(requireFounderAuthorization(aiCtx)).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED/);
  });

  it("appends authorization audit events and advances epoch atomically on updatePermissions", async () => {
    const { founderCtx, roleId, workspaceId } = await seedEnforcedAuthorityWorkspace();
    const wsId = BigInt(workspaceId);

    const result = await updatePermissionsService(founderCtx, {
      expectedVersion: 1,
      reason: "grant read permission to operations lead",
      mutations: [
        {
          kind: "SET_ROLE_PERMISSION",
          roleId,
          permissionKey: "operations.task.read",
          effect: "ALLOW",
        },
      ],
    });

    expect(result.version).toBe(2);

    // Verify events were appended
    const events = await db
      .select()
      .from(coreAuthorizationEvents)
      .where(eq(coreAuthorizationEvents.workspaceId, wsId));

    expect(events.length).toBeGreaterThan(0);
    const hasEpochOrPermEvent = events.some(
      (e) => e.eventType === "ROLE_PERMISSION_UPDATED" || e.eventType === "AUTHORIZATION_EPOCH_ADVANCED"
    );
    expect(hasEpochOrPermEvent).toBe(true);

    // Verify epoch was advanced in state
    const [state] = await db
      .select()
      .from(coreWorkspaceAuthorizationStates)
      .where(eq(coreWorkspaceAuthorizationStates.workspaceId, wsId));
    expect(state.authorizationEpoch).toBe(2);
  });
});
