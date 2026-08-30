import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import { createProject } from "../../handlers/project.handler";
import { createStagePolicy } from "../handlers/stage-policy.handler";
import { recordEvidence, getEvidence, listEvidence, updateEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";
import { runGateEvaluation } from "../handlers/gate-evaluation.handler";

describe("Evidence Kernel: candidate-to-approved lifecycle & workspace boundary", () => {
  it("candidate evidence requires privileged review before gate evaluation considers it", async () => {
    const ws = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    // Create a project in ws
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Evidence Kernel Project",
      description: "Testing candidate-to-approved evidence workflow",
      lifecycleStage: "P1_PROBLEM_VALIDATION",
    });

    // Create a stage policy requiring 1 interview evidence
    const policy = await createStagePolicy({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      stageKey: "P1_PROBLEM_VALIDATION",
      minimumEvidenceScore: 0.6,
      requirements: [
        {
          key: "interview_req",
          sourceType: "customer_interview",
          minCount: 1,
          description: "1 customer interview",
        },
      ],
    });

    // 1. Record evidence without approval (default is candidate)
    const candEvidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Customer validated problem exists",
      sampleSize: 10,
      supportsOrRefutes: "supports",
    });

    expect(candEvidence.status).toBe("candidate");
    expect(candEvidence.reviewedAt).toBeNull();

    // 2. Gate evaluation ignores candidate evidence -> requirements not met
    const gateEvalCandidate = await runGateEvaluation({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gateEvalCandidate.requirementsMet).toBe(false);
    expect(gateEvalCandidate.result).toBe("failed");

    // 3. Workspace boundary: Workspace B member cannot review Workspace A evidence
    await expect(
      reviewEvidence({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: candEvidence.id,
        action: "approve",
      })
    ).rejects.toThrow(/not found/i);

    // 4. Founder reviews and approves evidence in Workspace A
    const approvedEvidence = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: candEvidence.id,
      action: "approve",
      comment: "Verified audio transcript & interview notes",
    });

    expect(approvedEvidence.status).toBe("approved");
    expect(approvedEvidence.reviewComment).toBe("Verified audio transcript & interview notes");
    expect(approvedEvidence.reviewedAt).toBeDefined();

    // 5. Gate evaluation now includes approved evidence -> requirements met
    const gateEvalApproved = await runGateEvaluation({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gateEvalApproved.requirementsMet).toBe(true);
    expect(gateEvalApproved.result).toBe("passed");
  });

  it("direct recording of approved evidence is forbidden and candidate creation is enforced", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Direct Evidence Project",
      description: "Testing direct approved evidence recording",
      lifecycleStage: "P0_DISCOVERY",
    });

    // 1. Attempting to record approved evidence directly is rejected
    await expect(
      recordEvidence({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        sourceType: "customer_interview",
        claim: "Founder verified directly in field test",
        sampleSize: 15,
        supportsOrRefutes: "supports",
        status: "approved" as any,
      })
    ).rejects.toThrow(/candidate/i);

    // 2. Creating candidate evidence succeeds
    const cand = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Valid candidate claim",
      sampleSize: 15,
      supportsOrRefutes: "supports",
    });
    expect(cand.status).toBe("candidate");

    // 3. Founder reviews and approves
    const reviewed = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: cand.id,
      action: "approve",
      comment: "Approved by founder",
    });
    expect(reviewed.status).toBe("approved");

    // 4. Update on approved evidence requires privileged role
    const member = await addMemberToWorkspace(ws.workspaceId, "member");
    await expect(
      updateEvidence({
        authorization: member.bearerToken,
        workspaceId: ws.workspaceId,
        id: cand.id,
        claim: "Tampered claim by member",
      })
    ).rejects.toThrow(/privilege|founder|admin/i);
  });
});
