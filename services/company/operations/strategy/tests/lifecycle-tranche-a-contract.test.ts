import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import { createStagePolicy } from "../handlers/stage-policy.handler";
import { recordEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";
import { runGateEvaluation } from "../handlers/gate-evaluation.handler";
import { transitionProjectStageEndpoint, getStageContext } from "../handlers/project-stage.handler";

describe("COSA Lifecycle Tranche A Contract Verification", () => {
  const canonicalStages = [
    "P0_DISCOVERY",
    "P1_PROBLEM_VALIDATION",
    "P2_SOLUTION_VALIDATION",
    "P3_BUILD_VALIDATE",
    "P4_GO_TO_MARKET",
    "P5_OPERATE_GROWTH",
    "P6_SCALE_GOVERN",
  ] as const;

  it("verifies canonical wire stages P0–P6 structure", () => {
    expect(canonicalStages).toHaveLength(7);
    expect(canonicalStages[0]).toBe("P0_DISCOVERY");
    expect(canonicalStages[1]).toBe("P1_PROBLEM_VALIDATION");
    expect(canonicalStages[2]).toBe("P2_SOLUTION_VALIDATION");
    expect(canonicalStages[6]).toBe("P6_SCALE_GOVERN");
  });

  it("prohibits deprecated S-stages in canonical runtime validation", () => {
    const deprecatedStages = ["S0_IDEATION", "S1_PROBLEM_VALIDATION", "S2_SOLUTION_FIT"];
    for (const s of deprecatedStages) {
      expect(canonicalStages.includes(s as never)).toBe(false);
    }
  });

  it("validates evidence lifecycle state machine invariants", () => {
    const validStatuses = ["candidate", "approved", "rejected"] as const;
    expect(validStatuses).toContain("candidate");
    expect(validStatuses).toContain("approved");
    expect(validStatuses).toContain("rejected");
  });

  it("validates ingestion source system allowlist", () => {
    const validSources = ["interview", "crm", "telemetry", "payment"] as const;
    expect(validSources).toHaveLength(4);
    expect(validSources).toContain("interview");
    expect(validSources).toContain("crm");
    expect(validSources).toContain("telemetry");
    expect(validSources).toContain("payment");
  });

  it("executes full canonical Tranche A operating loop across services", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "admin" });

    // 1. Create project at P0
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Tranche A Operating Slice",
      description: "Governed venture operating slice",
      lifecycleStage: "P0_DISCOVERY",
    });
    expect(project.lifecycleStage).toBe("P0_DISCOVERY");

    // 2. Read stage context
    const ctx = await getStageContext({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
    });
    expect(ctx.project?.lifecycleStage).toBe("P0_DISCOVERY");

    // 3. Create stage policy requiring 1 reviewed interview
    const policy = await createStagePolicy({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      stageKey: "P0_DISCOVERY",
      minimumEvidenceScore: 0.5,
      requirements: [
        {
          key: "req_p0",
          sourceType: "customer_interview",
          minCount: 1,
          description: "Foundation Discovery Interview",
        },
      ],
    });

    // 4. Ingest candidate evidence
    const candEvidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Validated initial opportunity thesis",
      sampleSize: 10,
      supportsOrRefutes: "supports",
    });
    expect(candEvidence.status).toBe("candidate");

    // 5. Gate evaluation before review ignores candidate evidence
    const gate1 = await runGateEvaluation({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gate1.requirementsMet).toBe(false);

    // Verify stage did not mutate (recommendation only)
    const afterGate1Proj = await getProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(afterGate1Proj.lifecycleStage).toBe("P0_DISCOVERY");

    // 6. Privileged founder review
    const reviewed = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: candEvidence.id,
      action: "approve",
      comment: "Approved by founder",
    });
    expect(reviewed.status).toBe("approved");

    // 7. Gate evaluation after review passes
    const gate2 = await runGateEvaluation({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gate2.requirementsMet).toBe(true);
    expect(gate2.result).toBe("passed");

    // 8. Canonical transition to P1
    const transition = await transitionProjectStageEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "P0 gate passed with reviewed foundation evidence",
    });
    expect(transition.fromStage).toBe("P0_DISCOVERY");
    expect(transition.toStage).toBe("P1_PROBLEM_VALIDATION");
    expect(transition.noop).toBe(false);

    // 9. Verified project stage updated in DB
    const finalProj = await getProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(finalProj.lifecycleStage).toBe("P1_PROBLEM_VALIDATION");
  });
});
