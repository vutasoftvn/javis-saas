import { describe, expect, it } from "vitest";
import { eq, and } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";
import { randomUUID } from "node:crypto";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  getPermissionsService,
  simulatePermissionsService,
  updatePermissionsService,
} from "../services/permissions.service";
import { coreRolePermissions } from "../../shared/db/schema/identity";

describe("permissions-api service", () => {
  it("auditor cannot update permissions", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "auditor" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Auditor",
      status: "active",
    });

    const auditorCtx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "auditor",
      permissions: ["read"],
      correlationId: "auditor-test-1",
    };

    await expect(
      updatePermissionsService(auditorCtx, {
        expectedVersion: 1,
        reason: "Malicious update attempt",
        mutations: [
          {
            kind: "SET_ROLE_PERMISSION",
            roleId: randomUUID(),
            permissionKey: "agent.policy.manage",
            effect: "ALLOW",
          },
        ],
      })
    ).rejects.toThrow();
  });

  it("simulate does not mutate database", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });

    const founderCtx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "founder-sim-1",
    };

    const initialData = await getPermissionsService(founderCtx);
    const initialVersion = initialData.version;

    const simResult = await simulatePermissionsService(founderCtx, {
      action: "finance.request.create",
      scope: {
        workspaceId: ws.workspaceId,
        projectId: "999",
      },
      facts: {
        amount: {
          currency: "USD",
          minor: "50000",
        },
      },
    });

    expect(simResult).toBeDefined();
    expect(simResult.decision).toBeDefined();

    // Verify DB was NOT mutated
    const afterData = await getPermissionsService(founderCtx);
    expect(afterData.version).toBe(initialVersion);
    expect(afterData.assignments.length).toBe(initialData.assignments.length);
  });

  it("rejects concurrent or stale PUT with VERSION_CONFLICT", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });

    const founderCtx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "founder-conflict-1",
    };

    // Stale version: 999 instead of 1
    await expect(
      updatePermissionsService(founderCtx, {
        expectedVersion: 999,
        reason: "Stale update attempt",
        mutations: [],
      })
    ).rejects.toThrow(/VERSION_CONFLICT/);
  });

  it("updates permissions, increments version, and protects last founder", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });

    const founderCtx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "founder-update-1",
    };

    // Create a custom role in workspace
    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "operator",
      name: "Operator Role",
      isSystem: false,
    });

    // Create another workforce member to assign (e.g. AI_AGENT member)
    const operatorMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: operatorMemberId,
      workspaceId: wsId,
      memberType: "AI_AGENT",
      agentSpecId: "operator_agent",
      agentSpecVersion: "1.0.0",
      roleTitle: "Operator Agent",
      status: "active",
    });

    const initial = await getPermissionsService(founderCtx);

    // Apply mutation: SET_ROLE_PERMISSION & ASSIGN_ROLE
    const updateRes = await updatePermissionsService(founderCtx, {
      expectedVersion: initial.version,
      reason: "Giao quyền operator",
      mutations: [
        {
          kind: "SET_ROLE_PERMISSION",
          roleId,
          permissionKey: "execution.plan.approve",
          effect: "ALLOW",
        },
        {
          kind: "ASSIGN_ROLE",
          memberId: String(operatorMemberId),
          roleId,
        },
      ],
    });

    expect(updateRes.success).toBe(true);
    expect(updateRes.version).toBe(initial.version + 1);

    // Fetch again and verify
    const updated = await getPermissionsService(founderCtx);
    expect(updated.version).toBe(initial.version + 1);
    const assigned = updated.assignments.find(
      (a) => String(a.workforceMemberId) === String(operatorMemberId)
    );
    expect(assigned).toBeDefined();
    expect(assigned?.roleId).toBe(roleId);

    // Create founder role and assignment
    const founderRoleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: founderRoleId,
      workspaceId: wsId,
      roleKey: "founder",
      name: "Founder Role",
      isSystem: true,
    });

    const founderAssignmentId = randomUUID();
    await db.insert(coreMemberRoleAssignments).values({
      id: founderAssignmentId,
      workspaceId: wsId,
      workforceMemberId,
      roleId: founderRoleId,
    });

    const currentVersion = updated.version;
    // Attempting to revoke this sole founder role should fail
    await expect(
      updatePermissionsService(founderCtx, {
        expectedVersion: currentVersion,
        reason: "Try to revoke last founder",
        mutations: [
          {
            kind: "REVOKE_ROLE",
            assignmentId: founderAssignmentId,
          },
        ],
      })
    ).rejects.toThrow(/CANNOT_REVOKE_LAST_FOUNDER/);
  });

  it("PUT without conditions preserves existing maxAmountMinor/currency instead of wiping it (IA15)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });

    const founderCtx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "founder-preserve-conditions",
    };

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "spender",
      name: "Spender Role",
      isSystem: false,
    });

    const initial = await getPermissionsService(founderCtx);

    // 1. Set with a maxAmountMinor/currency limit.
    const afterFirst = await updatePermissionsService(founderCtx, {
      expectedVersion: initial.version,
      reason: "Set spending limit",
      mutations: [
        {
          kind: "SET_ROLE_PERMISSION",
          roleId,
          permissionKey: "finance.request.create",
          effect: "ALLOW",
          conditions: { maxAmountMinor: "1000000", currency: "VND" },
        },
      ],
    });
    expect(afterFirst.success).toBe(true);

    // 2. Second PUT changes only the effect, omitting conditions entirely
    // (mirrors the Flutter controller sending effect without conditions).
    await updatePermissionsService(founderCtx, {
      expectedVersion: afterFirst.version,
      reason: "Flip to REQUIRE_APPROVAL, forgot to resend conditions",
      mutations: [
        {
          kind: "SET_ROLE_PERMISSION",
          roleId,
          permissionKey: "finance.request.create",
          effect: "REQUIRE_APPROVAL",
        },
      ],
    });

    const [row] = await db
      .select()
      .from(coreRolePermissions)
      .where(
        and(
          eq(coreRolePermissions.roleId, roleId),
          eq(coreRolePermissions.permissionKey, "finance.request.create")
        )
      );
    expect(row.effect).toBe("REQUIRE_APPROVAL");
    expect(row.conditions).toEqual({ maxAmountMinor: "1000000", currency: "VND" });
  });
});
