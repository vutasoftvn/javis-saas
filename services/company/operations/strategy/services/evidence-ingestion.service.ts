import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db } from "../../models/db";
import { evidenceIngestions, evidence } from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { scoreEvidence, EvidenceSourceType } from "./evidence-scoring.service";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { TenantContext } from "../../../shared/types/tenant_context";

export type SourceSystem = "interview" | "crm" | "telemetry" | "payment";
export const ALLOWED_SOURCE_SYSTEMS: SourceSystem[] = ["interview", "crm", "telemetry", "payment"];

export type FactOrInference = "fact" | "inference" | "assumption";
export const ALLOWED_FACT_OR_INFERENCE: FactOrInference[] = ["fact", "inference", "assumption"];

export interface IngestClaimInput {
  claim: string;
  factOrInference?: FactOrInference;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
  strength?: number;
  confidence?: number;
  freshUntil?: string;
}

export interface IngestEvidenceSourceInput {
  projectId: string | number;
  sourceSystem: SourceSystem;
  sourceRecordId: string;
  observedAt: string;
  artifactRef?: string;
  sourceUrl?: string;
  sourcePayloadHash: string;
  claims: IngestClaimInput[];
}

export interface EvidenceIngestionReceipt {
  id: string;
  workspaceId: string;
  projectId: string;
  sourceSystem: string;
  sourceRecordId: string;
  sourcePayloadHash: string;
  artifactRef: string | null;
  sourceUrl: string | null;
  observedAt: string;
  ingestedByMemberId: string | null;
  createdAt: string;
  evidenceCount: number;
  isReplay: boolean;
}

export async function ingestEvidenceSource(
  ctx: TenantContext,
  input: IngestEvidenceSourceInput
): Promise<EvidenceIngestionReceipt> {
  if (!input.projectId || !input.sourceSystem || !input.sourceRecordId || !input.sourcePayloadHash || !input.observedAt) {
    throw APIError.invalidArgument("projectId, sourceSystem, sourceRecordId, sourcePayloadHash, and observedAt are required");
  }

  if (!ALLOWED_SOURCE_SYSTEMS.includes(input.sourceSystem)) {
    throw APIError.invalidArgument(
      `sourceSystem '${input.sourceSystem}' is not allowed. Must be one of: ${ALLOWED_SOURCE_SYSTEMS.join(", ")}`
    );
  }

  const observedDate = new Date(input.observedAt);
  if (isNaN(observedDate.getTime())) {
    throw APIError.invalidArgument("observedAt must be a valid ISO date string");
  }

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(input.projectId);

  // Validate project belongs to workspace
  await getProjectInWorkspace(input.projectId, ctx);

  return db.transaction(async (tx) => {
    // 1. Check existing receipt for idempotency
    const [existing] = await tx
      .select()
      .from(evidenceIngestions)
      .where(
        and(
          eq(evidenceIngestions.workspaceId, wsId),
          eq(evidenceIngestions.sourceSystem, input.sourceSystem),
          eq(evidenceIngestions.sourceRecordId, input.sourceRecordId),
          eq(evidenceIngestions.sourcePayloadHash, input.sourcePayloadHash)
        )
      )
      .limit(1);

    if (existing) {
      const existingEvidence = await tx
        .select({ id: evidence.id })
        .from(evidence)
        .where(eq(evidence.evidenceIngestionId, existing.id));

      return {
        id: existing.id.toString(),
        workspaceId: existing.workspaceId.toString(),
        projectId: existing.projectId.toString(),
        sourceSystem: existing.sourceSystem,
        sourceRecordId: existing.sourceRecordId,
        sourcePayloadHash: existing.sourcePayloadHash,
        artifactRef: existing.artifactRef ?? null,
        sourceUrl: existing.sourceUrl ?? null,
        observedAt: existing.observedAt.toISOString(),
        ingestedByMemberId: existing.ingestedByMemberId ? existing.ingestedByMemberId.toString() : null,
        createdAt: existing.createdAt.toISOString(),
        evidenceCount: existingEvidence.length,
        isReplay: true,
      };
    }

    // 2. Create new receipt
    const receiptId = generateSnowflake();
    const ingestedByMemberId = ctx.userId ? BigInt(ctx.userId) : null;

    const [receipt] = await tx
      .insert(evidenceIngestions)
      .values({
        id: receiptId,
        workspaceId: wsId,
        projectId: pId,
        sourceSystem: input.sourceSystem,
        sourceRecordId: input.sourceRecordId,
        sourcePayloadHash: input.sourcePayloadHash,
        artifactRef: input.artifactRef ?? null,
        sourceUrl: input.sourceUrl ?? null,
        observedAt: observedDate,
        ingestedByMemberId,
      })
      .returning();

    if (!receipt) {
      throw APIError.internal("failed to create evidence ingestion receipt");
    }

    // 3. Create candidate evidence rows for each claim
    const claims = Array.isArray(input.claims) ? input.claims : [];
    for (const c of claims) {
      if (!c.claim || !c.claim.trim()) continue;

      let mappedSourceType: EvidenceSourceType = "customer_interview";
      if (input.sourceSystem === "crm") mappedSourceType = "sales_crm";
      else if (input.sourceSystem === "telemetry") mappedSourceType = "product_telemetry";
      else if (input.sourceSystem === "payment") mappedSourceType = "financial_actuals";

      const scored = scoreEvidence({
        sourceType: mappedSourceType,
        rawStrength: c.strength,
        rawConfidence: c.confidence,
        supportsOrRefutes: c.supportsOrRefutes,
      });

      const freshUntilDate = c.freshUntil ? new Date(c.freshUntil) : null;

      await tx.insert(evidence).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: pId,
        evidenceIngestionId: receiptId,
        sourceType: mappedSourceType,
        claim: c.claim,
        strength: scored.strength,
        confidence: scored.confidence,
        supportsOrRefutes: c.supportsOrRefutes ?? "supports",
        status: "candidate", // Always candidate on ingestion
        factOrInference: c.factOrInference ?? "inference",
        artifactRef: input.artifactRef ?? null,
        sourceUrl: input.sourceUrl ?? null,
        sourceSystem: input.sourceSystem,
        observedAt: observedDate,
        freshUntil: freshUntilDate && !isNaN(freshUntilDate.getTime()) ? freshUntilDate : null,
      });
    }

    return {
      id: receipt.id.toString(),
      workspaceId: receipt.workspaceId.toString(),
      projectId: receipt.projectId.toString(),
      sourceSystem: receipt.sourceSystem,
      sourceRecordId: receipt.sourceRecordId,
      sourcePayloadHash: receipt.sourcePayloadHash,
      artifactRef: receipt.artifactRef ?? null,
      sourceUrl: receipt.sourceUrl ?? null,
      observedAt: receipt.observedAt.toISOString(),
      ingestedByMemberId: receipt.ingestedByMemberId ? receipt.ingestedByMemberId.toString() : null,
      createdAt: receipt.createdAt.toISOString(),
      evidenceCount: claims.length,
      isReplay: false,
    };
  });
}
