import { describe, it, expect } from "vitest";
import { sql, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  createOperatingRole,
  bindRoleAgent,
  deployRoleToProject,
  deployAgentToProject,
  bindWorkflowToProject,
  pauseProjectDeployment,
  getProjectDeploymentAuthority,
} from "../services/founder-asset-deployment.service";
import type { TenantContext } from "../../shared/types/tenant_context";

describe("Founder Asset Deployment Service", () => {
  it("allows only a HUMAN founder to deploy a role", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const role = await createOperatingRole(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "test-corr-1",
      },
      {
        roleCode: "product_ops",
        name: "Product Ops",
        reason: "Initial role setup",
        idempotencyKey: "role-1",
      }
    );

    const aiAgentContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-2",
      isAiAgent: true,
    };

    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-3",
      isAiAgent: false,
    };

    // AI agent context phải bị từ chối
    await expect(
      deployRoleToProject(aiAgentContext, {
        projectId: ws.projectId,
        roleId: role.id,
        expectedVersion: 1,
        reason: "Deploying role by AI",
        idempotencyKey: "deploy-ai-1",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // Human founder context phải thành công
    const deployed = await deployRoleToProject(founderContext, {
      projectId: ws.projectId,
      roleId: role.id,
      expectedVersion: 1,
      reason: "Deploying role by Founder",
      idempotencyKey: "deploy-founder-1",
    });

    expect(deployed.state).toBe("ACTIVE");
    expect(deployed.roleId).toBe(role.id);
  });

  it("does not append an event on stale expectedVersion", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-4",
      isAiAgent: false,
    };

    const role = await createOperatingRole(founderContext, {
      roleCode: "sales_director",
      name: "Sales Director",
      reason: "Creating sales role",
      idempotencyKey: "role-sales-1",
    });

    const deployment = await deployRoleToProject(founderContext, {
      projectId: ws.projectId,
      roleId: role.id,
      expectedVersion: 1,
      reason: "Initial deployment",
      idempotencyKey: "deploy-sales-1",
    });

    const initialEvents = await db
      .select()
      .from(schema.founderAssetEvents)
      .where(eq(schema.founderAssetEvents.workspaceId, BigInt(ws.workspaceId)));
    const countBefore = initialEvents.length;

    // Stale expectedVersion = 999 (version hiện tại là 1) -> phải throw aborted
    await expect(
      pauseProjectDeployment(founderContext, {
        deploymentId: deployment.id,
        kind: "ROLE",
        expectedVersion: 999,
        reason: "Stale update",
        idempotencyKey: "pause-stale-1",
      })
    ).rejects.toMatchObject({ code: "aborted" });

    const countAfter = (
      await db
        .select()
        .from(schema.founderAssetEvents)
        .where(eq(schema.founderAssetEvents.workspaceId, BigInt(ws.workspaceId)))
    ).length;

    expect(countAfter).toBe(countBefore);
  });
});
