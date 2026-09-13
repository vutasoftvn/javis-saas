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
import {
  handleAssetStatusCallback,
  requestAssetPublish,
} from "../services/founder-asset-authoring.service";
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

  it("rejects capability widening overrides and accepts only authority tightening", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const workforceMemberId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO core.workforce_members (
        id, workspace_id, member_type, role_title, agent_spec_id, agent_spec_version, status
      ) VALUES (
        ${workforceMemberId}, ${ws.workspaceId}, 'AI_AGENT', 'Support Agent', 'agent.support.1', '1.0.0', 'active'
      )
    `);

    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-tightening",
      isAiAgent: false,
    };

    const role = await createOperatingRole(founderContext, {
      roleCode: "customer_support",
      name: "Customer Support",
      reason: "Support operations",
    });

    const { createWorkspaceAgent, bindRoleAgent } = await import(
      "../services/founder-asset-deployment.service"
    );

    const agent = await createWorkspaceAgent(founderContext, {
      agentAssetId: "agent.support.1",
      agentAssetVersion: "1.0.0",
      agentDefinitionHash: "sha256:supporthash11111111111111111111111111111111111111111111111111111111",
      workforceMemberId: workforceMemberId.toString(),
      originKind: "CUSTOM",
      reason: "Support Agent",
    });

    await bindRoleAgent(founderContext, {
      roleId: role.id,
      workspaceAgentId: agent.id,
      reason: "Bind to support role",
    });

    const roleDep = await deployRoleToProject(founderContext, {
      projectId: ws.projectId,
      roleId: role.id,
      reason: "Deploy support role",
    });

    // 1. Widening attempt with ALLOW must be rejected
    await expect(
      deployAgentToProject(founderContext, {
        projectId: ws.projectId,
        workspaceAgentId: agent.id,
        projectRoleDeploymentId: roleDep.id,
        capabilityOverrides: [
          { capabilityId: "system.network.unrestricted", effect: "ALLOW" },
        ],
        reason: "Attempting to expand capability",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    // 2. Widening attempt with enabled: true must be rejected
    await expect(
      deployAgentToProject(founderContext, {
        projectId: ws.projectId,
        workspaceAgentId: agent.id,
        projectRoleDeploymentId: roleDep.id,
        capabilityOverrides: [
          { capabilityId: "system.db.admin", enabled: true },
        ],
        reason: "Attempting to enable capability",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    // 3. Tightening with DENY must succeed
    const deployed = await deployAgentToProject(founderContext, {
      projectId: ws.projectId,
      workspaceAgentId: agent.id,
      projectRoleDeploymentId: roleDep.id,
      capabilityOverrides: [
        { capabilityId: "system.shell.exec", effect: "DENY", reason: "Blocked in project" },
        { capabilityId: "billing.charge", enabled: false },
      ],
      reason: "Deploy with tightened security",
    });

    expect(deployed.state).toBe("ACTIVE");
    expect(deployed.capabilityOverrides).toHaveLength(2);

    // 4. getProjectDeploymentAuthority exposes capabilityRestrictions
    const authority = await getProjectDeploymentAuthority(founderContext, {
      projectId: ws.projectId,
      workspaceAgentId: agent.id,
    });

    expect(authority.capabilityRestrictions).toBeDefined();
    expect(authority.capabilityRestrictions).toHaveLength(2);
    expect(authority.capabilityRestrictions?.[0]).toMatchObject({
      capabilityId: "system.shell.exec",
      effect: "DENY",
    });
  });

  it("binds only an exact workflow version and hash with a successful publish receipt", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const founderContext: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-workflow-receipt",
      isAiAgent: false,
    };
    const workflowRef = {
      assetId: "workflow.sales.review",
      version: "0.1.0",
      definitionHash: "sha256:workflow-sales-review-0-1-0",
    };

    await expect(
      bindWorkflowToProject(founderContext, {
        projectId: ws.projectId,
        workflowAssetId: workflowRef.assetId,
        workflowAssetVersion: workflowRef.version,
        workflowDefinitionHash: workflowRef.definitionHash,
        reason: "Attempt to bind an arbitrary workflow",
        idempotencyKey: "bind-workflow-without-receipt",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    const publish = await requestAssetPublish(founderContext, {
      assetKind: "WORKFLOW",
      assetRef: workflowRef,
      idempotencyKey: "publish-workflow-sales-review",
      reason: "Publish reviewed sales workflow",
    });
    await handleAssetStatusCallback({
      commandId: publish.commandId,
      workspaceId: ws.workspaceId,
      assetKind: "WORKFLOW",
      operation: "PUBLISH",
      status: "SUCCESS",
      assetRef: workflowRef,
    });

    const binding = await bindWorkflowToProject(founderContext, {
      projectId: ws.projectId,
      workflowAssetId: workflowRef.assetId,
      workflowAssetVersion: workflowRef.version,
      workflowDefinitionHash: workflowRef.definitionHash,
      reason: "Bind the published sales workflow",
      idempotencyKey: "bind-published-workflow",
    });

    expect(binding.workflowAssetId).toBe(workflowRef.assetId);
    expect(binding.workflowAssetVersion).toBe(workflowRef.version);
    expect(binding.workflowDefinitionHash).toBe(workflowRef.definitionHash);
  });
});
