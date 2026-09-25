import { describe, it, expect } from "vitest";
import { sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { mintTestWorkerToken } from "../../shared/auth/worker-service-auth";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  getProjectDeploymentAuthorityApi,
  getProjectDeploymentAuthorityByDeploymentApi,
} from "../handlers/founder-asset-deployment.handler";
import {
  createOperatingRole,
  createWorkspaceAgent,
  bindRoleAgent,
  deployRoleToProject,
  deployAgentToProject,
} from "../services/founder-asset-deployment.service";

describe("Founder Asset Deployment Handler", () => {
  it("rejects dev-worker-service-token in production configuration", async () => {
    const originalEnv = process.env.ENVIRONMENT;
    process.env.ENVIRONMENT = "production";
    try {
      await expect(
        getProjectDeploymentAuthorityApi({
          workspaceId: "123",
          projectId: "456",
          workspaceAgentId: "789",
          serviceToken: "dev-worker-service-token",
        })
      ).rejects.toMatchObject({ code: expect.stringMatching(/unauthenticated|internal/) });
    } finally {
      if (originalEnv === undefined) { delete process.env.ENVIRONMENT; } else { process.env.ENVIRONMENT = originalEnv; }
    }
  });

  it("rejects cross-workspace deployment authority query", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createSecondWorkspace();

    const token = mintTestWorkerToken("worker-a");
    await expect(
      getProjectDeploymentAuthorityApi({
        serviceToken: token,
        workspaceId: wsB.workspaceId,
        projectId: wsA.projectId,
        workspaceAgentId: "999",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects unauthenticated worker service token", async () => {
    await expect(
      getProjectDeploymentAuthorityApi({
        workspaceId: "123",
        projectId: "456",
        workspaceAgentId: "789",
        serviceToken: "invalid-token",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("returns project deployment authority for valid service token", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    // Tạo workforce member
    const workforceMemberId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO core.workforce_members (
        id, workspace_id, member_type, role_title, agent_spec_id, agent_spec_version, status
      ) VALUES (
        ${workforceMemberId}, ${ws.workspaceId}, 'AI_AGENT', 'Lead Engineer Agent', 'agent.lead.eng', '1.0.0', 'active'
      )
    `);

    const ctx = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-handler-test",
    };

    const role = await createOperatingRole(ctx, {
      roleCode: "tech_lead",
      name: "Tech Lead",
      reason: "Engineering role",
    });

    const agent = await createWorkspaceAgent(ctx, {
      agentAssetId: "agent.lead.eng",
      agentAssetVersion: "1.0.0",
      agentDefinitionHash: "sha256:techleadhash1111111111111111111111111111111111111111111111111111",
      workforceMemberId: workforceMemberId.toString(),
      originKind: "CUSTOM",
      reason: "Custom tech lead agent",
    });

    await bindRoleAgent(ctx, {
      roleId: role.id,
      workspaceAgentId: agent.id,
      reason: "Binding tech lead agent",
    });

    const roleDep = await deployRoleToProject(ctx, {
      projectId: ws.projectId,
      roleId: role.id,
      reason: "Deploying tech lead role to project",
    });

    const agentDeployment = await deployAgentToProject(ctx, {
      projectId: ws.projectId,
      workspaceAgentId: agent.id,
      projectRoleDeploymentId: roleDep.id,
      reason: "Deploying tech lead agent to project",
    });

    const authority = await getProjectDeploymentAuthorityApi({
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      workspaceAgentId: agent.id,
      serviceToken: mintTestWorkerToken("worker-1"),
    });

    expect(authority).toMatchObject({
      workspaceAgentId: agent.id,
      workforceMemberId: workforceMemberId.toString(),
      agentSpec: {
        id: "agent.lead.eng",
        version: "1.0.0",
        definitionHash: "sha256:techleadhash1111111111111111111111111111111111111111111111111111",
      },
      roleIds: [role.id],
      projectId: ws.projectId,
      state: "ACTIVE",
    });

    const exactAuthority = await getProjectDeploymentAuthorityByDeploymentApi({
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      projectAgentDeploymentId: agentDeployment.id,
      serviceToken: mintTestWorkerToken("worker-1"),
    });
    expect(exactAuthority).toMatchObject({
      projectAgentDeploymentId: agentDeployment.id,
      workspaceAgentId: agent.id,
      projectId: ws.projectId,
    });
  });

  it("rejects createWorkspaceAgent when workforceMemberId belongs to another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createSecondWorkspace();

    const workforceMemberIdB = generateSnowflake();
    await db.execute(sql`
      INSERT INTO core.workforce_members (
        id, workspace_id, member_type, role_title, agent_spec_id, agent_spec_version, status
      ) VALUES (
        ${workforceMemberIdB}, ${wsB.workspaceId}, 'AI_AGENT', 'Foreign Member', 'foreign.spec', '1.0.0', 'active'
      )
    `);

    const ctxA = {
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-cross-tenant-test",
    };

    await expect(
      createWorkspaceAgent(ctxA, {
        agentAssetId: "agent.foreign.1",
        agentAssetVersion: "1.0.0",
        agentDefinitionHash: "sha256:foreignhash1111111111111111111111111111111111111111111111111111",
        workforceMemberId: workforceMemberIdB.toString(),
        originKind: "CUSTOM",
        reason: "Cross tenant workforce member should fail",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
