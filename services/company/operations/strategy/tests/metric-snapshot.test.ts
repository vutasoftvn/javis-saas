import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import { createMetricContract, publishMetricContractHandler } from "../handlers/metric-contract.handler";
import {
  ingestMetricSnapshotHandler,
  getMetricSnapshot,
  listMetricSnapshots,
} from "../handlers/metric-snapshot.handler";

describe("Metric Snapshot Aggregate & Ingestion (Task 2 / Tranche B2)", () => {
  it("validates telemetry quality, enforces idempotency, rejects zero denominator, and respects workspace boundary", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    // 1. Create project and published metric contract in Workspace A
    const projA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Telemetry Project A",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    const contractA = await createMetricContract({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
      metricKey: "pilot_activation_rate",
      displayName: "Pilot Activation Rate",
      unit: "percentage",
      numeratorDefinition: "Users activated",
      denominatorDefinition: "Total pilot cohort users",
      cohortDefinition: "Cohort Alpha",
      sourceMapping: {
        system: "posthog",
        identifier: "user_activated",
        aggregation: "count_distinct",
        window: "14d",
      },
      cadence: "weekly",
      freshUntil: new Date(Date.now() + 86400000 * 7).toISOString(),
      ownerMemberId: wsA.userId,
      decisionUse: "Validate activation baseline",
    });

    await publishMetricContractHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: contractA.id,
      approvalRef: "APR-ACT-1",
    });

    const validSnapshotPayload = {
      contractVersionId: contractA.id,
      sourceSystem: "posthog",
      sourceWindow: "2026-W35",
      sourceRecordId: "rec_agg_2026_w35_cohort_a",
      payloadHash: "sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      observedAt: new Date().toISOString(),
      value: 0.65,
      numerator: 13,
      denominator: 20,
      qualityChecks: {
        completeness: true,
        schemaMatch: true,
        windowMatch: true,
      },
    };

    // 2. Ingest valid telemetry snapshot -> VALID
    const snapshot1 = await ingestMetricSnapshotHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validSnapshotPayload,
    });
    expect(snapshot1.qualityStatus).toBe("VALID");
    expect(snapshot1.value).toBe(0.65);
    expect(snapshot1.numerator).toBe(13);
    expect(snapshot1.denominator).toBe(20);

    // 3. Idempotency: Ingesting exact same payload returns same snapshot ID
    const snapshotDuplicate = await ingestMetricSnapshotHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validSnapshotPayload,
    });
    expect(snapshotDuplicate.id).toBe(snapshot1.id);

    // 4. Reject zero denominator
    await expect(
      ingestMetricSnapshotHandler({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        ...validSnapshotPayload,
        sourceRecordId: "rec_zero_denom",
        payloadHash: "sha256_zero_denom",
        denominator: 0,
      })
    ).rejects.toThrow(/denominator/i);

    // 5. Ingesting stale telemetry snapshot marks STALE quality
    const staleDate = new Date(Date.now() - 86400000 * 120).toISOString(); // 120 days ago
    const staleSnapshot = await ingestMetricSnapshotHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validSnapshotPayload,
      sourceRecordId: "rec_stale_record",
      payloadHash: "sha256_stale_hash",
      observedAt: staleDate,
    });
    expect(staleSnapshot.qualityStatus).toBe("STALE");

    // 6. Cross-workspace isolation: Workspace B cannot ingest snapshot referencing Contract in Workspace A
    await expect(
      ingestMetricSnapshotHandler({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        ...validSnapshotPayload,
        sourceRecordId: "rec_cross_ws",
        payloadHash: "sha256_cross_ws",
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    // 7. Workspace B cannot get snapshot from Workspace A
    await expect(
      getMetricSnapshot({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: snapshot1.id,
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    // 8. Invariant: Project stage remains unchanged
    const projAfter = await getProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: projA.id,
    });
    expect(projAfter.lifecycleStage).toBe("P3_BUILD_VALIDATE");

    // 9. List snapshots
    const list = await listMetricSnapshots({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      contractVersionId: contractA.id,
    });
    expect(list.items.length).toBe(2); // snapshot1 and staleSnapshot
  });
});
