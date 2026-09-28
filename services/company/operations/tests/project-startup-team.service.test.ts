import { describe, it, expect } from "vitest";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember, createSecondWorkspace, makeTestTenantContext } from "./_helpers";
import {
  listProjectStartupTeam,
  ensureProjectStartupTeam,
} from "../services/project-startup-team.service";
import {
  commandFounderAsset,
  handleAssetStatusCallback,
  type AgentPublishManifest,
} from "../services/founder-asset-authoring.service";
import {
  createWorkspaceAgent,
  deployAgentToProject,
  pauseProjectDeployment,
  WORKSPACE_CLONE_ORIGIN,
} from "../services/founder-asset-deployment.service";
import {
  AGENT_PROFILE_SPEC_HASH,
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_VERSION,
} from "../services/ai-member.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";
import { db, schema } from "../models/db";
import { eq, and } from "drizzle-orm";
import {
  STARTUP_TEAM_PROFILES,
  STARTUP_TEAM_PROFILE_KEYS,
} from "../../shared/contracts/startup-team-profiles.generated";

describe("Project Startup Team Service", () => {
  it("newly created project has exactly the catalog profiles", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Alpha Startup",
      description: "Testing startup team creation",
    });

    const team = await listProjectStartupTeam({
      workspaceId: ws.workspaceId,
      projectId: project.id,
      actorId: ws.userId,
    });

    expect(team.length).toBe(STARTUP_TEAM_PROFILES.length);
    expect(team.map((m) => m.profileKey)).toEqual(STARTUP_TEAM_PROFILE_KEYS);

    const founder = team.find((m) => m.profileKey === "founder_assistant");
    expect(founder).toMatchObject({
      displayState: "CHAT_READY",
      runtimeReadiness: "READY",
    });

    const operations = team.find((m) => m.profileKey === "operations");
    expect(operations).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "READY",
      assignmentVersion: 1,
    });

    const coding = team.find((m) => m.profileKey === "coding");
    expect(coding).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "READY",
    });

    const marketing = team.find((m) => m.profileKey === "marketing");
    expect(marketing).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "READY",
    });

    const crm = team.find((m) => m.profileKey === "crm");
    expect(crm).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "PENDING_CRM_FOUNDATION",
      disabledReason: "PENDING_CRM_FOUNDATION",
    });
  });

  it("re-running ensureProjectStartupTeam is idempotent and does not duplicate rows", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Idempotent Project",
    });

    // Re-run ensureProjectStartupTeam
    await db.transaction(async (tx) => {
      await ensureProjectStartupTeam(tx, {
        workspaceId: ws.workspaceId,
        projectId: project.id,
        actorId: ws.userId,
      });
    });

    const rows = await db
      .select()
      .from(schema.projectAgentAssignments)
      .where(
        and(
          eq(schema.projectAgentAssignments.workspaceId, BigInt(ws.workspaceId)),
          eq(schema.projectAgentAssignments.projectId, BigInt(project.id))
        )
      );

    // 9 profiles
    expect(rows.length).toBe(STARTUP_TEAM_PROFILES.length);

    const team = await listProjectStartupTeam({
      workspaceId: ws.workspaceId,
      projectId: project.id,
      actorId: ws.userId,
    });
    expect(team.length).toBe(STARTUP_TEAM_PROFILES.length);
  });

  it("rejects project from another workspace with notFound", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Workspace A Project",
    });

    await expect(
      listProjectStartupTeam({
        workspaceId: wsB.workspaceId,
        projectId: projectA.id,
        actorId: wsB.workspaceId,
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  describe("UNION agent tự tạo (C2 — task-9-brief.md)", () => {
    /** CLONE -> EDIT_DRAFT -> EVALUATE -> PUBLISH tối giản cho AGENT (giống founder-agent-clone
     * .service.test.ts) — chỉ để có 1 biên nhận PUBLISH thật, dùng cho `createWorkspaceAgent`. */
    async function publishOperationsClone(
      ctx: TenantContext,
      projectId: string,
      workspaceId: string,
      displayName: string
    ) {
      const clone = await commandFounderAsset(ctx, {
        projectId,
        assetKind: "AGENT",
        operation: "CLONE",
        assetRef: { assetId: AGENT_PROFILE_SPEC_ID.operations },
        idempotencyKey: `union-clone-${generateSnowflake()}`,
        reason: "Founder tạo agent vận hành riêng",
        metadata: { name: displayName },
      });
      const draftRef = {
        assetId: `custom.operations.${clone.commandId}`,
        version: "0.1.0",
        definitionHash: "sha256:draft",
      };
      await handleAssetStatusCallback({
        commandId: clone.commandId,
        workspaceId,
        projectId,
        assetKind: "AGENT",
        operation: "CLONE",
        status: "SUCCESS",
        assetRef: draftRef,
      });

      const publish = await commandFounderAsset(ctx, {
        projectId,
        assetKind: "AGENT",
        operation: "PUBLISH",
        assetRef: draftRef,
        idempotencyKey: `union-publish-${generateSnowflake()}`,
        reason: "Publish agent vận hành riêng",
      });
      const manifest: AgentPublishManifest = {
        originProfileKey: "operations",
        originSpec: {
          id: AGENT_PROFILE_SPEC_ID.operations,
          version: AGENT_PROFILE_SPEC_VERSION.operations,
          definitionHash: AGENT_PROFILE_SPEC_HASH.operations,
        },
        capabilityRefs: [],
        displayName,
      };
      await handleAssetStatusCallback({
        commandId: publish.commandId,
        workspaceId,
        projectId,
        assetKind: "AGENT",
        operation: "PUBLISH",
        status: "SUCCESS",
        assetRef: draftRef,
        agentManifest: manifest,
      });
      return draftRef;
    }

    it("built-in + agent custom (WORKSPACE_CLONE) cùng hiện trong 1 danh sách, đúng project", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderMemberId = generateSnowflake();
      await db.insert(identityWorkforceMembers).values({
        id: founderMemberId,
        workspaceId: BigInt(ws.workspaceId),
        memberType: "HUMAN",
        humanUserId: BigInt(ws.userId),
        roleTitle: "Founder",
        status: "active",
      });
      const ctx = makeTestTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        workforceMemberId: founderMemberId.toString(),
        membershipRole: "founder",
      });

      const ref = await publishOperationsClone(
        ctx,
        ws.projectId,
        ws.workspaceId,
        "Vận hành Sao Mai"
      );
      const agent = await createWorkspaceAgent(ctx, {
        agentAssetId: ref.assetId,
        agentAssetVersion: ref.version,
        agentDefinitionHash: ref.definitionHash,
        originKind: WORKSPACE_CLONE_ORIGIN,
        reason: "Tạo agent workspace từ clone đã publish",
      });
      await deployAgentToProject(ctx, {
        projectId: ws.projectId,
        workspaceAgentId: agent.id,
        reason: "Deploy agent riêng vào Project",
      });

      const team = await listProjectStartupTeam({
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        actorId: ws.userId,
      });

      // Vẫn còn đủ built-in catalog, không bị custom agent đè/mất.
      expect(team.filter((m) => (STARTUP_TEAM_PROFILE_KEYS as readonly string[]).includes(m.profileKey)).length).toBe(
        STARTUP_TEAM_PROFILES.length
      );

      const custom = team.find((m) => m.profileKey === ref.assetId);
      expect(custom).toMatchObject({
        label: "Vận hành Sao Mai",
        displayState: "ACTIVE",
        runtimeReadiness: "READY",
      });
      expect(custom?.assignmentVersion).toBe(1);

      // Không lẫn sang Project khác cùng Workspace: tạo Project thứ 2, chưa deploy gì.
      const project2 = await createProject({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        title: "Second Project",
      });
      const team2 = await listProjectStartupTeam({
        workspaceId: ws.workspaceId,
        projectId: project2.id,
        actorId: ws.userId,
      });
      expect(team2.find((m) => m.profileKey === ref.assetId)).toBeUndefined();

      // Pause deployment -> UNION phản ánh displayState PAUSED (không phải "template" cố định).
      const deployments = await db
        .select()
        .from(schema.projectAgentDeployments)
        .where(
          and(
            eq(schema.projectAgentDeployments.workspaceId, BigInt(ws.workspaceId)),
            eq(schema.projectAgentDeployments.projectId, BigInt(ws.projectId))
          )
        );
      await pauseProjectDeployment(ctx, {
        deploymentId: deployments[0].id.toString(),
        kind: "AGENT",
        expectedVersion: deployments[0].version,
        reason: "Tạm dừng để test UNION",
      });
      const teamAfterPause = await listProjectStartupTeam({
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        actorId: ws.userId,
      });
      expect(teamAfterPause.find((m) => m.profileKey === ref.assetId)).toMatchObject({
        displayState: "PAUSED",
      });
    });
  });
});
