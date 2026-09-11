import { describe, it, expect, beforeEach } from "vitest";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
} from "./_helpers";
import {
  createDraftDeliberationApi,
  frameDeliberationApi,
  cancelDeliberationApi,
  appendFounderDecisionApi,
  getDeliberationApi,
} from "../handlers/executive-deliberation.handler";
import { activateProjectStartupTeamMember } from "../services/project-startup-team.service";
import { activateExecutiveRole } from "../services/executive-role-activation.service";

describe("Executive Deliberation Handler", () => {
  let founderToken: string;
  let memberToken: string;
  let workspaceId: string;
  let projectId: string;
  let foreignProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;
    founderToken = ws.bearerToken;

    const member = await addMemberToWorkspace(workspaceId, "member");
    memberToken = member.bearerToken;

    const secondWs = await createSecondWorkspace();
    foreignProjectId = secondWs.projectId;

    const founderCtx = {
      workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    };

    await activateProjectStartupTeamMember(founderCtx, projectId, "finance", { expectedVersion: 1 });
    await activateExecutiveRole(founderCtx, projectId, "cfo", { expectedVersion: 1 });
  });

  it("handles deliberation lifecycle through HTTP handlers", async () => {
    // 1. Create draft
    const draft = await createDraftDeliberationApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      title: "Pricing Strategy Review",
    });
    expect(draft.state).toBe("DRAFT");

    // 2. Member cannot frame
    await expect(
      frameDeliberationApi({
        authorization: memberToken,
        workspaceId,
        projectId,
        deliberationId: draft.id,
        question: "Should we raise enterprise tier price?",
        roleKeys: ["cfo"],
      })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);

    // 3. Founder frames
    const framed = await frameDeliberationApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      deliberationId: draft.id,
      question: "Should we raise enterprise tier price?",
      roleKeys: ["cfo"],
      expectedVersion: draft.version,
    });
    expect(framed.state).toBe("ANALYSIS_QUEUED");

    // 4. Get deliberation
    const details = await getDeliberationApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      deliberationId: draft.id,
    });
    expect(details.title).toBe("Pricing Strategy Review");
    expect(details.activeFrame?.question).toBe("Should we raise enterprise tier price?");

    // 5. Append decision
    const decision = await appendFounderDecisionApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      deliberationId: draft.id,
      decisionType: "APPROVE",
      expectedVersion: framed.version,
      notes: "Approve 15% increase",
    });
    expect(decision.decisionType).toBe("APPROVE");
  });
});
