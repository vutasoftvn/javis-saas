import { describe, it, expect } from "vitest";
import { sql, eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("Founder Asset Schema Invariants", () => {
  it("rejects a deployment whose project belongs to another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const roleId = generateSnowflake();
    // Tạo role thuộc workspace A
    await db.insert(schema.workspaceOperatingRoles).values({
      id: roleId,
      workspaceId: BigInt(wsA.workspaceId),
      roleCode: "lead_architect",
      name: "Lead Architect",
      createdBy: BigInt(wsA.userId),
    });

    const deploymentId = generateSnowflake();

    // Thử deploy role của wsA vào project của wsB -> phải reject do FK (project_id, workspace_id)
    await expect(
      db.insert(schema.projectRoleDeployments).values({
        id: deploymentId,
        workspaceId: BigInt(wsA.workspaceId),
        projectId: BigInt(wsB.projectId),
        roleId,
        createdBy: BigInt(wsA.userId),
      })
    ).rejects.toThrow();
  });

  it("keeps one workspace agent deployment per project and agent", async () => {
    const ws = await createTestWorkspaceWithMember();

    // Tạo workforce member kiểu AI_AGENT
    const workforceMemberId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO core.workforce_members (
        id, workspace_id, member_type, role_title, agent_spec_id, agent_spec_version, status
      ) VALUES (
        ${workforceMemberId}, ${ws.workspaceId}, 'AI_AGENT', 'Custom AI Agent', 'custom.agent.spec', '1.0.0', 'active'
      )
    `);

    // Tạo workspace agent
    const workspaceAgentId = generateSnowflake();
    await db.insert(schema.workspaceAgents).values({
      id: workspaceAgentId,
      workspaceId: BigInt(ws.workspaceId),
      agentAssetId: "agent.custom.1",
      agentAssetVersion: "1.0.0",
      agentDefinitionHash: "sha256:1111111111111111111111111111111111111111111111111111111111111111",
      workforceMemberId,
      state: "ACTIVE",
      originKind: "CLONE",
      createdBy: BigInt(ws.userId),
    });

    // Deploy lần đầu
    const depId1 = generateSnowflake();
    await db.insert(schema.projectAgentDeployments).values({
      id: depId1,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(ws.projectId),
      workspaceAgentId,
      state: "ACTIVE",
      createdBy: BigInt(ws.userId),
    });

    // Deploy lần thứ 2 cùng agent vào cùng project -> phải văng lỗi Unique constraint
    const depId2 = generateSnowflake();
    let errorThrown: any = null;
    try {
      await db.insert(schema.projectAgentDeployments).values({
        id: depId2,
        workspaceId: BigInt(ws.workspaceId),
        projectId: BigInt(ws.projectId),
        workspaceAgentId,
        state: "ACTIVE",
        createdBy: BigInt(ws.userId),
      });
    } catch (err: any) {
      errorThrown = err;
    }

    expect(errorThrown).not.toBeNull();
    const errorString = `${errorThrown?.message || ""} ${errorThrown?.cause?.message || ""} ${errorThrown?.detail || ""}`;
    expect(errorString).toMatch(/unique|duplicate/i);
  });

  it("rejects workspace agent creation with workforce member from another workspace via composite FK", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const workforceMemberIdB = generateSnowflake();
    await db.execute(sql`
      INSERT INTO core.workforce_members (
        id, workspace_id, member_type, role_title, agent_spec_id, agent_spec_version, status
      ) VALUES (
        ${workforceMemberIdB}, ${wsB.workspaceId}, 'AI_AGENT', 'Foreign Member', 'foreign.spec', '1.0.0', 'active'
      )
    `);

    const workspaceAgentId = generateSnowflake();
    await expect(
      db.insert(schema.workspaceAgents).values({
        id: workspaceAgentId,
        workspaceId: BigInt(wsA.workspaceId),
        agentAssetId: "agent.foreign.direct",
        agentAssetVersion: "1.0.0",
        agentDefinitionHash: "sha256:foreignhash1111111111111111111111111111111111111111111111111111",
        workforceMemberId: workforceMemberIdB,
        state: "ACTIVE",
        originKind: "CUSTOM",
        createdBy: BigInt(wsA.userId),
      })
    ).rejects.toThrow();
  });
});
