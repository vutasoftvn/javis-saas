import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { randomUUID } from "node:crypto";
import { db } from "../../models/db";
import {
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
} from "../../../shared/db/schema/identity";
import { workspaceStrategySettings } from "../../../shared/db/schema/strategy";
import { eq } from "drizzle-orm";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import {
  getWorkspaceStrategySettings,
  updateWorkspaceStrategySettings,
  validateStrategySettings,
  validatePolicyOverride,
  DEFAULT_WORKSPACE_STRATEGY_SETTINGS,
  WorkspaceStrategySettings,
} from "../services/workspace-strategy-settings.service";
import {
  requireStrategyGovernanceAuthority,
  canExecuteStrategyGovernance,
} from "../services/strategy-governance-authorization.service";

function createMockTenantContext(overrides: Partial<TenantContext> & { workspaceId: string; userId: string; membershipRole: string }): TenantContext {
  return {
    permissions: [],
    correlationId: "test-corr-id",
    ...overrides,
  };
}

describe("workspace-strategy-settings", () => {
  it("returns defaults for missing row without creating a row in DB", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const settings = await getWorkspaceStrategySettings(ws.workspaceId);

    expect(settings.workspaceId).toBe(ws.workspaceId);
    expect(settings.strategyMethod).toBe("CLASSIC");
    expect(settings.bscMode).toBe("OFF");
    expect(settings.towsSelectionLimit).toBe(1);
    expect(settings.weeklyReviewEnabled).toBe(true);
    expect(settings.midCycleReviewPolicy).toBe("AUTO");
    expect(settings.endCycleReviewEnabled).toBe(true);
    expect(settings.approvalPolicy).toBe("FOUNDER_ONLY");
    expect(settings.enabledBscPerspectives).toEqual([]);
    expect(settings.allowedAgentProfiles).toEqual([]);
    expect(settings.revision).toBe(1);

    // Verify row was NOT created
    const rows = await db
      .select()
      .from(workspaceStrategySettings)
      .where(eq(workspaceStrategySettings.workspaceId, BigInt(ws.workspaceId)));
    expect(rows.length).toBe(0);
  });

  describe("BSC consistency matrix & validations", () => {
    it("rejects BSC_FILTER combined with bscMode OFF", () => {
      expect(() =>
        validateStrategySettings({
          strategyMethod: "BSC_FILTER",
          bscMode: "OFF",
        })
      ).toThrow(APIError);
    });

    it("rejects bscMode REQUIRED with empty perspectives", () => {
      expect(() =>
        validateStrategySettings({
          strategyMethod: "BSC_FILTER",
          bscMode: "REQUIRED",
          enabledBscPerspectives: [],
        })
      ).toThrow(APIError);
    });

    it("rejects duplicate or unknown perspectives", () => {
      expect(() =>
        validateStrategySettings({
          enabledBscPerspectives: ["FINANCIAL", "FINANCIAL"],
        })
      ).toThrow(APIError);

      expect(() =>
        validateStrategySettings({
          enabledBscPerspectives: ["UNKNOWN" as any],
        })
      ).toThrow(APIError);
    });

    it("rejects duplicate or unknown agent profiles", () => {
      expect(() =>
        validateStrategySettings({
          allowedAgentProfiles: ["strategy", "strategy"],
        })
      ).toThrow(APIError);

      expect(() =>
        validateStrategySettings({
          allowedAgentProfiles: ["ninja_hacker" as any],
        })
      ).toThrow(APIError);
    });

    it("rejects towsSelectionLimit outside [1, 2]", () => {
      expect(() =>
        validateStrategySettings({
          towsSelectionLimit: 0,
        })
      ).toThrow(APIError);

      expect(() =>
        validateStrategySettings({
          towsSelectionLimit: 3,
        })
      ).toThrow(APIError);

      expect(() =>
        validateStrategySettings({
          towsSelectionLimit: 1.5,
        })
      ).toThrow(APIError);
    });

    it("rejects project overrides that relax workspace policy", () => {
      const wsSettings: WorkspaceStrategySettings = {
        workspaceId: "123",
        strategyMethod: "BSC_FILTER",
        bscMode: "REQUIRED",
        enabledBscPerspectives: ["FINANCIAL", "CUSTOMER"],
        towsSelectionLimit: 1,
        weeklyReviewEnabled: true,
        midCycleReviewPolicy: "AUTO",
        endCycleReviewEnabled: true,
        allowedAgentProfiles: ["strategy"],
        approvalPolicy: "FOUNDER_ONLY",
        revision: 1,
      };

      // Attempt to relax bscMode to OPTIONAL or OFF
      expect(() =>
        validatePolicyOverride(wsSettings, { bscMode: "OPTIONAL" })
      ).toThrow("relax workspace BSC mode");

      expect(() =>
        validatePolicyOverride(wsSettings, { bscMode: "OFF" })
      ).toThrow("relax workspace BSC mode");

      // Attempt to relax strategyMethod to CLASSIC
      expect(() =>
        validatePolicyOverride(wsSettings, { strategyMethod: "CLASSIC" })
      ).toThrow("relax workspace strategyMethod");

      // Attempt to relax approvalPolicy to DELEGATED_APPROVER
      expect(() =>
        validatePolicyOverride(wsSettings, { approvalPolicy: "DELEGATED_APPROVER" })
      ).toThrow("relax workspace approvalPolicy");

      // Attempt to expand towsSelectionLimit
      expect(() =>
        validatePolicyOverride(wsSettings, { towsSelectionLimit: 2 })
      ).toThrow("cannot expand towsSelectionLimit");

      // Attempt to disable weekly reviews
      expect(() =>
        validatePolicyOverride(wsSettings, { weeklyReviewEnabled: false })
      ).toThrow("cannot disable weekly reviews");

      // Attempt to disable end-cycle reviews
      expect(() =>
        validatePolicyOverride(wsSettings, { endCycleReviewEnabled: false })
      ).toThrow("cannot disable end cycle reviews");

      // Attempt to turn off auto mid-cycle reviews
      expect(() =>
        validatePolicyOverride(wsSettings, { midCycleReviewPolicy: "OFF" })
      ).toThrow("cannot turn off mid-cycle reviews");

      // Attempt to enable a perspective not enabled in workspace
      expect(() =>
        validatePolicyOverride(wsSettings, {
          enabledBscPerspectives: ["LEARNING_AND_GROWTH"],
        })
      ).toThrow("not enabled in workspace settings");
    });
  });

  describe("update & revision conflict", () => {
    it("allows only one concurrent write for the same settings revision", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      await updateWorkspaceStrategySettings(ctx, {
        workspaceId: ws.workspaceId,
        strategyMethod: "BSC_FILTER",
        bscMode: "OPTIONAL",
        enabledBscPerspectives: ["FINANCIAL"],
        expectedRevision: 1,
      });

      const results = await Promise.allSettled([
        updateWorkspaceStrategySettings(ctx, {
          workspaceId: ws.workspaceId,
          towsSelectionLimit: 1,
          expectedRevision: 1,
        }),
        updateWorkspaceStrategySettings(ctx, {
          workspaceId: ws.workspaceId,
          towsSelectionLimit: 2,
          expectedRevision: 1,
        }),
      ]);

      expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
      expect(results.filter((result) => result.status === "rejected")).toHaveLength(1);
    });

    it("updates settings atomically and detects revision conflict", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        workforceMemberId: generateSnowflake().toString(),
        membershipRole: "founder",
        permissions: ["*"],
      });

      // Initial create via update
      const updated1 = await updateWorkspaceStrategySettings(ctx, {
        workspaceId: ws.workspaceId,
        strategyMethod: "BSC_FILTER",
        bscMode: "OPTIONAL",
        enabledBscPerspectives: ["FINANCIAL", "CUSTOMER"],
        towsSelectionLimit: 2,
        expectedRevision: 1,
      });

      expect(updated1.strategyMethod).toBe("BSC_FILTER");
      expect(updated1.bscMode).toBe("OPTIONAL");
      expect(updated1.towsSelectionLimit).toBe(2);
      expect(updated1.revision).toBe(1);

      // Second update incrementing revision
      const updated2 = await updateWorkspaceStrategySettings(ctx, {
        workspaceId: ws.workspaceId,
        bscMode: "REQUIRED",
        expectedRevision: 1,
      });
      expect(updated2.bscMode).toBe("REQUIRED");
      expect(updated2.revision).toBe(2);

      // Revision conflict with stale expectedRevision
      await expect(
        updateWorkspaceStrategySettings(ctx, {
          workspaceId: ws.workspaceId,
          towsSelectionLimit: 1,
          expectedRevision: 1, // Stale! Current is 2
        })
      ).rejects.toThrow("revision conflict");
    });
  });

  describe("governance authorization", () => {
    it("allows founder by default under FOUNDER_ONLY policy", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      const decision = await requireStrategyGovernanceAuthority(
        ctx,
        "strategy.framework.manage",
        { workspaceId: ws.workspaceId }
      );
      expect(decision.effect).toBe("ALLOW");

      const canEdit = await canExecuteStrategyGovernance(
        ctx,
        "strategy.framework.manage",
        { workspaceId: ws.workspaceId }
      );
      expect(canEdit).toBe(true);
    });

    it("rejects an otherwise delegated grantee under FOUNDER_ONLY policy", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "member" });
      const wsId = BigInt(ws.workspaceId);
      const workforceMemberId = generateSnowflake();

      await db.insert(identityWorkforceMembers).values({
        id: workforceMemberId,
        workspaceId: wsId,
        memberType: "HUMAN",
        humanUserId: BigInt(ws.userId),
        roleTitle: "Strategy Officer",
        status: "active",
      });

      const roleId = randomUUID();
      await db.insert(coreWorkspaceRoles).values({
        id: roleId,
        workspaceId: wsId,
        roleKey: "strategy_admin",
        name: "Strategy Admin",
        isSystem: false,
      });

      await db.insert(coreRolePermissions).values({
        roleId,
        permissionKey: "strategy.framework.manage",
        effect: "ALLOW",
        conditions: {},
      });

      await db.insert(coreMemberRoleAssignments).values({
        id: randomUUID(),
        workspaceId: wsId,
        workforceMemberId,
        roleId,
      });

      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        workforceMemberId: workforceMemberId.toString(),
        membershipRole: "member",
      });

      // Default policy is FOUNDER_ONLY -> member must be denied even with role assignment
      await expect(
        requireStrategyGovernanceAuthority(
          ctx,
          "strategy.framework.manage",
          { workspaceId: ws.workspaceId }
        )
      ).rejects.toThrow("founder approval required");

      const canEdit = await canExecuteStrategyGovernance(
        ctx,
        "strategy.framework.manage",
        { workspaceId: ws.workspaceId }
      );
      expect(canEdit).toBe(false);
    });

    it("allows delegated approver when workspace policy is DELEGATED_APPROVER", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "member" });
      const wsId = BigInt(ws.workspaceId);
      const workforceMemberId = generateSnowflake();

      await db.insert(identityWorkforceMembers).values({
        id: workforceMemberId,
        workspaceId: wsId,
        memberType: "HUMAN",
        humanUserId: BigInt(ws.userId),
        roleTitle: "Strategy Officer",
        status: "active",
      });

      const roleId = randomUUID();
      await db.insert(coreWorkspaceRoles).values({
        id: roleId,
        workspaceId: wsId,
        roleKey: "strategy_lead",
        name: "Strategy Lead",
        isSystem: false,
      });

      await db.insert(coreRolePermissions).values({
        roleId,
        permissionKey: "strategy.framework.manage",
        effect: "ALLOW",
        conditions: {},
      });

      await db.insert(coreMemberRoleAssignments).values({
        id: randomUUID(),
        workspaceId: wsId,
        workforceMemberId,
        roleId,
      });

      // Update workspace policy to DELEGATED_APPROVER
      const founderCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        approvalPolicy: "DELEGATED_APPROVER",
      });

      const memberCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        workforceMemberId: workforceMemberId.toString(),
        membershipRole: "member",
      });

      const decision = await requireStrategyGovernanceAuthority(
        memberCtx,
        "strategy.framework.manage",
        { workspaceId: ws.workspaceId }
      );
      expect(decision.effect).toBe("ALLOW");

      const canEdit = await canExecuteStrategyGovernance(
        memberCtx,
        "strategy.framework.manage",
        { workspaceId: ws.workspaceId }
      );
      expect(canEdit).toBe(true);
    });

    it("rejects workspace member without the grant under DELEGATED_APPROVER", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "member" });

      const founderCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        approvalPolicy: "DELEGATED_APPROVER",
      });

      const unprivilegedCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        workforceMemberId: generateSnowflake().toString(),
        membershipRole: "member",
      });

      await expect(
        requireStrategyGovernanceAuthority(
          unprivilegedCtx,
          "strategy.framework.manage",
          { workspaceId: ws.workspaceId }
        )
      ).rejects.toThrow(APIError);

      const canEdit = await canExecuteStrategyGovernance(
        unprivilegedCtx,
        "strategy.framework.manage",
        { workspaceId: ws.workspaceId }
      );
      expect(canEdit).toBe(false);
    });

    it("respects project-scoped role assignments under DELEGATED_APPROVER", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "member" });
      const wsId = BigInt(ws.workspaceId);
      const workforceMemberId = generateSnowflake();

      await db.insert(identityWorkforceMembers).values({
        id: workforceMemberId,
        workspaceId: wsId,
        memberType: "HUMAN",
        humanUserId: BigInt(ws.userId),
        roleTitle: "Project Strategy Lead",
        status: "active",
      });

      const roleId = randomUUID();
      await db.insert(coreWorkspaceRoles).values({
        id: roleId,
        workspaceId: wsId,
        roleKey: "project_strat_lead",
        name: "Project Strategy Lead",
        isSystem: false,
      });

      await db.insert(coreRolePermissions).values({
        roleId,
        permissionKey: "strategy.analysis.write",
        effect: "ALLOW",
        conditions: {},
      });

      const projectA = generateSnowflake();
      const projectB = generateSnowflake();

      // Scoped only to Project A
      await db.insert(coreMemberRoleAssignments).values({
        id: randomUUID(),
        workspaceId: wsId,
        workforceMemberId,
        roleId,
        projectId: projectA,
      });

      // Set DELEGATED_APPROVER
      const founderCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        approvalPolicy: "DELEGATED_APPROVER",
      });

      const memberCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        workforceMemberId: workforceMemberId.toString(),
        membershipRole: "member",
      });

      // Allowed for Project A
      const decisionA = await requireStrategyGovernanceAuthority(
        memberCtx,
        "strategy.analysis.write",
        { workspaceId: ws.workspaceId, projectId: projectA.toString() }
      );
      expect(decisionA.effect).toBe("ALLOW");

      // Denied for Project B
      await expect(
        requireStrategyGovernanceAuthority(
          memberCtx,
          "strategy.analysis.write",
          { workspaceId: ws.workspaceId, projectId: projectB.toString() }
        )
      ).rejects.toThrow(APIError);
    });
  });
});
