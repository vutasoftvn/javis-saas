import { describe, it, expect, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../models/db";
import { createTestWorkspaceWithMember, makeTestTenantContext } from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  activateProjectStartupTeamMember,
  pauseProjectStartupTeamMember,
} from "../services/project-startup-team.service";
import { AGENT_PROFILE_GRANTED_CAPABILITIES } from "../services/agent-profile-grants.service";
import { issueAgentAuthorizationTicket } from "../../identity/services/agent-authorization-ticket.service";
import {
  coreAgentCapabilityGrants,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";

// ADR-CHAT-ACTIONS-001: founder kích hoạt profile trong startup team = cấp cho AI member các
// capability ghi của profile (scope Project); tạm dừng = thu hồi. Nhờ vậy live authorization
// ticket cấp được cho hành động founder đã duyệt trong chat.
describe("startup team activation grants agent capabilities", () => {
  let ctx: TenantContext;
  let projectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    projectId = ws.projectId;
    // Grant ghi người cấp là workforce member HUMAN của founder (FK granted_by_founder_member_id).
    const founderMemberId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: founderMemberId,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });
    ctx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: founderMemberId.toString(),
      membershipRole: "founder",
      isAiAgent: false,
    });
  });

  async function operationsAgentId(): Promise<string> {
    const [agent] = await db
      .select({ id: identityWorkforceMembers.id })
      .from(identityWorkforceMembers)
      .where(
        and(
          eq(identityWorkforceMembers.workspaceId, BigInt(ctx.workspaceId)),
          eq(identityWorkforceMembers.memberType, "AI_AGENT"),
          eq(identityWorkforceMembers.agentSpecId, "cosa.agents.operations")
        )
      )
      .limit(1);
    return agent.id.toString();
  }

  async function activeGrants(agentId: string): Promise<string[]> {
    const rows = await db
      .select({ capabilityId: coreAgentCapabilityGrants.capabilityId })
      .from(coreAgentCapabilityGrants)
      .where(
        and(
          eq(coreAgentCapabilityGrants.agentWorkforceMemberId, BigInt(agentId)),
          eq(coreAgentCapabilityGrants.projectId, BigInt(projectId)),
          eq(coreAgentCapabilityGrants.status, "ACTIVE")
        )
      );
    return rows.map((r) => r.capabilityId).sort();
  }

  it("activation grants the profile write capabilities and a ticket can be issued", async () => {
    await activateProjectStartupTeamMember(ctx, projectId, "operations", { expectedVersion: 1 });
    const agentId = await operationsAgentId();

    expect(await activeGrants(agentId)).toEqual(
      [...AGENT_PROFILE_GRANTED_CAPABILITIES.operations].sort()
    );

    const ticket = await issueAgentAuthorizationTicket({
      workspaceId: ctx.workspaceId,
      runId: "run-chat-1",
      toolCallId: "call-1",
      checkpointRef: "ckpt-1",
      capabilityId: "okr.key_result.create",
      agentWorkforceMemberId: agentId,
    });
    expect(ticket.ticketId).toMatch(/^tkt_/);
  });

  it("finance.transaction.record is never auto-granted", async () => {
    await activateProjectStartupTeamMember(ctx, projectId, "finance", { expectedVersion: 1 });
    const rows = await db
      .select({ capabilityId: coreAgentCapabilityGrants.capabilityId })
      .from(coreAgentCapabilityGrants)
      .where(eq(coreAgentCapabilityGrants.workspaceId, BigInt(ctx.workspaceId)));
    expect(rows.map((r) => r.capabilityId)).not.toContain("finance.transaction.record");
  });

  it("pausing the agent revokes the grants so tickets are denied", async () => {
    await activateProjectStartupTeamMember(ctx, projectId, "operations", { expectedVersion: 1 });
    const agentId = await operationsAgentId();
    await pauseProjectStartupTeamMember(ctx, projectId, "operations", { expectedVersion: 2 });

    expect(await activeGrants(agentId)).toEqual([]);
    await expect(
      issueAgentAuthorizationTicket({
        workspaceId: ctx.workspaceId,
        runId: "run-chat-2",
        toolCallId: "call-2",
        checkpointRef: "ckpt-2",
        capabilityId: "okr.key_result.create",
        agentWorkforceMemberId: agentId,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
