import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  deployWorkspaceAgentForProfile,
} from "./_helpers";
import {
  createDraftDeliberationApi,
  frameDeliberationApi,
  cancelDeliberationApi,
  appendFounderDecisionApi,
  getDeliberationApi,
} from "../handlers/executive-deliberation.handler";
import { activateWorkspaceExecutiveRole } from "../services/workspace-executive-role-activation.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { completeAllAnalyses } from "./_deliberation-helpers";

// COSA Control Plane là app khác — giả lập đúng catalog generated (xem executive-deliberation.service.test.ts).
vi.mock("../services/advisor-overlay.client", () => ({
  fetchAdvisorOverlayIdentity: vi.fn(async (_ws: string, roleKey: string) => {
    const { ADVISOR_OVERLAY_CATALOG: catalog } = await import(
      "../../shared/contracts/executive-advisor-overlays.generated"
    );
    return catalog[roleKey];
  }),
}));

describe("Executive Deliberation Handler", () => {
  let founderToken: string;
  let memberToken: string;
  let workspaceId: string;
  let projectId: string;
  let foreignProjectId: string;
  let founderCtx: TenantContext;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    founderToken = ws.bearerToken;
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;

    const secondWs = await createSecondWorkspace();
    foreignProjectId = secondWs.projectId;

    const member = await addMemberToWorkspace(workspaceId, "member");
    memberToken = member.bearerToken;

    founderCtx = {
      workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: [],
      correlationId: "corr-test",
      isAiAgent: false,
    };

    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});
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

    // 5. Worker trả phân tích → AWAITING_FOUNDER; quyết định trước đó bị từ chối.
    await expect(
      appendFounderDecisionApi({
        authorization: founderToken,
        workspaceId,
        projectId,
        deliberationId: draft.id,
        decisionType: "APPROVE",
      })
    ).rejects.toThrow(/DELIBERATION_NOT_AWAITING_FOUNDER/);
    await completeAllAnalyses(founderCtx, projectId, draft.id);
    const awaiting = await getDeliberationApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      deliberationId: draft.id,
    });
    expect(awaiting.state).toBe("AWAITING_FOUNDER");

    // 6. Append decision
    const decision = await appendFounderDecisionApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      deliberationId: draft.id,
      decisionType: "APPROVE",
      expectedVersion: awaiting.version,
      notes: "Approve 15% increase",
    });
    expect(decision.decisionType).toBe("APPROVE");
  });
});
