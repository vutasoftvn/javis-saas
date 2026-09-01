import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import {
  createExperimentInWorkspace,
  getExperimentInWorkspace,
  listExperimentsInWorkspace,
  updateExperimentInWorkspace,
  deleteExperimentInWorkspace,
} from "../strategy/services/experiment-proposal.service";
import {
  recordEvidenceInWorkspace,
} from "../strategy/services/evidence-lifecycle.service";
import {
  reviewEvidenceInWorkspace,
} from "../strategy/services/evidence-review.service";
import {
  createPilotDraft,
  approvePilot,
} from "../strategy/services/pilot-run.service";

describe("Strategy Experiment and Review Services", () => {
  it("isolates experiment CRUD by workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project A",
    });

    const ctxA = makeTenantContext(wsA);
    const ctxB = makeTenantContext({ workspaceId: wsB.workspaceId, userId: wsA.userId });

    const expA = await createExperimentInWorkspace(ctxA, {
      projectId: projectA.id,
      hypothesis: "Conversion will increase by 20%",
      method: "landing_page_test",
      successCriteria: "Signups > 100",
      budget: 500,
    });

    expect(expA.id).toBeDefined();
    expect(expA.workspaceId).toBe(wsA.workspaceId);

    // Same workspace lookup
    const found = await getExperimentInWorkspace(ctxA, expA.id);
    expect(found.id).toBe(expA.id);

    // Cross-workspace lookup throws not_found
    await expect(getExperimentInWorkspace(ctxB, expA.id)).rejects.toMatchObject({
      code: "not_found",
    });

    // List
    const list = await listExperimentsInWorkspace(ctxA, { projectId: projectA.id });
    expect(list.items.some((i) => i.id === expA.id)).toBe(true);

    // Update
    const updated = await updateExperimentInWorkspace(ctxA, expA.id, { budget: 1000 });
    expect(updated.budget).toBe(1000);

    // Delete
    await deleteExperimentInWorkspace(ctxA, expA.id);
    await expect(getExperimentInWorkspace(ctxA, expA.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("enforces role permissions and lifecycle on pilot runs", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "member" });
    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project A Pilot",
    });

    const wsId = BigInt(wsA.workspaceId);
    const projId = BigInt(projectA.id);
    const memberId = BigInt(wsA.userId);

    const ctxA_Member = makeTenantContext(wsA, { membershipRole: "member" });
    const ctxA_Founder = makeTenantContext(wsA, { membershipRole: "founder" });

    // Record and approve evidence for design partner
    const ev = await recordEvidenceInWorkspace(ctxA_Member, {
      projectId: projectA.id,
      sourceType: "partner_commitment",
      claim: "Partner signs LOI",
    });
    const approvedEv = await reviewEvidenceInWorkspace(ctxA_Founder, {
      id: ev.id,
      action: "approve",
    });

    const pilot = await createPilotDraft({
      workspaceId: wsId,
      projectId: projId,
      designPartnerEvidenceRefs: [approvedEv.id],
      metricContractArtifactRef: "art-metric",
      instrumentationArtifactRef: "art-inst",
      onboardingArtifactRef: "art-onboard",
      rollbackArtifactRef: "art-rollback",
      releaseOwnerMemberId: memberId,
      actorMemberId: memberId,
    });

    expect(pilot.status).toBe("DRAFT");

    // Regular member cannot approve pilot
    await expect(
      approvePilot({
        workspaceId: wsId,
        pilotId: pilot.id,
        approvalRef: "appr-1",
        actorMemberId: memberId,
        actorRole: "member",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // Founder can approve pilot
    const approved = await approvePilot({
      workspaceId: wsId,
      pilotId: pilot.id,
      approvalRef: "appr-1",
      actorMemberId: memberId,
      actorRole: "founder",
    });
    expect(approved.status).toBe("APPROVED");
  });
});
