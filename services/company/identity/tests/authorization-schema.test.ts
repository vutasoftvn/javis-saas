import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
  coreWorkspaceAuthorizationStates,
  coreCapabilityPermissionBindings,
  coreAgentCapabilityGrants,
  coreAuthorizationEvents,
  coreAgentAuthorizationTickets,
} from "../../shared/db/schema/identity";
import { randomUUID } from "node:crypto";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { updatePermissionsService } from "../services/permissions.service";

async function seedAuthorityWorkspace() {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const wsId = BigInt(ws.workspaceId);
  const humanMemberId = generateSnowflake();
  const aiMemberId = generateSnowflake();

  await db.insert(identityWorkforceMembers).values({
    id: humanMemberId,
    workspaceId: wsId,
    memberType: "HUMAN",
    humanUserId: BigInt(ws.userId),
    roleTitle: "Founder",
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

  const founderRoleId = randomUUID();
  await db.insert(coreWorkspaceRoles).values({
    id: founderRoleId,
    workspaceId: wsId,
    roleKey: "founder",
    name: "Founder",
    isSystem: true,
    allowedMemberTypes: ["HUMAN"],
  });

  const founderCtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: ws.userId,
    workforceMemberId: String(humanMemberId),
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "founder-test-1",
  };

  return {
    workspaceId: ws.workspaceId,
    founderCtx,
    aiMemberId: String(aiMemberId),
    founderRoleId,
    humanMemberId: String(humanMemberId),
  };
}

describe("authorization schema and database invariants", () => {
  it("rejects assigning a HUMAN-only founder role to an AI_AGENT in the database", async () => {
    const { workspaceId, founderCtx, aiMemberId, founderRoleId } = await seedAuthorityWorkspace();
    await expect(
      updatePermissionsService(founderCtx, {
        expectedVersion: 1,
        reason: "invalid AI founder assignment",
        mutations: [{ kind: "ASSIGN_ROLE", memberId: aiMemberId, roleId: founderRoleId }],
      })
    ).rejects.toThrow(/ROLE_MEMBER_TYPE_MISMATCH/);

    await expect(
      db.insert(coreMemberRoleAssignments).values({
        workspaceId: BigInt(workspaceId),
        workforceMemberId: BigInt(aiMemberId),
        roleId: founderRoleId,
      })
    ).rejects.toThrow();
  });

  it("permits assigning a HUMAN-only role to a HUMAN member", async () => {
    const { workspaceId, humanMemberId, founderRoleId } = await seedAuthorityWorkspace();
    await expect(
      db.insert(coreMemberRoleAssignments).values({
        workspaceId: BigInt(workspaceId),
        workforceMemberId: BigInt(humanMemberId),
        roleId: founderRoleId,
      })
    ).resolves.toBeDefined();
  });

  it("exposes all required schema tables and defaults", async () => {
    expect(coreWorkspaceAuthorizationStates).toBeDefined();
    expect(coreCapabilityPermissionBindings).toBeDefined();
    expect(coreAgentCapabilityGrants).toBeDefined();
    expect(coreAuthorizationEvents).toBeDefined();
    expect(coreAgentAuthorizationTickets).toBeDefined();
  });
});
