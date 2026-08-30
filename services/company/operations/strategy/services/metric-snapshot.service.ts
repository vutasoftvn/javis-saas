import { APIError } from "encore.dev/api";
import { and, eq, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { metricContracts, metricSnapshots, evidenceIngestions } from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

export type MetricSnapshotQuality = "VALID" | "STALE" | "INCOMPLETE" | "REJECTED";

export interface QualityChecks {
  completeness?: boolean;
  schemaMatch?: boolean;
  windowMatch?: boolean;
  identityMatch?: boolean;
  fresh?: boolean;
  reason?: string;
}

export interface IngestMetricSnapshotParams {
  workspaceId: bigint;
  contractVersionId: bigint;
  sourceSystem: string;
  sourceWindow: string;
  sourceRecordId: string;
  payloadHash: string;
  observedAt: Date;
  value: number;
  numerator?: number;
  denominator?: number;
  qualityChecks?: QualityChecks;
  evidenceIngestionId?: bigint;
  actorMemberId?: bigint;
  actorRole?: string;
}

export async function ingestMetricSnapshot(p: IngestMetricSnapshotParams) {
  // 1. Verify contract exists in workspace
  const [contract] = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.id, p.contractVersionId),
        eq(metricContracts.workspaceId, p.workspaceId),
        isNull(metricContracts.deletedAt)
      )
    )
    .limit(1);

  if (!contract) {
    throw APIError.notFound("Metric contract không tồn tại trong workspace này");
  }

  // 2. Validate denominator
  if (p.denominator !== undefined && p.denominator === 0) {
    throw APIError.invalidArgument("Denominator cannot be zero");
  }

  // 3. Verify evidenceIngestionId if provided
  if (p.evidenceIngestionId) {
    const [ingestion] = await db
      .select()
      .from(evidenceIngestions)
      .where(
        and(
          eq(evidenceIngestions.id, p.evidenceIngestionId),
          eq(evidenceIngestions.workspaceId, p.workspaceId),
          eq(evidenceIngestions.projectId, contract.projectId)
        )
      )
      .limit(1);

    if (!ingestion) {
      throw APIError.notFound("Evidence ingestion không tồn tại trong workspace hoặc project này");
    }
  }

  // 4. Idempotency check: unique by (workspaceId, contractVersionId, sourceSystem, sourceRecordId, payloadHash)
  const [existing] = await db
    .select()
    .from(metricSnapshots)
    .where(
      and(
        eq(metricSnapshots.workspaceId, p.workspaceId),
        eq(metricSnapshots.contractVersionId, p.contractVersionId),
        eq(metricSnapshots.sourceSystem, p.sourceSystem),
        eq(metricSnapshots.sourceRecordId, p.sourceRecordId),
        eq(metricSnapshots.payloadHash, p.payloadHash)
      )
    )
    .limit(1);

  if (existing) {
    return existing;
  }

  // 5. Evaluate machine quality status
  let qualityStatus: MetricSnapshotQuality = "VALID";
  const now = new Date();

  const isStale =
    (contract.freshUntil && p.observedAt > contract.freshUntil) ||
    p.observedAt.getTime() < now.getTime() - 86400000 * 90; // > 90 days old without refresh

  if (isStale) {
    qualityStatus = "STALE";
  }

  const checks: QualityChecks = {
    completeness: p.value !== undefined && !isNaN(p.value),
    schemaMatch: true,
    windowMatch: true,
    identityMatch: true,
    fresh: !isStale,
    ...(p.qualityChecks || {}),
  };

  const id = generateSnowflake();

  const [created] = await db
    .insert(metricSnapshots)
    .values({
      id,
      workspaceId: p.workspaceId,
      projectId: contract.projectId,
      contractVersionId: p.contractVersionId,
      sourceSystem: p.sourceSystem,
      sourceWindow: p.sourceWindow,
      sourceRecordId: p.sourceRecordId,
      payloadHash: p.payloadHash,
      observedAt: p.observedAt,
      capturedAt: now,
      value: p.value,
      numerator: p.numerator ?? null,
      denominator: p.denominator ?? null,
      qualityStatus,
      qualityChecks: checks,
      evidenceIngestionId: p.evidenceIngestionId ?? null,
      createdAt: now,
    })
    .returning();

  if (!created) {
    throw APIError.internal("Failed to ingest metric snapshot");
  }

  return created;
}

export async function getMetricSnapshotInWorkspace(workspaceId: bigint, snapshotId: bigint) {
  const [snapshot] = await db
    .select()
    .from(metricSnapshots)
    .where(and(eq(metricSnapshots.id, snapshotId), eq(metricSnapshots.workspaceId, workspaceId)))
    .limit(1);

  if (!snapshot) {
    throw APIError.notFound("Metric snapshot không tồn tại trong workspace này");
  }

  return snapshot;
}

export async function listMetricSnapshotsInWorkspace(
  workspaceId: bigint,
  contractVersionId?: bigint,
  projectId?: bigint
) {
  if (contractVersionId) {
    return db
      .select()
      .from(metricSnapshots)
      .where(
        and(
          eq(metricSnapshots.workspaceId, workspaceId),
          eq(metricSnapshots.contractVersionId, contractVersionId)
        )
      )
      .orderBy(metricSnapshots.observedAt);
  }

  if (projectId) {
    return db
      .select()
      .from(metricSnapshots)
      .where(
        and(
          eq(metricSnapshots.workspaceId, workspaceId),
          eq(metricSnapshots.projectId, projectId)
        )
      )
      .orderBy(metricSnapshots.observedAt);
  }

  return db
    .select()
    .from(metricSnapshots)
    .where(eq(metricSnapshots.workspaceId, workspaceId))
    .orderBy(metricSnapshots.observedAt);
}
