import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { EVIDENCE_RECORDED } from "../../../shared/events";
import { scoreEvidence, EvidenceSourceType } from "../services/evidence-scoring.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

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
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
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
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  experimentId?: string | number;
}

export interface UpdateEvidenceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
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
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    // Xác nhận project thuộc workspace này
    await getProjectInWorkspace(params.projectId, ctx);

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
      })
      .returning();

    if (!row) throw APIError.internal("failed to record evidence");

    return toEvidence(row);
  }
);

export const getEvidence = api(
  { method: "GET", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Evidence> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(evidence)
      .where(and(eq(evidence.id, BigInt(id)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Evidence not found");
    return toEvidence(row);
  }
);

export const listEvidence = api(
  { method: "GET", path: "/operations/strategy/evidence", expose: true },
  async (params: ListEvidenceParams): Promise<{ items: Evidence[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const conditions = [eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)];

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
  async (params: UpdateEvidenceParams): Promise<Evidence> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.claim !== undefined) updateValues.claim = params.claim;
    if (params.strength !== undefined) updateValues.strength = params.strength;
    if (params.confidence !== undefined) updateValues.confidence = params.confidence;
    if (params.supportsOrRefutes !== undefined) updateValues.supportsOrRefutes = params.supportsOrRefutes;

    const [row] = await db
      .update(evidence)
      .set(updateValues)
      .where(and(eq(evidence.id, BigInt(params.id)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Evidence not found");
    return toEvidence(row);
  }
);

export const deleteEvidence = api(
  { method: "DELETE", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(evidence)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(evidence.id, BigInt(id)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Evidence not found");
    return { success: true };
  }
);
