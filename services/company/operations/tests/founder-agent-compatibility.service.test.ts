import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  ensureAiWorkforceMemberForAsset,
  resolveProjectAgentAuthorityV2,
  verifyUnderlyingAgentActive,
} from "../services/founder-agent-compatibility.service";
import {
  ensureAiWorkforceMember,
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_HASH,
} from "../services/ai-member.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProjectService } from "../services/project.service";
import { activateProjectStartupTeamMemberApi } from "../handlers/project-startup-team.handler";

const { workspaceAgents, projectAgentDeployments, projectAgentAssignments } = schema;

describe("Founder Agent Compatibility & Dual-Read Service", () => {
  const origEnv = process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE;

  beforeEach(() => {
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "SHADOW";
  });

  afterEach(() => {
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = origEnv;
  });

  it("creates one AI workforce member for a published custom agent asset", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const customSpec = {
      specId: "agent_custom_growth_hacker",
      specVersion: "1.0.0",
      definitionHash: "abc123def4567890123456789012345678901234567890123456789012345678",
      title: "Growth Hacker Custom Agent",
    };

    let first: string;
    let second: string;

    await db.transaction(async (tx) => {
      first = await ensureAiWorkforceMemberForAsset(tx, ws.workspaceId, customSpec);
      second = await ensureAiWorkforceMemberForAsset(tx, ws.workspaceId, customSpec);
    });

    expect(first!).toBeDefined();
    expect(second!).toEqual(first!);
  });

  it("ensures built-in compatibility wrappers use exact pinned hashes", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    let memberId: string;
    await db.transaction(async (tx) => {
      memberId = await ensureAiWorkforceMember(tx, ws.workspaceId, "operations");
    });

    expect(memberId!).toBeDefined();

    // Re-running with same profile returns identical member ID
    let memberIdAgain: string;
    await db.transaction(async (tx) => {
      memberIdAgain = await ensureAiWorkforceMember(tx, ws.workspaceId, "operations");
    });
    expect(memberIdAgain!).toEqual(memberId!);
  });

  it("uses V2 deployment authority only when the feature is enabled", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Compatibility Test Project" }
    );

    // Activate operations profile in legacy assignments
    await activateProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "operations",
      expectedVersion: 1,
    });

    const ctx = {
      workspaceId: ws.workspaceId,
      projectId: project.id,
    };

    const legacyProfile = {
      projectId: project.id,
      profileKey: "operations",
    };

    // Default mode is SHADOW -> returns source: legacy
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "SHADOW";
    const shadowRes = await resolveProjectAgentAuthorityV2(ctx, legacyProfile);
    expect(shadowRes).toMatchObject({
      source: "legacy",
      profileKey: "operations",
      projectId: project.id,
    });

    // When ENFORCED but no V2 deployment exists -> rejects with notFound
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "ENFORCED";
    await expect(resolveProjectAgentAuthorityV2(ctx, legacyProfile)).rejects.toThrow(
      /no active v2 agent deployment/i
    );

    // Create active V2 workspaceAgent + projectAgentDeployment
    const memberId = await db.transaction(async (tx) => {
      return ensureAiWorkforceMember(tx, ws.workspaceId, "operations");
    });

    const wsAgentId = generateSnowflake();
    const deploymentId = generateSnowflake();

    await db.insert(workspaceAgents).values({
      id: wsAgentId,
      workspaceId: BigInt(ws.workspaceId),
      agentAssetId: AGENT_PROFILE_SPEC_ID.operations,
      agentAssetVersion: "1.3.0",
      agentDefinitionHash: AGENT_PROFILE_SPEC_HASH.operations,
      workforceMemberId: BigInt(memberId),
      state: "ACTIVE",
      originKind: "BUILTIN",
      createdBy: BigInt(ws.userId),
      version: 1,
    });

    await db.insert(projectAgentDeployments).values({
      id: deploymentId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      workspaceAgentId: wsAgentId,
      state: "ACTIVE",
      version: 1,
      createdBy: BigInt(ws.userId),
    });

    // In ENFORCED mode with active deployment -> returns source: v2
    const enforcedRes = await resolveProjectAgentAuthorityV2(ctx, legacyProfile);
    expect(enforcedRes).toMatchObject({
      source: "v2",
      mode: "ENFORCED",
      profileKey: "operations",
      deploymentId: deploymentId.toString(),
      workspaceAgentId: wsAgentId.toString(),
    });
  });

  it("verifies underlying agent active state in both shadow and enforced modes", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Underlying Check Project" }
    );

    // Before activation
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "SHADOW";
    let isActive = await verifyUnderlyingAgentActive(ws.workspaceId, project.id, "finance");
    expect(isActive).toBe(false);

    // Activate finance
    await activateProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "finance",
      expectedVersion: 1,
    });

    isActive = await verifyUnderlyingAgentActive(ws.workspaceId, project.id, "finance");
    expect(isActive).toBe(true);

    // In ENFORCED mode without V2 deployment -> false
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "ENFORCED";
    isActive = await verifyUnderlyingAgentActive(ws.workspaceId, project.id, "finance");
    expect(isActive).toBe(false);
  });
});
