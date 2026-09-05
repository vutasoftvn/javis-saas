import { describe, expect, it } from "vitest";
import {
  combinePermissionRules,
  PermissionEffect,
  PermissionRule,
} from "../services/permission-evaluator";
import {
  authorizeBusinessAction,
  requireBusinessAction,
} from "../services/business-authorization.service";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db, schema } from "../../identity/models/db";
import {
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  coreWorkspacePolicyVersions,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";
import { randomUUID } from "node:crypto";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { APIError } from "encore.dev/api";

describe("permission-evaluator unit", () => {
  it("combines rules with DENY > REQUIRE_APPROVAL > ALLOW", () => {
    expect(combinePermissionRules([])).toBe("DENY");

    expect(
      combinePermissionRules([
        { id: "r1", effect: "ALLOW" },
        { id: "r2", effect: "REQUIRE_APPROVAL" },
      ])
    ).toBe("REQUIRE_APPROVAL");

    expect(
      combinePermissionRules([
        { id: "r1", effect: "ALLOW" },
        { id: "r2", effect: "DENY" },
      ])
    ).toBe("DENY");

    expect(
      combinePermissionRules([
        { id: "r1", effect: "REQUIRE_APPROVAL" },
        { id: "r2", effect: "DENY" },
      ])
    ).toBe("DENY");

    expect(
      combinePermissionRules([
        { id: "r1", effect: "ALLOW" },
        { id: "r2", effect: "ALLOW" },
      ])
    ).toBe("ALLOW");
  });
});

describe("permission-evaluator db & scoping", () => {
  it("evaluates scoped role assignments and expiration", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const wsId = BigInt(ws.workspaceId);

    // Create a workforce member
    const workforceMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Finance Operator",
      status: "active",
    });

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "project_finance",
      name: "Project Finance",
      isSystem: false,
    });

    // Add permissions to role
    await db.insert(coreRolePermissions).values({
      roleId,
      permissionKey: "finance.request.create",
      effect: "ALLOW",
      conditions: {},
    });

    const projectIdA = generateSnowflake();
    const projectIdB = generateSnowflake();

    // Assign role scoped to Project A
    const assignmentId = randomUUID();
    await db.insert(coreMemberRoleAssignments).values({
      id: assignmentId,
      workspaceId: wsId,
      workforceMemberId,
      roleId,
      projectId: projectIdA,
      validFrom: new Date(Date.now() - 60000),
      validUntil: new Date(Date.now() + 60000),
    });

    const ctx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "member",
      permissions: [],
      correlationId: "test-corr",
    };

    // Action matching project A: ALLOW
    const decisionA = await authorizeBusinessAction(
      ctx,
      "finance.request.create",
      { workspaceId: ws.workspaceId, projectId: String(projectIdA) }
    );
    expect(decisionA.effect).toBe("ALLOW");

    // Action matching project B: DENY (scoped to project A only)
    const decisionB = await authorizeBusinessAction(
      ctx,
      "finance.request.create",
      { workspaceId: ws.workspaceId, projectId: String(projectIdB) }
    );
    expect(decisionB.effect).toBe("DENY");

    // Unknown action: DENY
    const decisionUnknown = await authorizeBusinessAction(
      ctx,
      "unknown.action.do_something",
      { workspaceId: ws.workspaceId, projectId: String(projectIdA) }
    );
    expect(decisionUnknown.effect).toBe("DENY");
  });

  it("handles expired assignment and DENY override", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const wsId = BigInt(ws.workspaceId);

    const workforceMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Operator",
      status: "active",
    });

    const roleAllowId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleAllowId,
      workspaceId: wsId,
      roleKey: "role_allow",
      name: "Role Allow",
      isSystem: false,
    });
    await db.insert(coreRolePermissions).values({
      roleId: roleAllowId,
      permissionKey: "strategy.write",
      effect: "ALLOW",
      conditions: {},
    });

    // Assign role_allow with expired validity
    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId,
      roleId: roleAllowId,
      validFrom: new Date(Date.now() - 120000),
      validUntil: new Date(Date.now() - 60000), // EXPIRED
    });

    const ctx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "member",
      permissions: [],
      correlationId: "test-corr-expired",
    };

    // Expired -> DENY
    const decisionExpired = await authorizeBusinessAction(
      ctx,
      "strategy.write",
      { workspaceId: ws.workspaceId }
    );
    expect(decisionExpired.effect).toBe("DENY");

    // Now assign active role_allow AND active role_deny
    const roleDenyId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleDenyId,
      workspaceId: wsId,
      roleKey: "role_deny",
      name: "Role Deny",
      isSystem: false,
    });
    await db.insert(coreRolePermissions).values({
      roleId: roleDenyId,
      permissionKey: "strategy.write",
      effect: "DENY",
      conditions: {},
    });

    // Active allow
    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId,
      roleId: roleAllowId,
      validFrom: new Date(Date.now() - 60000),
      validUntil: new Date(Date.now() + 60000),
    });

    // Active deny
    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId,
      roleId: roleDenyId,
      validFrom: new Date(Date.now() - 60000),
      validUntil: new Date(Date.now() + 60000),
    });

    // DENY must win over ALLOW
    const decisionConflict = await authorizeBusinessAction(
      ctx,
      "strategy.write",
      { workspaceId: ws.workspaceId }
    );
    expect(decisionConflict.effect).toBe("DENY");

    // requireBusinessAction throws APIError.permissionDenied on DENY
    await expect(
      requireBusinessAction(ctx, "strategy.write", { workspaceId: ws.workspaceId })
    ).rejects.toThrow(APIError);
  });

  it("enforces money condition limits and rejects different currency", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const wsId = BigInt(ws.workspaceId);

    const workforceMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Finance Officer",
      status: "active",
    });

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "finance_spender",
      name: "Finance Spender",
      isSystem: false,
    });

    await db.insert(coreRolePermissions).values({
      roleId,
      permissionKey: "finance.request.create",
      effect: "ALLOW",
      conditions: {
        maxAmountMinor: "1000000",
        currency: "VND",
      },
    });

    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId,
      roleId,
      validFrom: new Date(Date.now() - 60000),
      validUntil: new Date(Date.now() + 60000),
    });

    const ctx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(workforceMemberId),
      membershipRole: "member",
      permissions: [],
      correlationId: "test-corr-money",
    };

    // Amount within limit (500,000 VND <= 1,000,000 VND) -> ALLOW
    const decisionOk = await authorizeBusinessAction(
      ctx,
      "finance.request.create",
      { workspaceId: ws.workspaceId },
      { amount: { minor: "500000", currency: "VND" } }
    );
    expect(decisionOk.effect).toBe("ALLOW");

    // Amount exceeds limit (2,000,000 VND > 1,000,000 VND) -> DENY
    const decisionExceed = await authorizeBusinessAction(
      ctx,
      "finance.request.create",
      { workspaceId: ws.workspaceId },
      { amount: { minor: "2000000", currency: "VND" } }
    );
    expect(decisionExceed.effect).toBe("DENY");

    // Currency mismatch (USD != VND) -> DENY (cannot compare different currencies)
    const decisionDiffCurrency = await authorizeBusinessAction(
      ctx,
      "finance.request.create",
      { workspaceId: ws.workspaceId },
      { amount: { minor: "100", currency: "USD" } }
    );
    expect(decisionDiffCurrency.effect).toBe("DENY");
  });
});
