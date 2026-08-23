import { describe, it, expect } from "vitest";
import {
  assessProjectStage,
  rankAssumptions,
  proposeExperimentsForAssumptions,
  scoreEvidence,
  evaluateGate,
  buildDecisionRecord,
  generateAndRankNextActions,
} from "../services";

describe("Phase 2c: Deterministic Strategy Business Logic Services", () => {
  describe("1. stage-assessment.service", () => {
    it("should return S0_GENESIS when no evidence or passed gates exist", () => {
      const result = assessProjectStage({ evidenceList: [] });
      expect(result.recommendedStage).toBe("S0_GENESIS");
    });

    it("should recommend S1_PROBLEM_VALIDATION when supporting evidence exists without passed gates", () => {
      const result = assessProjectStage({
        evidenceList: [
          { sourceType: "interview", strength: 0.8, confidence: 0.8, supportsOrRefutes: "supports" },
        ],
      });
      expect(result.recommendedStage).toBe("S1_PROBLEM_VALIDATION");
      expect(result.supportingEvidenceCount).toBe(1);
    });

    it("should advance stage according to passed gates deterministically", () => {
      const resultS2 = assessProjectStage({
        evidenceList: [],
        passedGates: [{ stageKey: "S1_PROBLEM_VALIDATION", result: "passed" }],
      });
      expect(resultS2.recommendedStage).toBe("S2_SOLUTION_VALIDATION");

      const resultS3 = assessProjectStage({
        evidenceList: [],
        passedGates: [
          { stageKey: "S1_PROBLEM_VALIDATION", result: "passed" },
          { stageKey: "S2_SOLUTION_VALIDATION", result: "passed" },
        ],
      });
      expect(resultS3.recommendedStage).toBe("S3_MVP_BUILD");
    });
  });

  describe("2. assumption-ranking.service", () => {
    it("should rank assumptions by risk score = importance * uncertainty descending", () => {
      const assumptions = [
        { id: 1, projectId: 10, statement: "Market size is large", importance: 3, uncertainty: 4 }, // score = 12
        { id: 2, projectId: 10, statement: "Customers will pay $50/mo", importance: 9, uncertainty: 8 }, // score = 72
        { id: 3, projectId: 10, statement: "Churn is below 2%", importance: 7, uncertainty: 5 }, // score = 35
      ];

      const ranked = rankAssumptions(assumptions);
      expect(ranked).toHaveLength(3);
      expect(ranked[0].id).toBe(2);
      expect(ranked[0].computedRiskScore).toBe(72);
      expect(ranked[0].rank).toBe(1);

      expect(ranked[1].id).toBe(3);
      expect(ranked[1].computedRiskScore).toBe(35);
      expect(ranked[1].rank).toBe(2);

      expect(ranked[2].id).toBe(1);
      expect(ranked[2].computedRiskScore).toBe(12);
      expect(ranked[2].rank).toBe(3);
    });

    it("should have deterministic tie-breaking for equal risk scores", () => {
      const assumptions = [
        { id: 10, projectId: 1, statement: "Zeta hypothesis", importance: 5, uncertainty: 4 }, // 20, uncert=4
        { id: 20, projectId: 1, statement: "Alpha hypothesis", importance: 4, uncertainty: 5 }, // 20, uncert=5 (higher uncertainty first)
      ];

      const ranked = rankAssumptions(assumptions);
      expect(ranked[0].id).toBe(20);
    });
  });

  describe("3. experiment-proposal.service", () => {
    it("should generate experiment proposals for top untested assumptions", () => {
      const rankedAssumptions = rankAssumptions([
        { id: 1, projectId: 100, statement: "Customers need feature X", importance: 9, uncertainty: 9 },
        { id: 2, projectId: 100, statement: "Users prefer mobile app", importance: 5, uncertainty: 5 },
      ]);

      const proposals = proposeExperimentsForAssumptions(rankedAssumptions, [], 2);
      expect(proposals).toHaveLength(2);
      expect(proposals[0].assumptionId).toBe(1);
      expect(proposals[0].hypothesis).toContain("Customers need feature X");
      expect(proposals[0].status).toBe("draft");
    });

    it("should exclude already covered assumptions", () => {
      const rankedAssumptions = rankAssumptions([
        { id: 1, projectId: 100, statement: "A1", importance: 9, uncertainty: 9 },
        { id: 2, projectId: 100, statement: "A2", importance: 5, uncertainty: 5 },
      ]);

      const proposals = proposeExperimentsForAssumptions(rankedAssumptions, [{ assumptionId: 1 }], 2);
      expect(proposals).toHaveLength(1);
      expect(proposals[0].assumptionId).toBe(2);
    });
  });

  describe("4. evidence-scoring.service", () => {
    it("should score evidence by source type weights with normalized values [0, 1]", () => {
      const interviewScore = scoreEvidence({ sourceType: "customer_interview" });
      expect(interviewScore.strength).toBe(0.85);
      expect(interviewScore.confidence).toBe(0.80);
      expect(interviewScore.compositeScore).toBe(0.68);

      const paymentScore = scoreEvidence({ sourceType: "financial_transaction" });
      expect(paymentScore.strength).toBe(0.95);
      expect(paymentScore.confidence).toBe(0.90);

      const surveyScore = scoreEvidence({ sourceType: "survey", sampleSize: 20 });
      expect(surveyScore.confidence).toBeGreaterThan(0.65);
    });
  });

  describe("5. gate-evaluation.service", () => {
    it("should pass gate when evidence meets requirements and no blocking risks exist", () => {
      const evaluation = evaluateGate({
        policy: {
          stageKey: "S1_PROBLEM_VALIDATION",
          minimumEvidenceScore: 0.6,
          requirements: [{ key: "interviews", minCount: 2, sourceType: "customer_interview", description: "Interviews" }],
        },
        evidenceList: [
          { sourceType: "customer_interview", strength: 0.85, confidence: 0.8, supportsOrRefutes: "supports" },
          { sourceType: "customer_interview", strength: 0.85, confidence: 0.8, supportsOrRefutes: "supports" },
        ],
      });

      expect(evaluation.requirementsMet).toBe(true);
      expect(evaluation.result).toBe("passed");
      expect(evaluation.evidenceScore).toBeGreaterThanOrEqual(0.6);
    });

    it("should fail gate when unresolved critical blocking risks exist", () => {
      const evaluation = evaluateGate({
        policy: {
          stageKey: "S1_PROBLEM_VALIDATION",
          minimumEvidenceScore: 0.5,
          requirements: [],
        },
        evidenceList: [
          { sourceType: "customer_interview", strength: 0.9, confidence: 0.9, supportsOrRefutes: "supports" },
        ],
        blockingRisks: [
          { riskKey: "REGULATORY_BLOCKER", severity: "critical", resolved: false },
        ],
      });

      expect(evaluation.requirementsMet).toBe(false);
      expect(evaluation.result).toBe("failed");
      expect(evaluation.blockingRisks).toHaveLength(1);
    });
  });

  describe("6. decision-recording.service", () => {
    it("should package decision record with complete evidence snapshot", () => {
      const record = buildDecisionRecord({
        projectId: 1,
        decision: "proceed",
        actorMemberId: 5,
        evidenceList: [
          { id: 101, sourceType: "customer_interview", strength: 0.85, confidence: 0.8, supportsOrRefutes: "supports" },
        ],
        notes: "Approved stage 1 advancement",
      });

      expect(record.decision).toBe("proceed");
      expect(record.evidenceSnapshot.totalEvidenceCount).toBe(1);
      expect(record.evidenceSnapshot.supportingCount).toBe(1);
      expect(record.evidenceSnapshot.averageStrength).toBe(0.85);
      expect(record.evidenceSnapshot.decisionNotes).toBe("Approved stage 1 advancement");
    });
  });

  describe("7. next-best-action.service", () => {
    it("should generate deterministic ranking across multiple candidate sources", () => {
      const input = {
        projectId: 42,
        untestedAssumptions: [
          { id: 1, statement: "High-value assumption", importance: 10, uncertainty: 10 }, // score = 50 + 45 = 95
          { id: 2, statement: "Medium assumption", importance: 5, uncertainty: 5 }, // score = 50 + 11 = 61
        ],
        blockedTasks: [
          { id: 10, title: "Deploy API backend", priority: "urgent", status: "blocked" }, // score = 90
        ],
        okrGaps: [
          { id: 20, title: "Sign 5 LOIs", currentValue: 1, targetValue: 5, gapPercentage: 80 }, // score = 55 + 24 = 79
        ],
      };

      const run1 = generateAndRankNextActions(input);
      const run2 = generateAndRankNextActions(input);

      // Verify deterministic reproduction
      expect(run1).toEqual(run2);

      // Verify ranking order
      expect(run1[0].candidate.source).toBe("assumption");
      expect(run1[0].candidate.score).toBe(95);
      expect(run1[0].rank).toBe(1);

      expect(run1[1].candidate.source).toBe("task");
      expect(run1[1].candidate.score).toBe(90);
      expect(run1[1].rank).toBe(2);

      expect(run1[2].candidate.source).toBe("okr_gap");
      expect(run1[2].candidate.score).toBe(79);
      expect(run1[2].rank).toBe(3);

      expect(run1[3].candidate.source).toBe("assumption");
      expect(run1[3].candidate.score).toBe(61);
      expect(run1[3].rank).toBe(4);
    });
  });
});
