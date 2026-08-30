import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "../../tests/_helpers";
import { createProject } from "../../handlers/project.handler";
import { createStagePolicy } from "../handlers/stage-policy.handler";
import { recordEvidence, getEvidence, listEvidence } from "../handlers/evidence.handler";
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
          minCount: 1,
          sourceType: "customer_interview",
          description: "At least 1 customer interview",
        },
      ],
    });

    // 1. Ingest evidence as candidate (default)
    const candidateEvidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "8 out of 10 users verified the problem",
      sampleSize: 10,
      supportsOrRefutes: "supports",
    });

    expect(candidateEvidence.id).toBeDefined();
    expect(candidateEvidence.status).toBe("candidate");
    expect(candidateEvidence.reviewedAt).toBeNull();

    // 2. Gate evaluation while evidence is still candidate -> gate should FAIL (requirementsMet = false)
    const gateEvalCandidate = await runGateEvaluation({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gateEvalCandidate.requirementsMet).toBe(false);
    expect(gateEvalCandidate.result).toBe("failed");

    // 3. Tenant boundary check: workspaceB cannot review ws evidence
    await expect(
      reviewEvidence({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: candidateEvidence.id,
        action: "approve",
      })
    ).rejects.toMatchObject({ code: "not_found" });

    // 4. Privileged review: approve evidence
    const approvedEvidence = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: candidateEvidence.id,
      action: "approve",
      comment: "Verified with 10 real interview recordings.",
    });

    expect(approvedEvidence.status).toBe("approved");
    expect(approvedEvidence.reviewComment).toBe("Verified with 10 real interview recordings.");
    expect(approvedEvidence.reviewedAt).toBeDefined();

    // 5. Gate evaluation after approval -> gate should PASS
    const gateEvalApproved = await runGateEvaluation({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gateEvalApproved.requirementsMet).toBe(true);
    expect(gateEvalApproved.result).toBe("passed");
  });

  it("direct recording of approved evidence by founder is allowed", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Direct Evidence Project",
      description: "Testing direct approved evidence recording",
      lifecycleStage: "P0_DISCOVERY",
    });

    const directApproved = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Founder verified directly in field test",
      sampleSize: 15,
      supportsOrRefutes: "supports",
      status: "approved",
    });

    expect(directApproved.status).toBe("approved");
    expect(directApproved.reviewedAt).toBeDefined();
  });
});
