import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
  identityUserProjections,
  coreRolePermissions,
  coreCapabilityPermissionBindings,
  coreAgentCapabilityGrants,
  coreWorkspaceAuthorizationStates,
} from "../../shared/db/schema/identity";
import { randomUUID } from "node:crypto";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  evaluateAgentCapabilityAuthority,
  grantAgentCapability,
  revokeAgentCapability,
  getAuthorizationOverview,
} from "../services/agent-authorization.service";

export async function seedAgentAuthorityWorkspace(opts?: { capabilityId?: string }) {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const wsId = BigInt(ws.workspaceId);
  const capabilityId = opts?.capabilityId || "operations.task.list";

  const founderMemberId = generateSnowflake();
  const agentMemberId = generateSnowflake();

  await db.insert(identityWorkforceMembers).values({
    id: founderMemberId,
    workspaceId: wsId,
    memberType: "HUMAN",
    humanUserId: BigInt(ws.userId),
    roleTitle: "Founder",
    status: "active",
  });

  await db.insert(identityWorkforceMembers).values({
    id: agentMemberId,
    workspaceId: wsId,
    memberType: "AI_AGENT",
    agentSpecId: "agent-ops-v1",
    agentSpecVersion: "1.0.0",
    roleTitle: "Operations AI",
    status: "active",
  });

  // Assign founder role to founder
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

  // Create agent execution role with operations.task.read permission
  const agentRoleId = randomUUID();
  await db.insert(coreWorkspaceRoles).values({
    id: agentRoleId,
    workspaceId: wsId,
    roleKey: "task_executor",
    name: "Task Executor",
    isSystem: false,
    allowedMemberTypes: ["AI_AGENT"],
  });

  await db.insert(coreRolePermissions).values({
    roleId: agentRoleId,
    permissionKey: "operations.task.read",
    effect: "ALLOW",
  });

  // Assign agent role to agent member
  await db.insert(coreMemberRoleAssignments).values({
    workspaceId: wsId,
    workforceMemberId: agentMemberId,
    roleId: agentRoleId,
  });

  // Ensure capability binding exists
  await db
    .insert(coreCapabilityPermissionBindings)
    .values({
      capabilityId,
      permissionKey: "operations.task.read",
      riskClass: "READ",
      version: 1,
    })
    .onConflictDoNothing();

  const founderCtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: ws.userId,
    workforceMemberId: String(founderMemberId),
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "founder-grant-test-1",
  };

  return {
    workspaceId: ws.workspaceId,
    founderCtx,
    founderMemberId: String(founderMemberId),
    agentMemberId: String(agentMemberId),
    agentRoleId,
    capabilityId,
  };
}

describe("agent capability grant, mapping and authority evaluation", () => {
  it("denies an AI agent with a role but no exact capability grant", async () => {
    const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });
    const decision = await evaluateAgentCapabilityAuthority({
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
      scope: { workspaceId: seeded.workspaceId },
      facts: {},
    });
    expect(decision.effect).toBe("DENY");
    expect(decision.reasonCodes).toContain("MISSING_AGENT_CAPABILITY_GRANT");
  });

  it("permits AI agent after founder grants exact capability", async () => {
    const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });

    const grant = await grantAgentCapability(seeded.founderCtx, {
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
    });

    expect(grant.status).toBe("ACTIVE");
    expect(grant.capabilityId).toBe("operations.task.list");

    const decision = await evaluateAgentCapabilityAuthority({
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
      scope: { workspaceId: seeded.workspaceId },
      facts: {},
    });

    expect(decision.effect).toBe("ALLOW");
    expect(decision.grantId).toBe(grant.id);
    expect(decision.riskClass).toBe("READ");
  });

  it("denies when capability grant is revoked by founder", async () => {
    const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });

    const grant = await grantAgentCapability(seeded.founderCtx, {
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
    });

    await revokeAgentCapability(seeded.founderCtx, {
      grantId: grant.id,
      reason: "security rotation",
    });

    const decision = await evaluateAgentCapabilityAuthority({
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
      scope: { workspaceId: seeded.workspaceId },
      facts: {},
    });

    expect(decision.effect).toBe("DENY");
    expect(decision.reasonCodes).toContain("AGENT_CAPABILITY_GRANT_REVOKED");
  });

  it("denies when amount constraint is exceeded", async () => {
    const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });

    await grantAgentCapability(seeded.founderCtx, {
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
      constraints: { maxAmountMinor: "5000", currency: "USD" },
    });

    const decision = await evaluateAgentCapabilityAuthority({
      workspaceId: seeded.workspaceId,
      agentWorkforceMemberId: seeded.agentMemberId,
      capabilityId: "operations.task.list",
      scope: { workspaceId: seeded.workspaceId },
      facts: { amount: { minor: "10000", currency: "USD" } },
    });

    expect(decision.effect).toBe("DENY");
    expect(decision.reasonCodes).toContain("CONSTRAINT_AMOUNT_EXCEEDED");
  });

  it("rejects granting a capability to a HUMAN workforce member", async () => {
    const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });

    await expect(
      grantAgentCapability(seeded.founderCtx, {
        workspaceId: seeded.workspaceId,
        agentWorkforceMemberId: seeded.founderMemberId,
        capabilityId: "operations.task.list",
      })
    ).rejects.toThrow(/Target must be an active AI_AGENT/);
  });

  it("returns overview for workspace", async () => {
    const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });
    const overview = await getAuthorizationOverview(seeded.founderCtx);

    expect(overview.workspaceId).toBe(seeded.workspaceId);
    expect(overview.roles.length).toBeGreaterThan(0);
    expect(overview.bindings.length).toBeGreaterThan(0);
    expect(overview.enforcementMode).toBeDefined();
    expect(overview.authorizationEpoch).toBeDefined();
  });
});
