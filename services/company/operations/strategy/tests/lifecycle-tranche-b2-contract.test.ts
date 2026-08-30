import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import { listGateEvaluations } from "../handlers/gate-evaluation.handler";
import { listProjectStageTransitionsEndpoint } from "../handlers/project-stage.handler";
import {
  createMetricContract,
  publishMetricContractHandler,
  reviseMetricContractHandler,
  getMetricContract,
  listMetricContracts,
} from "../handlers/metric-contract.handler";
import {
  ingestMetricSnapshotHandler,
  getMetricSnapshot,
} from "../handlers/metric-snapshot.handler";
import {
  calculatePmfScoreboardHandler,
  getPmfScoreboardRun,
} from "../handlers/pmf-scoreboard.handler";
import { recordEvidence } from "../handlers/evidence.handler";
import { reviewEvidence } from "../handlers/evidence-review.handler";

// Task 8 gap-fill (Tranche B2 audit) — cross-plane real-DB contract test cho PMF
// Scoreboard / Maturity backend. Đối chiếu song song với
// tests/apps/cosa/test_lifecycle_tranche_b2_acceptance.py (Python leg) và
// frontend/test/lifecycle_tranche_b2_flow_test.dart (Flutter leg).
describe("COSA Lifecycle Tranche B2 Contract Verification (PMF & Maturity)", () => {
  it("allows two metric contract versions to coexist with only the earlier one carrying the ACTIVE approval", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Tranche B2 Versioning Project",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    const v1 = await createMetricContract({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      metricKey: "b2_versioning_metric",
      displayName: "B2 Versioning Metric",
      unit: "percentage",
      numeratorDefinition: "Numerator v1",
      denominatorDefinition: "Denominator v1",
      cohortDefinition: "Cohort v1",
      sourceMapping: { system: "amplitude", identifier: "metric_v1", aggregation: "count", window: "7d" },
      cadence: "weekly",
      ownerMemberId: ws.userId,
      decisionUse: "Test versioning coexistence",
    });

    const v1Published = await publishMetricContractHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: v1.id,
      approvalRef: "APR-B2-V1",
    });
    expect(v1Published.status).toBe("ACTIVE");
    expect(v1Published.version).toBe(1);

    const v2 = await reviseMetricContractHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: v1.id,
      cohortDefinition: "Cohort v2 narrowed",
      changeRationale: "Narrow cohort definition",
    });
    expect(v2.version).toBe(2);
    expect(v2.status).toBe("DRAFT");

    // Cả 2 version đều tồn tại và query được, nhưng chỉ v1 (đã publish) là ACTIVE.
    const list = await listMetricContracts({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
    });
    const sameMetric = list.items.filter((c) => c.metricKey === "b2_versioning_metric");
    expect(sameMetric).toHaveLength(2);
    const activeVersions = sameMetric.filter((c) => c.status === "ACTIVE");
    expect(activeVersions).toHaveLength(1);
    expect(activeVersions[0].version).toBe(1);

    const v1Reloaded = await getMetricContract({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: v1.id,
    });
    expect(v1Reloaded.status).toBe("ACTIVE");
  });

  it("prevents workspace B from resolving workspace A's metric contract, snapshot, or scoreboard run", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    const projA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Tranche B2 Tenant Isolation Project",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    const contractA = await createMetricContract({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      metricKey: "b2_isolation_metric",
      displayName: "B2 Isolation Metric",
      unit: "percentage",
      numeratorDefinition: "Numerator",
      denominatorDefinition: "Denominator",
      cohortDefinition: "Cohort",
      sourceMapping: { system: "amplitude", identifier: "metric_iso", aggregation: "count", window: "7d" },
      cadence: "weekly",
      ownerMemberId: wsA.userId,
      decisionUse: "Test tenant isolation",
    });
    await publishMetricContractHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: contractA.id,
      approvalRef: "APR-B2-ISO",
    });

    const snapshotA = await ingestMetricSnapshotHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      contractVersionId: contractA.id,
      sourceSystem: "amplitude",
      sourceWindow: "2026-W36",
      sourceRecordId: "b2_iso_rec_1",
      payloadHash: "sha256_b2_iso_1",
      observedAt: new Date().toISOString(),
      value: 0.5,
      numerator: 50,
      denominator: 100,
    });

    const evidence = await recordEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      sourceType: "customer_interview",
      claim: "Isolation test evidence",
      sampleSize: 5,
      supportsOrRefutes: "supports",
    });
    const reviewedEvidence = await reviewEvidence({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: evidence.id,
      action: "approve",
      comment: "Approved for isolation test",
    });

    const runA = await calculatePmfScoreboardHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      contractVersionIds: [contractA.id],
      inputSnapshotIds: [snapshotA.id],
      reviewedEvidenceIds: [reviewedEvidence.id],
      policyVersion: "v1",
    });

    await expect(
      getMetricContract({ authorization: wsB.bearerToken, workspaceId: wsB.workspaceId, id: contractA.id })
    ).rejects.toThrow(/not found|không tồn tại/i);

    await expect(
      getMetricSnapshot({ authorization: wsB.bearerToken, workspaceId: wsB.workspaceId, id: snapshotA.id })
    ).rejects.toThrow(/not found|không tồn tại/i);

    await expect(
      getPmfScoreboardRun({ authorization: wsB.bearerToken, workspaceId: wsB.workspaceId, id: runA.id })
    ).rejects.toThrow(/not found|không tồn tại/i);
  });

  it("is idempotent on replayed snapshot ingestion (same id) and deterministic on scoreboard recalculation (same calculationHash)", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Tranche B2 Determinism Project",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    const contract = await createMetricContract({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      metricKey: "b2_determinism_metric",
      displayName: "B2 Determinism Metric",
      unit: "percentage",
      numeratorDefinition: "Numerator",
      denominatorDefinition: "Denominator",
      cohortDefinition: "Cohort",
      sourceMapping: { system: "amplitude", identifier: "metric_det", aggregation: "count", window: "7d" },
      cadence: "weekly",
      ownerMemberId: ws.userId,
      decisionUse: "Test determinism",
    });
    await publishMetricContractHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: contract.id,
      approvalRef: "APR-B2-DET",
    });

    const snapshotPayload = {
      contractVersionId: contract.id,
      sourceSystem: "amplitude",
      sourceWindow: "2026-W37",
      sourceRecordId: "b2_det_rec_1",
      payloadHash: "sha256_b2_det_1",
      observedAt: new Date().toISOString(),
      value: 0.6,
      numerator: 60,
      denominator: 100,
    };

    const snapshot1 = await ingestMetricSnapshotHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      ...snapshotPayload,
    });

    // Replay cùng payload (idempotency key = payloadHash + sourceRecordId trong scope contract).
    const snapshotReplay = await ingestMetricSnapshotHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      ...snapshotPayload,
    });
    expect(snapshotReplay.id).toBe(snapshot1.id);

    const evidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "Determinism test evidence",
      sampleSize: 5,
      supportsOrRefutes: "supports",
    });
    const reviewedEvidence = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: evidence.id,
      action: "approve",
      comment: "Approved",
    });

    const inputs = {
      projectId: project.id,
      contractVersionIds: [contract.id],
      inputSnapshotIds: [snapshot1.id],
      reviewedEvidenceIds: [reviewedEvidence.id],
      policyVersion: "v1",
    };

    const run1 = await calculatePmfScoreboardHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      ...inputs,
    });

    const run2 = await calculatePmfScoreboardHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      ...inputs,
    });

    expect(run2.calculationHash).toBe(run1.calculationHash);
    expect(run2.result).toBe(run1.result);
  });

  it("never mutates projects.lifecycleStage or writes to the gate/stage-transition tables via any scoreboard/maturity endpoint", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Tranche B2 No-Gate-Mutation Project",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    const contract = await createMetricContract({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      metricKey: "b2_no_gate_mutation_metric",
      displayName: "B2 No Gate Mutation Metric",
      unit: "percentage",
      numeratorDefinition: "Numerator",
      denominatorDefinition: "Denominator",
      cohortDefinition: "Cohort",
      sourceMapping: { system: "amplitude", identifier: "metric_nogate", aggregation: "count", window: "7d" },
      cadence: "weekly",
      ownerMemberId: ws.userId,
      decisionUse: "Test no gate mutation",
    });
    await publishMetricContractHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: contract.id,
      approvalRef: "APR-B2-NOGATE",
    });

    const snapshot = await ingestMetricSnapshotHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      contractVersionId: contract.id,
      sourceSystem: "amplitude",
      sourceWindow: "2026-W38",
      sourceRecordId: "b2_nogate_rec_1",
      payloadHash: "sha256_b2_nogate_1",
      observedAt: new Date().toISOString(),
      value: 0.55,
      numerator: 55,
      denominator: 100,
    });

    const evidence = await recordEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      sourceType: "customer_interview",
      claim: "No gate mutation evidence",
      sampleSize: 5,
      supportsOrRefutes: "supports",
    });
    const reviewedEvidence = await reviewEvidence({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: evidence.id,
      action: "approve",
      comment: "Approved",
    });

    await calculatePmfScoreboardHandler({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      contractVersionIds: [contract.id],
      inputSnapshotIds: [snapshot.id],
      reviewedEvidenceIds: [reviewedEvidence.id],
      policyVersion: "v1",
    });

    const projAfter = await getProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(projAfter.lifecycleStage).toBe("P3_BUILD_VALIDATE");

    const gateEvals = await listGateEvaluations({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
    });
    expect(gateEvals.items).toHaveLength(0);

    const transitions = await listProjectStageTransitionsEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(transitions.transitions).toHaveLength(0);
  });
});
