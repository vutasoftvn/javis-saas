import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import { createMetricContract, publishMetricContractHandler } from "../handlers/metric-contract.handler";
import { ingestMetricSnapshotHandler } from "../handlers/metric-snapshot.handler";
import { recordEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";
import {
  calculatePmfScoreboardHandler,
  getPmfScoreboardRun,
  listPmfScoreboardRuns,
} from "../handlers/pmf-scoreboard.handler";
import {
  assessMaturityHandler,
  getMaturityAssessment,
  listMaturityAssessments,
} from "../handlers/maturity-assessment.handler";

describe("PMF Scoreboard & Maturity Assessment (Task 3 / Tranche B2)", () => {
  it("calculates reproducible scoreboard run, handles missing and stale data, and derives maturity without gate mutation", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    // 1. Create project in Workspace A
    const projA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "PMF Test Project",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    // 2. Create and publish metric contract
    const contractA = await createMetricContract({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      metricKey: "user_retention_d30",
      displayName: "Day 30 User Retention",
      unit: "percentage",
      numeratorDefinition: "Users active on day 30",
      denominatorDefinition: "Total cohort signups",
      cohortDefinition: "Alpha Pilot Cohort",
      sourceMapping: {
        system: "amplitude",
        identifier: "retention_d30",
        aggregation: "cohort_ratio",
        window: "30d",
      },
      cadence: "monthly",
      freshUntil: new Date(Date.now() + 86400000 * 30).toISOString(),
      ownerMemberId: wsA.userId,
      decisionUse: "Evaluate PMF retention curve",
    });

    await publishMetricContractHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: contractA.id,
      approvalRef: "APR-RET-1",
    });

    // 3. Ingest high-quality metric snapshot (value: 0.72)
    const snap1 = await ingestMetricSnapshotHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      contractVersionId: contractA.id,
      sourceSystem: "amplitude",
      sourceWindow: "2026-M08",
      sourceRecordId: "amp_ret_2026_08",
      payloadHash: "sha256_amp_ret_08",
      observedAt: new Date().toISOString(),
      value: 0.72,
      numerator: 72,
      denominator: 100,
    });

    // 4. Record and approve supporting customer evidence
    const rawEv = await recordEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      sourceType: "customer_interview",
      claim: "Customer confirmed high value and willingness to renew",
      sampleSize: 10,
      rawStrength: 0.9,
      rawConfidence: 0.9,
      supportsOrRefutes: "supports",
    });

    const reviewedEv = await reviewEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: rawEv.id,
      action: "approve",
      comment: "Verified interview recording and notes",
    });

    const validInputs = {
      projectId: projA.id,
      contractVersionIds: [contractA.id],
      inputSnapshotIds: [snap1.id],
      reviewedEvidenceIds: [reviewedEv.id],
      policyVersion: "v1.2",
    };

    // 5. Calculate PMF Scoreboard with valid inputs -> PROMISING
    const run1 = await calculatePmfScoreboardHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validInputs,
    });

    expect(run1.result).toBe("PROMISING");
    expect(run1.inputSnapshotIds).toEqual([snap1.id]);
    expect(run1.missingDataFlags).toHaveLength(0);
    expect(run1.calculationHash).toBeDefined();
    expect(run1.scoreComponents.length).toBeGreaterThanOrEqual(2);

    // 6. Reproducibility: Calculating again with same inputs produces identical hash and result
    const runDuplicate = await calculatePmfScoreboardHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validInputs,
    });
    expect(runDuplicate.calculationHash).toBe(run1.calculationHash);
    expect(runDuplicate.result).toBe(run1.result);

    // 7. Calculate with empty snapshots -> INSUFFICIENT_DATA
    const runEmptySnapshots = await calculatePmfScoreboardHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validInputs,
      inputSnapshotIds: [],
    });
    expect(runEmptySnapshots.result).toBe("INSUFFICIENT_DATA");
    expect(runEmptySnapshots.missingDataFlags).toContain("NO_VALID_METRIC_SNAPSHOTS");

    // 8. Stale snapshot lowers data completeness and adds reliability flag
    const staleSnapshot = await ingestMetricSnapshotHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      contractVersionId: contractA.id,
      sourceSystem: "amplitude",
      sourceWindow: "2025-M08",
      sourceRecordId: "amp_ret_old",
      payloadHash: "sha256_amp_ret_old",
      observedAt: new Date(Date.now() - 86400000 * 150).toISOString(),
      value: 0.80,
    });

    const runWithStale = await calculatePmfScoreboardHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validInputs,
      inputSnapshotIds: [staleSnapshot.id],
    });
    expect(runWithStale.reliabilityFlags.some((f) => f.includes("STALE_SNAPSHOT"))).toBe(true);

    // 9. Derive Maturity Assessment
    const maturity = await assessMaturityHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      scoreboardRunId: run1.id,
    });
    expect(maturity.dimensions.measurement.level).toBe("GOVERNED");
    expect(maturity.dimensions.value.level).toBeDefined();
    expect(maturity.dimensions.retention.level).toBeDefined();
    expect(maturity.dimensions.commercial.level).toBeDefined();
    expect(maturity.dimensions.operational.level).toBeDefined();

    // 10. Workspace B cannot access Workspace A run or maturity
    await expect(
      getPmfScoreboardRun({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: run1.id,
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    await expect(
      getMaturityAssessment({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: maturity.id,
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    // 11. Invariant: Project lifecycle stage remains completely unchanged (never auto-transitioned)
    const projAfter = await getProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: projA.id,
    });
    expect(projAfter.lifecycleStage).toBe("P3_BUILD_VALIDATE");

    // 12. List runs and maturity assessments
    const runsList = await listPmfScoreboardRuns({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
    });
    expect(runsList.items.length).toBeGreaterThanOrEqual(3);

    const matList = await listMaturityAssessments({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
    });
    expect(matList.items.length).toBeGreaterThanOrEqual(1);
  });
});
