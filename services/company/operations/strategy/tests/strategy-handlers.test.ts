import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "../../tests/_helpers";
import {
  createStagePolicy,
  getStagePolicy,
  listStagePolicies,
  updateStagePolicy,
  deleteStagePolicy,
} from "../handlers/stage-policy.handler";
import {
  createStageTransition,
  getStageTransition,
  listStageTransitions,
} from "../handlers/stage-transition.handler";
import {
  createAssumption,
  getAssumption,
  listAssumptions,
  updateAssumption,
  getRankedAssumptionsByProject,
} from "../handlers/assumption.handler";
import {
  createExperiment,
  getExperiment,
  listExperiments,
  updateExperiment,
  proposeExperiments,
} from "../handlers/experiment.handler";
import {
  recordEvidence,
  getEvidence,
  listEvidence,
  updateEvidence,
} from "../handlers/evidence.handler";
import {
  createInterview,
  getInterview,
  listInterviews,
} from "../handlers/interview.handler";
import {
  createDiscoverySignal,
  getDiscoverySignal,
  listDiscoverySignals,
} from "../handlers/discovery-signal.handler";
import {
  runGateEvaluation,
  getGateEvaluation,
  listGateEvaluations,
} from "../handlers/gate-evaluation.handler";
import {
  createDecisionRecord,
  getDecisionRecord,
  listDecisionRecords,
} from "../handlers/decision-record.handler";
import { getNextBestActions } from "../handlers/next-best-action.handler";
import { createProject } from "../../handlers/project.handler";

describe("Phase 2: Strategy Domain API Handlers & Tenant Isolation", () => {
  it("1. Stage Policy CRUD & Tenant Isolation", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const policyA = await createStagePolicy({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      stageKey: "S1_PROBLEM_VALIDATION",
      requirements: [{ key: "interviews", minCount: 5, description: "5 Customer Interviews" }],
      minimumEvidenceScore: 0.7,
      blockingRiskRules: ["NO_LEGAL_BLOCKER"],
    });

    expect(policyA.id).toBeDefined();
    expect(policyA.stageKey).toBe("S1_PROBLEM_VALIDATION");
    expect(policyA.minimumEvidenceScore).toBe(0.7);

    // List for workspaceA
    const listA = await listStagePolicies({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
    });
    expect(listA.items.some((p) => p.id === policyA.id)).toBe(true);

    // Tenant isolation: workspaceB should NOT see policyA
    // Note: wsA user tries to access wsB - should get permission_denied, not see the policy
    await expect(
      listStagePolicies({
        authorization: wsA.bearerToken,
        workspaceId: wsB.workspaceId,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // Update policy
    const updated = await updateStagePolicy({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: policyA.id,
      minimumEvidenceScore: 0.8,
    });
    expect(updated.minimumEvidenceScore).toBe(0.8);
  });

  it("2. Stage Transition CRUD", async () => {
    const wsA = await createTestWorkspaceWithMember();

    const transition = await createStageTransition({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      fromStage: "S0_GENESIS",
      toStage: "S1_PROBLEM_VALIDATION",
      allowed: true,
    });

    expect(transition.id).toBeDefined();
    expect(transition.fromStage).toBe("S0_GENESIS");
    expect(transition.toStage).toBe("S1_PROBLEM_VALIDATION");

    const fetched = await getStageTransition({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: transition.id,
    });
    expect(fetched.id).toBe(transition.id);
  });

  it("3. End-to-end Strategy Flow with Project, Assumption, Experiment, Evidence, Gate, Decision, and Next Actions", async () => {
    const wsA = await createTestWorkspaceWithMember();

    // 1. Create a Project
    const project = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "AI Co-Founder Platform",
      description: "Autonomous strategy engine for founders",
      phase: "S1_PROBLEM_VALIDATION",
    });

    expect(project.id).toBeDefined();

    // 2. Create Assumptions
    const assumption1 = await createAssumption({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      statement: "Founders want deterministic next-best-action recommendations",
      importance: 9,
      uncertainty: 8,
    });
    expect(assumption1.riskScore).toBe(72);

    const assumption2 = await createAssumption({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      statement: "Founders prefer mobile UI over web dashboard",
      importance: 4,
      uncertainty: 4,
    });
    expect(assumption2.riskScore).toBe(16);

    // Verify ranked assumptions
    const rankedAssumptions = await getRankedAssumptionsByProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
    });
    expect(rankedAssumptions.items[0].id).toBe(assumption1.id);
    expect(rankedAssumptions.items[0].computedRiskScore).toBe(72);

    // 3. Propose Experiments
    const proposed = await proposeExperiments({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
    });
    expect(proposed.items.length).toBeGreaterThanOrEqual(1);
    expect(proposed.items[0].assumptionId).toBe(assumption1.id);

    // 4. Create Experiment
    const exp = await createExperiment({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      assumptionId: assumption1.id,
      hypothesis: proposed.items[0].hypothesis,
      method: proposed.items[0].method,
      successCriteria: proposed.items[0].successCriteria,
      budget: 100,
    });
    expect(exp.id).toBeDefined();

    // 5. Conduct Interview
    const interview = await createInterview({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      notes: "Founder expressed urgent pain with chaotic task priorities and loved deterministic roadmap.",
    });
    expect(interview.id).toBeDefined();

    // 6. Record Discovery Signal
    const signal = await createDiscoverySignal({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      signalType: "market_search_trend",
      payload: { keyword: "AI co-founder", searchVolumeGrowth: "+300%" },
      source: "Google Trends",
    });
    expect(signal.id).toBeDefined();

    // 7. Record Evidence (auto-scored)
    const evidenceItem = await recordEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      experimentId: exp.id,
      sourceType: "customer_interview",
      claim: "8 out of 10 founders validate extreme demand for deterministic next-action system",
      sampleSize: 10,
      supportsOrRefutes: "supports",
    });
    expect(evidenceItem.id).toBeDefined();
    expect(evidenceItem.strength).toBe(0.85);
    expect(evidenceItem.confidence).toBeGreaterThanOrEqual(0.8);

    // 8. Create Policy & Evaluate Gate
    const policy = await createStagePolicy({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      stageKey: "S1_PROBLEM_VALIDATION",
      minimumEvidenceScore: 0.6,
      requirements: [{ key: "interview_evidence", minCount: 1, sourceType: "customer_interview", description: "Customer Interview" }],
    });

    const gateEval = await runGateEvaluation({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      stagePolicyId: policy.id,
    });
    expect(gateEval.id).toBeDefined();
    expect(gateEval.requirementsMet).toBe(true);
    expect(gateEval.result).toBe("passed");

    // Check project phase was updated and outbox event emitted
    const { getProject } = await import("../../handlers/project.handler");
    const updatedProject = await getProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: project.id,
    });
    expect(updatedProject.phase).toBe("S2_SOLUTION_VALIDATION");

    const { eventOutbox } = await import("../../../shared/db/schema/integration");
    const { eq } = await import("drizzle-orm");
    const { db } = await import("../../models/db");
    const phaseEvents = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, project.id));
    expect(phaseEvents.some((e) => e.eventType.startsWith("project.phase.changed"))).toBe(true);

    // 9. Record Decision with Evidence Snapshot
    const decision = await createDecisionRecord({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: project.id,
      gateEvaluationId: gateEval.id,
      decision: "proceed",
      notes: "S1 passed with strong qualitative evidence. Advance to S2.",
    });
    expect(decision.id).toBeDefined();
    expect(decision.decision).toBe("proceed");
    expect(decision.evidenceSnapshot.totalEvidenceCount).toBe(1);

    // 10. Query Next Best Actions
    const nextActions = await getNextBestActions({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: project.id,
    });
    expect(nextActions.projectId).toBe(project.id);
    expect(nextActions.items.length).toBeGreaterThan(0);
    expect(nextActions.items[0].candidate).toBeDefined();
    expect(nextActions.items[0].rank).toBe(1);
  });
});
