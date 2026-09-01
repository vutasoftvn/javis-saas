import { APIError } from "encore.dev/api";
import { eq, and, isNull, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { scoreEvidence, EvidenceSourceType } from "./evidence-scoring.service";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { assertLifecyclePrivileged } from "./lifecycle-authorization.service";
import { assertNotAcademyReference, assertNotAcademyTemplateDraft } from "../../../academy/contracts";
import { EvidenceIngestionReceipt } from "./evidence-ingestion.service";

const { evidence, evidenceIngestions } = schema;

export interface Evidence {
  id: string;
  workspaceId: string;
  projectId: string;
  experimentId: string | null;
  sourceType: string;
  claim: string;
  strength: number;
  confidence: number;
  supportsOrRefutes: string;
  status: string;
  reviewComment?: string | null;
  reviewedByMemberId?: string | null;
  reviewedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface RecordEvidenceInput {
  projectId: string | number;
  experimentId?: string | number;
  sourceType: EvidenceSourceType;
  claim: string;
  rawStrength?: number;
  rawConfidence?: number;
  sampleSize?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
  status?: "candidate" | "approved";
  artifactRef?: string;
  artifactKind?: string;
  sourceRecordId?: string;
}

export interface ListEvidenceInput {
  projectId?: string | number;
  experimentId?: string | number;
  status?: string;
}

export interface UpdateEvidenceInput {
  claim?: string;
  strength?: number;
  confidence?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
}

export function toEvidence(row: typeof evidence.$inferSelect): Evidence {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    experimentId: row.experimentId ? row.experimentId.toString() : null,
    sourceType: row.sourceType,
    claim: row.claim,
    strength: row.strength,
    confidence: row.confidence,
    supportsOrRefutes: row.supportsOrRefutes,
    status: row.status,
    reviewComment: row.reviewComment ?? null,
    reviewedByMemberId: row.reviewedByMemberId ? row.reviewedByMemberId.toString() : null,
    reviewedAt: row.reviewedAt ? row.reviewedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function recordEvidenceInWorkspace(
  ctx: TenantContext,
  params: RecordEvidenceInput
): Promise<Evidence> {
  if (!params.projectId || !params.sourceType || !params.claim) {
    throw APIError.invalidArgument("projectId, sourceType, and claim are required");
  }
  const wsId = BigInt(ctx.workspaceId);

  // Academy firewall: reject synthetic/academy artifact refs before any persistence
  assertNotAcademyReference(params.artifactRef, "artifactRef");
  assertNotAcademyReference(params.sourceRecordId, "sourceRecordId");
  assertNotAcademyTemplateDraft(params.artifactKind, "artifactKind");

  // Xác nhận project thuộc workspace này
  await getProjectInWorkspace(params.projectId, ctx);

  if (params.status && params.status !== "candidate") {
    throw APIError.invalidArgument("Evidence can only be created as 'candidate'; approval requires privileged review");
  }

  // Auto-score evidence deterministically based on source type and sample size
  const scored = scoreEvidence({
    sourceType: params.sourceType,
    rawStrength: params.rawStrength,
    rawConfidence: params.rawConfidence,
    sampleSize: params.sampleSize,
    supportsOrRefutes: params.supportsOrRefutes,
  });

  const [row] = await db
    .insert(evidence)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      experimentId: params.experimentId ? BigInt(params.experimentId) : null,
      sourceType: params.sourceType,
      claim: params.claim,
      strength: scored.strength,
      confidence: scored.confidence,
      supportsOrRefutes: params.supportsOrRefutes ?? "supports",
      status: "candidate",
      reviewedByMemberId: null,
      reviewedAt: null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to record evidence");
  return toEvidence(row);
}

export async function getEvidenceInWorkspace(
  ctx: TenantContext,
  evidenceId: string | number
): Promise<Evidence> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(evidence)
    .where(and(eq(evidence.id, BigInt(evidenceId)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Evidence not found");
  return toEvidence(row);
}

export async function listEvidenceInWorkspace(
  ctx: TenantContext,
  params: ListEvidenceInput
): Promise<{ items: Evidence[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)];

  if (params.projectId) {
    conditions.push(eq(evidence.projectId, BigInt(params.projectId)));
  }
  if (params.experimentId) {
    conditions.push(eq(evidence.experimentId, BigInt(params.experimentId)));
  }
  if (params.status) {
    conditions.push(eq(evidence.status, params.status));
  }

  const rows = await db
    .select()
    .from(evidence)
    .where(and(...conditions));

  return {
    items: rows.map(toEvidence),
  };
}

export async function updateEvidenceInWorkspace(
  ctx: TenantContext,
  evidenceId: string | number,
  params: UpdateEvidenceInput
): Promise<Evidence> {
  const wsId = BigInt(ctx.workspaceId);

  // Fetch existing record to verify review state
  const [existing] = await db
    .select()
    .from(evidence)
    .where(and(eq(evidence.id, BigInt(evidenceId)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
    .limit(1);

  if (!existing) throw APIError.notFound("Evidence not found");

  if (existing.status === "approved" || existing.status === "reviewed") {
    assertLifecyclePrivileged(ctx.membershipRole, "updateApprovedEvidence");
  }

  const updateValues: Record<string, any> = { updatedAt: new Date() };
  if (params.claim !== undefined) updateValues.claim = params.claim;
  if (params.strength !== undefined) updateValues.strength = params.strength;
  if (params.confidence !== undefined) updateValues.confidence = params.confidence;
  if (params.supportsOrRefutes !== undefined) updateValues.supportsOrRefutes = params.supportsOrRefutes;

  const [row] = await db
    .update(evidence)
    .set(updateValues)
    .where(and(eq(evidence.id, BigInt(evidenceId)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Evidence not found");
  return toEvidence(row);
}

export async function deleteEvidenceInWorkspace(
  ctx: TenantContext,
  evidenceId: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .update(evidence)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(evidence.id, BigInt(evidenceId)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Evidence not found");
  return { success: true };
}

export async function listEvidenceIngestionsInWorkspace(
  ctx: TenantContext,
  params: { projectId?: string | number }
): Promise<{ items: EvidenceIngestionReceipt[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(evidenceIngestions.workspaceId, wsId)];
  if (params.projectId) {
    conditions.push(eq(evidenceIngestions.projectId, BigInt(params.projectId)));
  }

  const rows = await db
    .select()
    .from(evidenceIngestions)
    .where(and(...conditions))
    .orderBy(desc(evidenceIngestions.createdAt));

  const items: EvidenceIngestionReceipt[] = [];
  for (const r of rows) {
    const evCount = await db
      .select({ id: evidence.id })
      .from(evidence)
      .where(eq(evidence.evidenceIngestionId, r.id));

    items.push({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      projectId: r.projectId.toString(),
      sourceSystem: r.sourceSystem,
      sourceRecordId: r.sourceRecordId,
      sourcePayloadHash: r.sourcePayloadHash,
      artifactRef: r.artifactRef ?? null,
      sourceUrl: r.sourceUrl ?? null,
      observedAt: r.observedAt.toISOString(),
      ingestedByMemberId: r.ingestedByMemberId ? r.ingestedByMemberId.toString() : null,
      createdAt: r.createdAt.toISOString(),
      evidenceCount: evCount.length,
      isReplay: false,
    });
  }

  return { items };
}
