import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  coreWorkspacePolicyVersions,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";
import { randomUUID } from "node:crypto";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { evaluateBusinessPolicyService } from "../services/business-policy.service";
import type { TenantContext } from "../../shared/types/tenant_context";

describe("policy-snapshot (A3)", () => {
  it("resolves business policy decision with version and hash", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const wsId = BigInt(ws.workspaceId);

    const wfMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: wfMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Staff",
      status: "active",
    });

    // Seed policy version
    await db.insert(coreWorkspacePolicyVersions).values({
      workspaceId: wsId,
      version: 1,
      policyHash: "hash-v1",
      reason: "Initial policy",
    });

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "staff_role",
      name: "Staff Role",
      isSystem: false,
    });

    await db.insert(coreRolePermissions).values({
      roleId,
      permissionKey: "finance.request.create",
      effect: "REQUIRE_APPROVAL",
      conditions: {},
    });

    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId: wfMemberId,
      roleId,
      validFrom: new Date(Date.now() - 60000),
      validUntil: new Date(Date.now() + 60000),
    });

    const ctx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: String(wfMemberId),
      membershipRole: "member",
      permissions: [],
      correlationId: "corr-eval-1",
    };

    // 1. Before revocation: REQUIRE_APPROVAL
    const res1 = await evaluateBusinessPolicyService({
      ctx,
      action: "finance.request.create",
      resourceRef: "fin_req_1",
      version: 1,
      runRef: "run_1",
    });

    expect(res1.decision.effect).toBe("REQUIRE_APPROVAL");
    expect(res1.policyVersion).toBe(1);
    expect(res1.policyHash).toBe("hash-v1");

    // 2. Revoke permission in role -> update to DENY
    await db
      .update(coreRolePermissions)
      .set({ effect: "DENY" })
      .where(eq(coreRolePermissions.roleId, roleId));

    // Bump policy version to 2
    await db.insert(coreWorkspacePolicyVersions).values({
      workspaceId: wsId,
      version: 2,
      policyHash: "hash-v2",
      reason: "Revoked finance.request.create",
    });

    // 3. After revocation: DENY immediately
    const res2 = await evaluateBusinessPolicyService({
      ctx,
      action: "finance.request.create",
      resourceRef: "fin_req_1",
      version: 2,
      runRef: "run_1",
    });

    expect(res2.decision.effect).toBe("DENY");
    expect(res2.policyVersion).toBe(2);
    expect(res2.policyHash).toBe("hash-v2");
  });
});
