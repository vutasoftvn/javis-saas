import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  createTestWorkspaceWithMember,
  deployWorkspaceAgentForProfile,
  makeTestTenantContext,
} from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import { resolveChatRunAuthority } from "../services/founder-agent-compatibility.service";
import { activateProjectStartupTeamMember } from "../services/project-startup-team.service";
import {
  deployAgentToProject,
  pauseProjectDeployment,
} from "../services/founder-asset-deployment.service";
import { AGENT_PROFILE_SPEC_HASH, AGENT_PROFILE_SPEC_ID } from "../services/ai-member.service";

const { workspaceAgents } = schema;

/**
 * Chat run và Executive Board phải cùng tôn trọng V2 `project_agent_deployments`:
 * Founder pause deployment thì chat cũng dừng, ENFORCED chỉ nhận V2.
 */
describe("resolveChatRunAuthority", () => {
  const origMode = process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE;
  let ctx: TenantContext;
  let projectId: string;

  beforeEach(async () => {
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "SHADOW";
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    projectId = ws.projectId;
    ctx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });
  });

  afterEach(() => {
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = origMode;
  });

  async function activateLegacy(profileKey: string) {
    await activateProjectStartupTeamMember(ctx, projectId, profileKey, { expectedVersion: 1 });
  }

  /** Deploy đúng Workspace Agent mà activation legacy đã tạo (không tạo agent thứ hai). */
  async function deployLegacyAgent(profileKey: "finance" | "marketing") {
    const [agent] = await db
      .select({ id: workspaceAgents.id })
      .from(workspaceAgents)
      .where(
        and(
          eq(workspaceAgents.workspaceId, BigInt(ctx.workspaceId)),
          eq(workspaceAgents.agentAssetId, AGENT_PROFILE_SPEC_ID[profileKey])
        )
      )
      .limit(1);
    return deployAgentToProject(ctx, {
      projectId,
      workspaceAgentId: agent.id.toString(),
      reason: "test",
      idempotencyKey: `chat-auth-${profileKey}`,
    });
  }

  it("SHADOW: legacy only keeps the legacy authority", async () => {
    await activateLegacy("finance");

    const auth = await resolveChatRunAuthority(ctx.workspaceId, projectId, "finance");

    expect(auth.profileKey).toBe("finance");
    expect(auth.spec.hash).toBe(AGENT_PROFILE_SPEC_HASH.finance);
  });

  it("SHADOW: a PAUSED V2 deployment blocks chat even with an active legacy assignment", async () => {
    await activateLegacy("finance");
    const dep = await deployLegacyAgent("finance");
    await pauseProjectDeployment(ctx, {
      deploymentId: dep.id,
      kind: "AGENT",
      expectedVersion: dep.version,
      reason: "Founder pause",
    });

    await expect(resolveChatRunAuthority(ctx.workspaceId, projectId, "finance")).rejects.toThrow(
      /PAUSED/
    );
  });

  it("SHADOW: an ACTIVE V2 deployment without legacy assignment is enough", async () => {
    await deployWorkspaceAgentForProfile(ctx, projectId, "finance");

    const auth = await resolveChatRunAuthority(ctx.workspaceId, projectId, "finance");

    expect(auth.spec.id).toBe(AGENT_PROFILE_SPEC_ID.finance);
    expect(auth.spec.hash).toBe(AGENT_PROFILE_SPEC_HASH.finance);
    expect(auth.agentWorkforceMemberId).not.toBe("0");
  });

  it("ENFORCED: legacy assignment alone is rejected; V2 ACTIVE is accepted", async () => {
    await activateLegacy("finance");
    process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = "ENFORCED";

    await expect(resolveChatRunAuthority(ctx.workspaceId, projectId, "finance")).rejects.toThrow(
      /not actively deployed/
    );

    await deployLegacyAgent("finance");
    const auth = await resolveChatRunAuthority(ctx.workspaceId, projectId, "finance");
    expect(auth.spec.hash).toBe(AGENT_PROFILE_SPEC_HASH.finance);
  });

  it.each(["SHADOW", "ENFORCED", "LEGACY"])(
    "%s: no legacy and no V2 is notFound, never a compat authority",
    async (mode) => {
      process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE = mode;
      await expect(
        resolveChatRunAuthority(ctx.workspaceId, projectId, "marketing")
      ).rejects.toThrow();
    }
  );

  it("rejects unknown and non-runnable profiles", async () => {
    await expect(resolveChatRunAuthority(ctx.workspaceId, projectId, "nope")).rejects.toThrow(
      /Unknown profile key/
    );
    await expect(
      resolveChatRunAuthority(ctx.workspaceId, projectId, "founder_assistant")
    ).rejects.toThrow(/founder_assistant/);
  });
});
