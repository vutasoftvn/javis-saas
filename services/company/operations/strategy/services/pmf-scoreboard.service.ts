import { APIError } from "encore.dev/api";
import { and, desc, eq, inArray, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";
import {
  metricContracts,
  metricSnapshots,
  evidence,
  pmfScoreboardRuns,
} from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { createHash } from "node:crypto";

export type PmfScoreboardResult = "INSUFFICIENT_DATA" | "MIXED" | "PROMISING" | "CONCERNING";

export interface ScoreComponent {
  componentKey: string;
  sourceType: string;
  sourceId: string;
  rawScore: number;
  weight: number;
  weightedScore: number;
  qualityStatus: string;
  notes?: string;
}

export interface CalculatePmfScoreboardParams {
  workspaceId: bigint;
  projectId: bigint;
  contractVersionIds: string[];
  inputSnapshotIds: string[];
  reviewedEvidenceIds: string[];
  policyVersion?: string;
  actorMemberId?: bigint;
  actorRole?: string;
}

export async function calculatePmfScoreboard(p: CalculatePmfScoreboardParams) {
  // 1. Verify project in workspace
  const [proj] = await db
    .select({ id: projects.id, lifecycleStage: projects.lifecycleStage })
    .from(projects)
    .where(and(eq(projects.id, p.projectId), eq(projects.workspaceId, p.workspaceId), isNull(projects.deletedAt)))
    .limit(1);

  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  const policyVersion = p.policyVersion || "v1";
  const missingDataFlags: string[] = [];
  const reliabilityFlags: string[] = [];
  const scoreComponents: ScoreComponent[] = [];

  const contractBigIntIds = (p.contractVersionIds || []).map((id) => BigInt(id));
  const snapshotBigIntIds = (p.inputSnapshotIds || []).map((id) => BigInt(id));
  const evidenceBigIntIds = (p.reviewedEvidenceIds || []).map((id) => BigInt(id));

  // 2. Fetch contracts
  const contracts =
    contractBigIntIds.length > 0
      ? await db
          .select()
          .from(metricContracts)
          .where(
            and(
              eq(metricContracts.workspaceId, p.workspaceId),
              eq(metricContracts.projectId, p.projectId),
              inArray(metricContracts.id, contractBigIntIds),
              isNull(metricContracts.deletedAt)
            )
          )
      : [];

  if (contracts.length === 0) {
    missingDataFlags.push("NO_METRIC_CONTRACTS");
  }

  // 3. Fetch snapshots
  const snapshots =
    snapshotBigIntIds.length > 0
      ? await db
          .select()
          .from(metricSnapshots)
          .where(
            and(
              eq(metricSnapshots.workspaceId, p.workspaceId),
              eq(metricSnapshots.projectId, p.projectId),
              inArray(metricSnapshots.id, snapshotBigIntIds)
            )
          )
      : [];

  if (snapshots.length === 0) {
    missingDataFlags.push("NO_VALID_METRIC_SNAPSHOTS");
  }

  // 4. Fetch reviewed evidence
  const reviewedEvidenceList =
    evidenceBigIntIds.length > 0
      ? await db
          .select()
          .from(evidence)
          .where(
            and(
              eq(evidence.workspaceId, p.workspaceId),
              eq(evidence.projectId, p.projectId),
              inArray(evidence.id, evidenceBigIntIds),
              isNull(evidence.deletedAt)
            )
          )
      : [];

  if (reviewedEvidenceList.length === 0) {
    missingDataFlags.push("NO_REVIEWED_EVIDENCE");
  }

  // Check evidence reviews
  const unreviewedEvidence = reviewedEvidenceList.filter((e) => e.status !== "approved");
  if (unreviewedEvidence.length > 0) {
    reliabilityFlags.push(`UNREVIEWED_EVIDENCE_EXCLUDED:${unreviewedEvidence.length}`);
  }

  const validEvidence = reviewedEvidenceList.filter((e) => e.status === "approved");

  // 5. Evaluate snapshots & compute components
  let totalWeightedScore = 0;
  let totalWeight = 0;

  for (const snap of snapshots) {
    if (snap.qualityStatus === "STALE") {
      reliabilityFlags.push(`STALE_SNAPSHOT:${snap.id}`);
    }

    const weight = 1.0;
    let score = Math.max(0, Math.min(1.0, snap.value));
    if (snap.qualityStatus === "STALE") {
      score *= 0.75; // Stale penalty
    }

    const weightedScore = score * weight;
    totalWeightedScore += weightedScore;
    totalWeight += weight;

    scoreComponents.push({
      componentKey: `snapshot_${snap.contractVersionId}`,
      sourceType: "metric_snapshot",
      sourceId: snap.id.toString(),
      rawScore: snap.value,
      weight,
      weightedScore,
      qualityStatus: snap.qualityStatus,
    });
  }

  // Evaluate qualitative evidence components
  for (const ev of validEvidence) {
    const weight = 0.5;
    const isSupport = ev.supportsOrRefutes === "supports";
    const score = isSupport ? ev.strength * ev.confidence : 0;
    const weightedScore = score * weight;

    totalWeightedScore += weightedScore;
    totalWeight += weight;

    scoreComponents.push({
      componentKey: `evidence_${ev.id}`,
      sourceType: "reviewed_evidence",
      sourceId: ev.id.toString(),
      rawScore: score,
      weight,
      weightedScore,
      qualityStatus: "APPROVED",
      notes: ev.claim,
    });
  }

  // 6. Determine classification
  let result: PmfScoreboardResult = "INSUFFICIENT_DATA";

  if (snapshots.length === 0 || totalWeight === 0) {
    result = "INSUFFICIENT_DATA";
  } else {
    const compositeScore = totalWeightedScore / totalWeight;
    const refutingCount = validEvidence.filter((e) => e.supportsOrRefutes === "refutes").length;

    if (compositeScore >= 0.6 && refutingCount === 0 && missingDataFlags.length === 0) {
      result = "PROMISING";
    } else if (compositeScore < 0.35 || refutingCount > validEvidence.length / 2) {
      result = "CONCERNING";
    } else {
      result = "MIXED";
    }
  }

  // 7. Calculate deterministic hash of calculation inputs
  const sortedContractIds = [...p.contractVersionIds].sort();
  const sortedSnapshotIds = [...p.inputSnapshotIds].sort();
  const sortedEvidenceIds = [...p.reviewedEvidenceIds].sort();

  const hashPayload = {
    projectId: p.projectId.toString(),
    contractVersionIds: sortedContractIds,
    inputSnapshotIds: sortedSnapshotIds,
    reviewedEvidenceIds: sortedEvidenceIds,
    policyVersion,
    scoreComponents: scoreComponents.map((c) => ({
      key: c.componentKey,
      raw: c.rawScore,
      quality: c.qualityStatus,
    })),
    result,
  };

  const calculationHash = createHash("sha256").update(JSON.stringify(hashPayload)).digest("hex");
  const now = new Date();
  const id = generateSnowflake();

  const [run] = await db
    .insert(pmfScoreboardRuns)
    .values({
      id,
      workspaceId: p.workspaceId,
      projectId: p.projectId,
      contractVersionIds: sortedContractIds,
      inputSnapshotIds: sortedSnapshotIds,
      reviewedEvidenceIds: sortedEvidenceIds,
      policyVersion,
      scoreComponents,
      missingDataFlags,
      reliabilityFlags,
      calculationHash,
      result,
      humanReviewState: {},
      calculatedAt: now,
      createdAt: now,
    })
    .returning();

  if (!run) {
    throw APIError.internal("Failed to save PMF scoreboard run");
  }

  return run;
}

export async function getPmfScoreboardRunInWorkspace(workspaceId: bigint, runId: bigint) {
  const [run] = await db
    .select()
    .from(pmfScoreboardRuns)
    .where(and(eq(pmfScoreboardRuns.id, runId), eq(pmfScoreboardRuns.workspaceId, workspaceId)))
    .limit(1);

  if (!run) {
    throw APIError.notFound("PMF scoreboard run không tồn tại trong workspace này");
  }

  return run;
}

export async function listPmfScoreboardRunsInWorkspace(workspaceId: bigint, projectId?: bigint) {
  if (projectId) {
    return db
      .select()
      .from(pmfScoreboardRuns)
      .where(
        and(
          eq(pmfScoreboardRuns.workspaceId, workspaceId),
          eq(pmfScoreboardRuns.projectId, projectId)
        )
      )
      .orderBy(desc(pmfScoreboardRuns.calculatedAt));
  }

  return db
    .select()
    .from(pmfScoreboardRuns)
    .where(eq(pmfScoreboardRuns.workspaceId, workspaceId))
    .orderBy(desc(pmfScoreboardRuns.calculatedAt));
}
