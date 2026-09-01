import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { EvidenceItem, GateEvaluationOutput } from "./gate-evaluation.service";

const { decisionRecords, gateEvaluations, evidence } = schema;

export type StrategyDecision = "proceed" | "pivot" | "kill" | "hold";

export interface DecisionRecord {
  id: string;
  workspaceId: string;
  projectId: string | null;
  gateEvaluationId: string | null;
  decision: string;
  actorMemberId: string | null;
  evidenceSnapshot: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDecisionRecordInput {
  projectId?: string | number;
  gateEvaluationId?: string | number;
  decision: StrategyDecision;
  actorMemberId?: string | number;
  notes?: string;
}

export interface ListDecisionRecordsInput {
  projectId?: string | number;
}

export interface RecordDecisionInput {
  projectId: number | bigint | string;
  gateEvaluationId?: number | bigint | string | null;
  gateEvaluation?: GateEvaluationOutput;
  decision: StrategyDecision;
  actorMemberId?: number | bigint | string | null;
  evidenceList: EvidenceItem[];
  notes?: string;
}

export interface EvidenceSnapshot {
  evaluatedAt: string;
  totalEvidenceCount: number;
  supportingCount: number;
  refutingCount: number;
  averageStrength: number;
  items: Array<{
    id?: number | bigint | string;
    sourceType: string;
    strength: number;
    confidence: number;
    supportsOrRefutes: string;
  }>;
  gateEvaluationSummary?: {
    requirementsMet: boolean;
    evidenceScore: number;
    result: string;
    rationale: string;
  };
  decisionNotes?: string;
}

export interface DecisionRecordPayload {
  projectId: number | bigint | string;
  gateEvaluationId?: number | bigint | string | null;
  decision: StrategyDecision;
  actorMemberId?: number | bigint | string | null;
  evidenceSnapshot: EvidenceSnapshot;
  createdAt: string;
}

/**
 * Đóng gói bản ghi quyết định chiến lược và snapshot evidence tại thời điểm quyết định.
 * Hàm thuần tất định, không gọi LLM.
 */
export function buildDecisionRecord(input: RecordDecisionInput): DecisionRecordPayload {
  const {
    projectId,
    gateEvaluationId,
    gateEvaluation,
    decision,
    actorMemberId,
    evidenceList,
    notes,
  } = input;

  const supporting = evidenceList.filter((e) => e.supportsOrRefutes === "supports");
  const refuting = evidenceList.filter((e) => e.supportsOrRefutes === "refutes");

  const avgStrength = evidenceList.length > 0
    ? Math.round((evidenceList.reduce((acc, curr) => acc + curr.strength, 0) / evidenceList.length) * 10000) / 10000
    : 0;

  const evidenceSnapshot: EvidenceSnapshot = {
    evaluatedAt: new Date().toISOString(),
    totalEvidenceCount: evidenceList.length,
    supportingCount: supporting.length,
    refutingCount: refuting.length,
    averageStrength: avgStrength,
    items: evidenceList.map((e) => ({
      id: e.id,
      sourceType: e.sourceType,
      strength: e.strength,
      confidence: e.confidence,
      supportsOrRefutes: e.supportsOrRefutes,
    })),
    gateEvaluationSummary: gateEvaluation ? {
      requirementsMet: gateEvaluation.requirementsMet,
      evidenceScore: gateEvaluation.evidenceScore,
      result: gateEvaluation.result,
      rationale: gateEvaluation.rationale,
    } : undefined,
    decisionNotes: notes,
  };

  return {
    projectId,
    gateEvaluationId: gateEvaluationId ?? null,
    decision,
    actorMemberId: actorMemberId ?? null,
    evidenceSnapshot,
    createdAt: new Date().toISOString(),
  };
}

export function toDecisionRecord(row: typeof decisionRecords.$inferSelect): DecisionRecord {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId ? row.projectId.toString() : null,
    gateEvaluationId: row.gateEvaluationId ? row.gateEvaluationId.toString() : null,
    decision: row.decision,
    actorMemberId: row.actorMemberId ? row.actorMemberId.toString() : null,
    evidenceSnapshot: row.evidenceSnapshot as Record<string, any>,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createDecisionRecordInWorkspace(
  ctx: TenantContext,
  params: CreateDecisionRecordInput
): Promise<DecisionRecord> {
  if (!params.projectId || !params.decision) {
    throw APIError.invalidArgument("projectId and decision are required");
  }
  const wsId = BigInt(ctx.workspaceId);

  // Verify project belongs to workspace
  await getProjectInWorkspace(params.projectId, ctx);

  // 1. Fetch gate evaluation if provided
  let gateEvalData: any = undefined;
  if (params.gateEvaluationId) {
    const [evalRow] = await db
      .select()
      .from(gateEvaluations)
      .where(and(eq(gateEvaluations.id, BigInt(params.gateEvaluationId)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
      .limit(1);

    if (evalRow) {
      gateEvalData = {
        requirementsMet: evalRow.requirementsMet,
        evidenceScore: evalRow.evidenceScore,
        result: evalRow.result,
        rationale: evalRow.rationale,
      };
    }
  }

  // 2. Fetch current project evidence for snapshot
  const evidenceRows = await db
    .select()
    .from(evidence)
    .where(and(eq(evidence.projectId, BigInt(params.projectId)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)));

  // 3. Build snapshot deterministically
  const built = buildDecisionRecord({
    projectId: params.projectId,
    gateEvaluationId: params.gateEvaluationId,
    gateEvaluation: gateEvalData,
    decision: params.decision,
    actorMemberId: params.actorMemberId,
    evidenceList: evidenceRows.map((e) => ({
      id: e.id.toString(),
      sourceType: e.sourceType,
      strength: e.strength,
      confidence: e.confidence,
      supportsOrRefutes: e.supportsOrRefutes,
    })),
    notes: params.notes,
  });

  // 4. Save record
  const [row] = await db
    .insert(decisionRecords)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      gateEvaluationId: params.gateEvaluationId ? BigInt(params.gateEvaluationId) : null,
      decision: params.decision,
      actorMemberId: params.actorMemberId ? BigInt(params.actorMemberId) : null,
      evidenceSnapshot: built.evidenceSnapshot as Record<string, any>,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create decision record");
  return toDecisionRecord(row);
}

export async function getDecisionRecordInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<DecisionRecord> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(decisionRecords)
    .where(and(eq(decisionRecords.id, BigInt(id)), eq(decisionRecords.workspaceId, wsId), isNull(decisionRecords.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Decision record not found");
  return toDecisionRecord(row);
}

export async function listDecisionRecordsInWorkspace(
  ctx: TenantContext,
  params: ListDecisionRecordsInput
): Promise<{ items: DecisionRecord[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(decisionRecords.workspaceId, wsId), isNull(decisionRecords.deletedAt)];

  if (params.projectId) {
    conditions.push(eq(decisionRecords.projectId, BigInt(params.projectId)));
  }

  const rows = await db
    .select()
    .from(decisionRecords)
    .where(and(...conditions));

  return {
    items: rows.map(toDecisionRecord),
  };
}

export async function deleteDecisionRecordInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .update(decisionRecords)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(decisionRecords.id, BigInt(id)), eq(decisionRecords.workspaceId, wsId), isNull(decisionRecords.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Decision record not found");
  return { success: true };
}
