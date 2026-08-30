import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import { recordEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";
import {
  createPilot,
  approvePilot,
  activatePilot,
  closePilot,
  getPilot,
  listPilots,
} from "../handlers/pilot-run.handler";

describe("Pilot Run Aggregate & State Machine (Tranche B1)", () => {
  it("manages human-owned pilot lifecycle with strict role authorization and reviewed evidence guards", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();
    const memberA = await addMemberToWorkspace(wsA.workspaceId, "member");

    // 1. Create a P2 project in workspace A
    const p2Project = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Pilot Validation Project",
      description: "Moving from P2 to P3 Pilot",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });
    expect(p2Project.lifecycleStage).toBe("P2_SOLUTION_VALIDATION");

    // 2. Record unreviewed candidate evidence
    const candidateEvidence = await recordEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: p2Project.id,
      sourceType: "customer_interview",
      claim: "Design partner committed to 3-month pilot test",
      sampleSize: 5,
      supportsOrRefutes: "supports",
    });
    expect(candidateEvidence.status).toBe("candidate");

    // 3. Attempting to create pilot draft with unreviewed candidate evidence is rejected
    await expect(
      createPilot({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: p2Project.id,
        designPartnerEvidenceRefs: [candidateEvidence.id],
        metricContractArtifactRef: "artifact://ws-a/metrics/pilot-v1",
        instrumentationArtifactRef: "artifact://ws-a/instrumentation/pilot-v1",
        onboardingArtifactRef: "artifact://ws-a/pilot/onboarding-v1",
        rollbackArtifactRef: "artifact://ws-a/pilot/rollback-v1",
        releaseOwnerMemberId: wsA.userId,
      })
    ).rejects.toThrow(/chưa được review|approved/i);

    // 4. Founder reviews and approves evidence
    const reviewedEvidence = await reviewEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: candidateEvidence.id,
      action: "approve",
      comment: "Design partner contract and interview verified",
    });
    expect(reviewedEvidence.status).toBe("approved");

    // 5. Create pilot draft with reviewed evidence
    const draft = await createPilot({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: p2Project.id,
      designPartnerEvidenceRefs: [reviewedEvidence.id],
      metricContractArtifactRef: "artifact://ws-a/metrics/pilot-v1",
      instrumentationArtifactRef: "artifact://ws-a/instrumentation/pilot-v1",
      onboardingArtifactRef: "artifact://ws-a/pilot/onboarding-v1",
      rollbackArtifactRef: "artifact://ws-a/pilot/rollback-v1",
      releaseOwnerMemberId: wsA.userId,
    });
    expect(draft.status).toBe("DRAFT");
    expect(draft.projectId).toBe(p2Project.id);
    expect(draft.designPartnerEvidenceRefs).toContain(reviewedEvidence.id);

    // 6. Activating DRAFT pilot directly fails (must be APPROVED first)
    await expect(
      activatePilot({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: draft.id,
        approvalRef: "APR-1",
      })
    ).rejects.toThrow(/APPROVED/i);

    // 7. Non-privileged member cannot approve pilot
    await expect(
      approvePilot({
        authorization: memberA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: draft.id,
        approvalRef: "APR-1",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);

    // 8. Founder approves pilot
    const approved = await approvePilot({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: draft.id,
      approvalRef: "APR-1",
    });
    expect(approved.status).toBe("APPROVED");
    expect(approved.approvalRef).toBe("APR-1");
    expect(approved.approvedAt).toBeDefined();

    // 9. Non-privileged member cannot activate pilot
    await expect(
      activatePilot({
        authorization: memberA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: draft.id,
        approvalRef: "APR-1",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);

    // 10. Founder activates pilot
    const active = await activatePilot({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: draft.id,
      approvalRef: "APR-1",
    });
    expect(active.status).toBe("ACTIVE");
    expect(active.activatedAt).toBeDefined();

    // 11. Invariant: Project stage remains P2_SOLUTION_VALIDATION (never changed by pilot activation)
    const projectAfter = await getProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: p2Project.id,
    });
    expect(projectAfter.lifecycleStage).toBe("P2_SOLUTION_VALIDATION");

    // 12. Idempotency: re-activating returns ACTIVE pilot rather than error
    const reActive = await activatePilot({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: draft.id,
      approvalRef: "APR-1",
    });
    expect(reActive.status).toBe("ACTIVE");

    // 13. Cross-workspace isolation
    await expect(
      getPilot({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: draft.id,
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    await expect(
      activatePilot({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: draft.id,
        approvalRef: "APR-B",
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    // 14. List pilots in workspace A
    const listResult = await listPilots({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: p2Project.id,
    });
    expect(listResult.items.length).toBe(1);
    expect(listResult.items[0].id).toBe(draft.id);

    // 15. Close pilot (COMPLETED)
    const completed = await closePilot({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: draft.id,
      status: "COMPLETED",
    });
    expect(completed.status).toBe("COMPLETED");
    expect(completed.completedAt).toBeDefined();
  });

  it("permits cancellation with reason from non-terminal states", async () => {
    const ws = await createTestWorkspaceWithMember();

    const proj = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Cancel Test Project",
      lifecycleStage: "P2_SOLUTION_VALIDATION",
    });

    const ev = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: proj.id,
      sourceType: "customer_interview",
      claim: "Reviewed interview for cancellation test",
    });

    await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: ev.id,
      action: "approve",
    });

    const draft = await createPilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: proj.id,
      designPartnerEvidenceRefs: [ev.id],
      metricContractArtifactRef: "artifact://ws/metrics/v1",
      instrumentationArtifactRef: "artifact://ws/inst/v1",
      onboardingArtifactRef: "artifact://ws/onb/v1",
      rollbackArtifactRef: "artifact://ws/rb/v1",
      releaseOwnerMemberId: ws.userId,
    });

    // Cancelling without reason fails
    await expect(
      closePilot({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: draft.id,
        status: "CANCELLED",
        cancellationReason: "",
      })
    ).rejects.toThrow(/cancellationReason is required/i);

    // Cancelling with reason succeeds
    const cancelled = await closePilot({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: draft.id,
      status: "CANCELLED",
      cancellationReason: "Design partner postponed their trial program",
    });
    expect(cancelled.status).toBe("CANCELLED");
    expect(cancelled.cancellationReason).toBe("Design partner postponed their trial program");
    expect(cancelled.cancelledAt).toBeDefined();

    // Closing already cancelled pilot fails
    await expect(
      closePilot({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: draft.id,
        status: "CANCELLED",
        cancellationReason: "Another reason",
      })
    ).rejects.toThrow(/terminal/i);
  });
});
