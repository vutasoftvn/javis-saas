import { describe, expect, it } from "vitest";
import { db, schema } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import {
  getOrganizationOverviewApi,
  listOrganizationWorkforceApi,
} from "../handlers/organization-overview.handler";
import { createAiWorkforceApi } from "../handlers/ai-workforce.handler";

// Spec 2026-09-25 §7 — Organization API hẹp, kiểm quyền server-side.

async function seedWorkspaceAgent(
  workspaceId: string,
  createdBy: string,
  state: "ACTIVE" | "RETIRED" = "ACTIVE"
): Promise<{ workspaceAgentId: string; workforceMemberId: string }> {
  const memberId = generateSnowflake();
  const agentId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: memberId,
    workspaceId: BigInt(workspaceId),
    memberType: "AI_AGENT",
    agentSpecId: `agent-${agentId}`,
    agentSpecVersion: "1.0.0",
    roleTitle: "Unassigned agent",
  });
  await db.insert(schema.workspaceAgents).values({
    id: agentId,
    workspaceId: BigInt(workspaceId),
    agentAssetId: `agent-${agentId}`,
    agentAssetVersion: "1.0.0",
    agentDefinitionHash: "sha256:" + "a".repeat(64),
    workforceMemberId: memberId,
    state,
    originKind: "CLONE",
    createdBy: BigInt(createdBy),
  });
  return { workspaceAgentId: agentId.toString(), workforceMemberId: memberId.toString() };
}

describe("Organization overview/workforce API", () => {
  it("lets a member read the overview but not manage workforce", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const overview = await getOrganizationOverviewApi({
      organizationId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    expect(overview).toMatchObject({
      organizationId: ws.workspaceId,
      viewerRole: "member",
      canManageWorkforce: false,
    });

    const { workspaceAgentId } = await seedWorkspaceAgent(ws.workspaceId, ws.userId);
    await expect(
      createAiWorkforceApi({
        organizationId: ws.workspaceId,
        authorization: ws.bearerToken,
        roleTitle: "Ops Agent",
        workspaceAgentId,
        idempotencyKey: "k-member",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects a header/path organization mismatch and outsiders", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const other = await createSecondWorkspace();
    await expect(
      getOrganizationOverviewApi({
        organizationId: ws.workspaceId,
        workspaceId: other.workspaceId,
        authorization: ws.bearerToken,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
    await expect(
      listOrganizationWorkforceApi({
        organizationId: other.workspaceId,
        authorization: ws.bearerToken,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
    await expect(
      getOrganizationOverviewApi({ organizationId: ws.workspaceId })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("lets a founder place a deployable workspace agent and returns a durable member id", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const { workspaceAgentId, workforceMemberId } = await seedWorkspaceAgent(
      ws.workspaceId,
      ws.userId
    );

    const first = await createAiWorkforceApi({
      organizationId: ws.workspaceId,
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      roleTitle: "Ops Agent",
      workspaceAgentId,
      idempotencyKey: "k-1",
    });
    expect(first.member).toMatchObject({
      id: workforceMemberId,
      memberType: "AI_AGENT",
      roleTitle: "Ops Agent",
      workspaceAgentId,
    });

    // Lặp lại cùng yêu cầu không sinh member mới.
    const again = await createAiWorkforceApi({
      organizationId: ws.workspaceId,
      authorization: ws.bearerToken,
      roleTitle: "Ops Agent",
      workspaceAgentId,
      idempotencyKey: "k-1",
    });
    expect(again.member.id).toBe(first.member.id);

    const list = await listOrganizationWorkforceApi({
      organizationId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    const aiRows = list.members.filter((m) => m.memberType === "AI_AGENT");
    expect(aiRows).toHaveLength(1);
    expect(aiRows[0]).toMatchObject({ id: workforceMemberId, workspaceAgentId });
  });

  it("refuses a foreign or non-deployable workspace agent", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const foreign = await createTestWorkspaceWithMember({ role: "founder" });
    const foreignAgent = await seedWorkspaceAgent(foreign.workspaceId, foreign.userId);
    const retiredAgent = await seedWorkspaceAgent(ws.workspaceId, ws.userId, "RETIRED");

    await expect(
      createAiWorkforceApi({
        organizationId: ws.workspaceId,
        authorization: ws.bearerToken,
        roleTitle: "Borrowed Agent",
        workspaceAgentId: foreignAgent.workspaceAgentId,
        idempotencyKey: "k-foreign",
      })
    ).rejects.toMatchObject({ code: "not_found" });
    await expect(
      createAiWorkforceApi({
        organizationId: ws.workspaceId,
        authorization: ws.bearerToken,
        roleTitle: "Retired Agent",
        workspaceAgentId: retiredAgent.workspaceAgentId,
        idempotencyKey: "k-retired",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
    await expect(
      createAiWorkforceApi({
        organizationId: ws.workspaceId,
        authorization: ws.bearerToken,
        roleTitle: "",
        workspaceAgentId: retiredAgent.workspaceAgentId,
        idempotencyKey: "k-empty",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });
});
