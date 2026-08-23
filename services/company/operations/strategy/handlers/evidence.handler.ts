import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveWorkspaceId } from "../../../shared/services/workspace-resolver.service";
import { EVIDENCE_RECORDED, makeDomainEvent } from "../../../shared/events";
import { scoreEvidence, EvidenceSourceType } from "../services/evidence-scoring.service";

const { evidence } = schema;

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
  createdAt: string;
  updatedAt: string;
}

export interface RecordEvidenceParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId: string | number;
  experimentId?: string | number;
  sourceType: EvidenceSourceType;
  claim: string;
  rawStrength?: number;
  rawConfidence?: number;
  sampleSize?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
}

export interface ListEvidenceParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId?: string | number;
  experimentId?: string | number;
}

export interface UpdateEvidenceParams {
  claim?: string;
  strength?: number;
  confidence?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
}

function toEvidence(row: typeof evidence.$inferSelect): Evidence {
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
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export const recordEvidence = api(
  { method: "POST", path: "/operations/strategy/evidence", expose: true },
  async (params: RecordEvidenceParams): Promise<Evidence> => {
    if (!params.projectId || !params.sourceType || !params.claim) {
      throw APIError.invalidArgument("projectId, sourceType, and claim are required");
    }
    const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });

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
        workspaceId,
        projectId: BigInt(params.projectId),
        experimentId: params.experimentId ? BigInt(params.experimentId) : null,
        sourceType: params.sourceType,
        claim: params.claim,
        strength: scored.strength,
        confidence: scored.confidence,
        supportsOrRefutes: params.supportsOrRefutes ?? "supports",
      })
      .returning();

    if (!row) throw APIError.internal("failed to record evidence");

    // Emit domain event
    const event = makeDomainEvent(EVIDENCE_RECORDED, {
      evidenceId: row.id.toString(),
      projectId: row.projectId.toString(),
      experimentId: row.experimentId ? row.experimentId.toString() : null,
      sourceType: row.sourceType,
      strength: row.strength,
      supportsOrRefutes: row.supportsOrRefutes,
      workspaceId: row.workspaceId.toString(),
    });
    console.log(`[DomainEvent] ${EVIDENCE_RECORDED}:`, JSON.stringify(event));

    return toEvidence(row);
  }
);

export const getEvidence = api(
  { method: "GET", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ id }: { id: string }): Promise<Evidence> => {
    const [row] = await db
      .select()
      .from(evidence)
      .where(and(eq(evidence.id, BigInt(id)), isNull(evidence.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`evidence with id ${id} not found`);
    return toEvidence(row);
  }
);

export const listEvidence = api(
  { method: "GET", path: "/operations/strategy/evidence", expose: true },
  async (params: ListEvidenceParams): Promise<{ items: Evidence[] }> => {
    const conditions = [isNull(evidence.deletedAt)];

    if (params.workspaceId || params.companyId) {
      const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });
      conditions.push(eq(evidence.workspaceId, workspaceId));
    }
    if (params.projectId) {
      conditions.push(eq(evidence.projectId, BigInt(params.projectId)));
    }
    if (params.experimentId) {
      conditions.push(eq(evidence.experimentId, BigInt(params.experimentId)));
    }

    const rows = await db
      .select()
      .from(evidence)
      .where(and(...conditions));

    return {
      items: rows.map(toEvidence),
    };
  }
);

export const updateEvidence = api(
  { method: "PATCH", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ id, ...params }: UpdateEvidenceParams & { id: string }): Promise<Evidence> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.claim !== undefined) updateValues.claim = params.claim;
    if (params.strength !== undefined) updateValues.strength = params.strength;
    if (params.confidence !== undefined) updateValues.confidence = params.confidence;
    if (params.supportsOrRefutes !== undefined) updateValues.supportsOrRefutes = params.supportsOrRefutes;

    const [row] = await db
      .update(evidence)
      .set(updateValues)
      .where(and(eq(evidence.id, BigInt(id)), isNull(evidence.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`evidence with id ${id} not found`);
    return toEvidence(row);
  }
);

export const deleteEvidence = api(
  { method: "DELETE", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(evidence)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(evidence.id, BigInt(id)), isNull(evidence.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`evidence with id ${id} not found`);
    return { success: true };
  }
);
