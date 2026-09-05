import { describe, expect, it } from "vitest";
import { isEvidenceEligible } from "../services/eligible-evidence.service";
import { runGateEvaluationInWorkspace } from "../services/gate-evaluation.service";
import { calculatePmfScoreboard } from "../services/pmf-scoreboard.service";
import {
  transitionProjectStageInTransaction,
  ProjectLifecycleStage,
} from "../services/project-stage-lifecycle.service";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { db } from "../../models/db";
import { eq } from "drizzle-orm";
import {
  evidence,
  stagePolicies,
  metricContracts,
  metricSnapshots,
  decisionRecords,
  projectStageTransitions,
} from "../../../shared/db/schema/strategy";
import { projects } from "../../../shared/db/schema/operations";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("strategy-gate-integrity: isEvidenceEligible unit matrix", () => {
  const now = new Date("2026-09-05T10:00:00Z");

  it("approves valid, fresh, non-deleted evidence", () => {
    expect(
      isEvidenceEligible(
        {
          status: "approved",
          deletedAt: null,
          freshUntil: null,
        },
        now
      )
    ).toBe(true);

    expect(
      isEvidenceEligible(
        {
          status: "approved",
          deletedAt: null,
          freshUntil: new Date("2026-09-06T00:00:00Z"),
        },
        now
      )
    ).toBe(true);
  });

  it("rejects candidate, rejected, deleted, or expired evidence", () => {
    // candidate (even with high score) is not eligible
    expect(
      isEvidenceEligible(
        {
          status: "candidate",
          deletedAt: null,
          freshUntil: null,
        },
        now
      )
    ).toBe(false);

    // deleted evidence is not eligible
    expect(
      isEvidenceEligible(
        {
          status: "approved",
          deletedAt: new Date("2026-09-01T00:00:00Z"),
          freshUntil: null,
        },
        now
      )
    ).toBe(false);

    // expired evidence is not eligible
    expect(
      isEvidenceEligible(
        {
          status: "approved",
          deletedAt: null,
          freshUntil: new Date("2026-09-04T00:00:00Z"),
        },
        now
      )
    ).toBe(false);
  });
});

describe("strategy-gate-integrity: DB gate evaluation & PMF", () => {
  it("ignores candidate evidence in gate evaluation", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const projectId = generateSnowflake();

    await db.insert(projects).values({
      id: projectId,
      workspaceId: wsId,
      title: "Test Project S1",
      lifecycleStage: "P0_DISCOVERY",
      stageVersion: 1,
    });

    const policyId = generateSnowflake();
    await db.insert(stagePolicies).values({
      id: policyId,
      workspaceId: wsId,
      stageKey: "P0_DISCOVERY",
      requirements: [{ key: "req1", minCount: 1, minStrength: 0.5 }],
      minimumEvidenceScore: 0.5,
      blockingRiskRules: [],
    });

    // Insert only CANDIDATE evidence with high strength
    await db.insert(evidence).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId,
      sourceType: "interview",
      claim: "Strong candidate claim",
      strength: 0.95,
      confidence: 1.0,
      supportsOrRefutes: "supports",
      status: "candidate", // Not approved!
    });

    const ctx: TenantContext = {
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "gate-eval-test",
    };

    const evaluation = await runGateEvaluationInWorkspace(ctx, {
      projectId: projectId.toString(),
      stagePolicyId: policyId.toString(),
    });

    // Gate must fail because candidate evidence is excluded
    expect(evaluation.requirementsMet).toBe(false);
    expect(evaluation.evidenceScore).toBe(0);
    expect(evaluation.result).toBe("failed");
  });

  it("returns INSUFFICIENT_DATA when metric contracts or eligible evidence are missing in PMF", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const projectId = generateSnowflake();

    await db.insert(projects).values({
      id: projectId,
      workspaceId: wsId,
      title: "Test Project PMF",
      lifecycleStage: "P1_PROBLEM_VALIDATION",
      stageVersion: 1,
    });

    // 1. No metric contracts at all
    const pmfNoContracts = await calculatePmfScoreboard({
      workspaceId: wsId,
      projectId,
      contractVersionIds: [],
      inputSnapshotIds: [],
      reviewedEvidenceIds: [],
    });

    expect(pmfNoContracts.result).toBe("INSUFFICIENT_DATA");
    expect(pmfNoContracts.missingDataFlags).toContain("NO_METRIC_CONTRACTS");

    // 2. Has contract and snapshot, but evidence is candidate/expired
    const contractId = generateSnowflake();
    await db.insert(metricContracts).values({
      id: contractId,
      workspaceId: wsId,
      projectId,
      metricKey: "activation_rate",
      displayName: "Activation Rate",
      unit: "RATIO",
      numeratorDefinition: "active_users",
      denominatorDefinition: "total_signups",
      cohortDefinition: "signup_month",
      cadence: "weekly",
      decisionUse: "pmf_eval",
      sourceMapping: {},
      status: "APPROVED",
      version: 1,
    });

    const snapshotId = generateSnowflake();
    await db.insert(metricSnapshots).values({
      id: snapshotId,
      workspaceId: wsId,
      projectId,
      contractVersionId: contractId,
      sourceSystem: "mixpanel",
      sourceWindow: "7d",
      sourceRecordId: "rec_1",
      payloadHash: "hash_1",
      observedAt: new Date(),
      value: 0.8,
      qualityStatus: "VALID",
    });

    const expiredEvidenceId = generateSnowflake();
    await db.insert(evidence).values({
      id: expiredEvidenceId,
      workspaceId: wsId,
      projectId,
      sourceType: "analytics",
      claim: "Expired claim",
      strength: 0.9,
      confidence: 1.0,
      supportsOrRefutes: "supports",
      status: "approved",
      freshUntil: new Date("2020-01-01T00:00:00Z"), // Expired in the past!
    });

    const pmfExpiredEvidence = await calculatePmfScoreboard({
      workspaceId: wsId,
      projectId,
      contractVersionIds: [contractId.toString()],
      inputSnapshotIds: [snapshotId.toString()],
      reviewedEvidenceIds: [expiredEvidenceId.toString()],
    });

    // Must be INSUFFICIENT_DATA because evidence expired
    expect(pmfExpiredEvidence.result).toBe("INSUFFICIENT_DATA");
    expect(pmfExpiredEvidence.missingDataFlags).toContain("NO_ELIGIBLE_EVIDENCE");
  });

  it("enforces CAS stageVersion and decision linkage on project stage transitions", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const projectIdA = generateSnowflake();
    const projectIdB = generateSnowflake();

    await db.insert(projects).values([
      {
        id: projectIdA,
        workspaceId: wsId,
        title: "Project A",
        lifecycleStage: "P0_DISCOVERY",
        stageVersion: 1,
      },
      {
        id: projectIdB,
        workspaceId: wsId,
        title: "Project B",
        lifecycleStage: "P0_DISCOVERY",
        stageVersion: 1,
      },
    ]);

    // Create decision for Project B
    const decisionBId = generateSnowflake();
    await db.insert(decisionRecords).values({
      id: decisionBId,
      workspaceId: wsId,
      projectId: projectIdB,
      decision: "proceed",
      founderDecision: "accepted",
      decidedAt: new Date(),
    });

    // 1. CAS mismatch on Project A: expected 999 but current is 1
    await expect(
      db.transaction(async (tx) => {
        await transitionProjectStageInTransaction(tx, {
          workspaceId: wsId,
          projectId: projectIdA,
          toStage: "P1_PROBLEM_VALIDATION",
          reason: "Proceed to P1",
          actorRole: "founder",
          expectedStageVersion: 999,
        });
      })
    ).rejects.toThrow(/stage_version đã thay đổi/);

    // 2. DecisionId belonging to Project B cannot be used for Project A
    await expect(
      db.transaction(async (tx) => {
        await transitionProjectStageInTransaction(tx, {
          workspaceId: wsId,
          projectId: projectIdA,
          toStage: "P1_PROBLEM_VALIDATION",
          reason: "Proceed to P1 with B's decision",
          actorRole: "founder",
          expectedStageVersion: 1,
          decisionId: decisionBId,
        });
      })
    ).rejects.toThrow(/Decision record không thuộc về project này/);

    // 3. Create valid approved decision for Project A
    const decisionAId = generateSnowflake();
    await db.insert(decisionRecords).values({
      id: decisionAId,
      workspaceId: wsId,
      projectId: projectIdA,
      decision: "proceed",
      founderDecision: "accepted",
      decidedAt: new Date(),
    });

    // Valid transition with CAS and decision
    const result = await db.transaction(async (tx) => {
      return await transitionProjectStageInTransaction(tx, {
        workspaceId: wsId,
        projectId: projectIdA,
        toStage: "P1_PROBLEM_VALIDATION",
        reason: "Proper transition with valid decision",
        actorRole: "founder",
        expectedStageVersion: 1,
        decisionId: decisionAId,
      });
    });

    expect(result.fromStage).toBe("P0_DISCOVERY");
    expect(result.toStage).toBe("P1_PROBLEM_VALIDATION");
    expect(result.stageVersion).toBe(2);

    // Check transition record has provenance
    const [tRecord] = await db
      .select()
      .from(projectStageTransitions)
      .where(eq(projectStageTransitions.projectId, projectIdA))
      .limit(1);

    expect(tRecord).toBeDefined();
    expect(tRecord.decisionId).toBe(decisionAId);
    expect(tRecord.expectedStageVersion).toBe(1);
    expect(tRecord.provenanceSnapshot).toBeDefined();
  });
});
