import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { DECISION_RECORDED, makeDomainEvent } from "../../../shared/events";
import { buildDecisionRecord, StrategyDecision } from "../services/decision-recording.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveWorkspaceId } from "../../../shared/services/workspace-resolver.service";

const { decisionRecords, gateEvaluations, evidence } = schema;

export interface DecisionRecord {
  id: string;
  workspaceId: string;
  projectId: string;
  gateEvaluationId: string | null;
  decision: string;
  actorMemberId: string | null;
  evidenceSnapshot: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDecisionRecordParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId: string | number;
  gateEvaluationId?: string | number;
  decision: StrategyDecision;
  actorMemberId?: string | number;
  notes?: string;
}

export interface ListDecisionRecordsParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId?: string | number;
}

function toDecisionRecord(row: typeof decisionRecords.$inferSelect): DecisionRecord {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    gateEvaluationId: row.gateEvaluationId ? row.gateEvaluationId.toString() : null,
    decision: row.decision,
    actorMemberId: row.actorMemberId ? row.actorMemberId.toString() : null,
    evidenceSnapshot: row.evidenceSnapshot as Record<string, any>,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export const createDecisionRecord = api(
  { method: "POST", path: "/operations/strategy/decision-records", expose: true },
  async (params: CreateDecisionRecordParams): Promise<DecisionRecord> => {
    if (!params.projectId || !params.decision) {
      throw APIError.invalidArgument("projectId and decision are required");
    }
    const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });

    // 1. Fetch gate evaluation if provided
    let gateEvalData: any = undefined;
    if (params.gateEvaluationId) {
      const [evalRow] = await db
        .select()
        .from(gateEvaluations)
        .where(and(eq(gateEvaluations.id, BigInt(params.gateEvaluationId)), isNull(gateEvaluations.deletedAt)))
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
      .where(and(eq(evidence.projectId, BigInt(params.projectId)), isNull(evidence.deletedAt)));

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
        workspaceId,
        projectId: BigInt(params.projectId),
        gateEvaluationId: params.gateEvaluationId ? BigInt(params.gateEvaluationId) : null,
        decision: params.decision,
        actorMemberId: params.actorMemberId ? BigInt(params.actorMemberId) : null,
        evidenceSnapshot: built.evidenceSnapshot as Record<string, any>,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create decision record");

    // 5. Emit domain event
    const event = makeDomainEvent(DECISION_RECORDED, {
      decisionRecordId: row.id.toString(),
      projectId: row.projectId.toString(),
      gateEvaluationId: row.gateEvaluationId ? row.gateEvaluationId.toString() : null,
      decision: row.decision,
      actorMemberId: row.actorMemberId ? row.actorMemberId.toString() : null,
      workspaceId: row.workspaceId.toString(),
    });
    console.log(`[DomainEvent] ${DECISION_RECORDED}:`, JSON.stringify(event));

    return toDecisionRecord(row);
  }
);

export const getDecisionRecord = api(
  { method: "GET", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ id }: { id: string }): Promise<DecisionRecord> => {
    const [row] = await db
      .select()
      .from(decisionRecords)
      .where(and(eq(decisionRecords.id, BigInt(id)), isNull(decisionRecords.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`decision record with id ${id} not found`);
    return toDecisionRecord(row);
  }
);

export const listDecisionRecords = api(
  { method: "GET", path: "/operations/strategy/decision-records", expose: true },
  async (params: ListDecisionRecordsParams): Promise<{ items: DecisionRecord[] }> => {
    const conditions = [isNull(decisionRecords.deletedAt)];

    if (params.workspaceId || params.companyId) {
      const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });
      conditions.push(eq(decisionRecords.workspaceId, workspaceId));
    }
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
);

export const deleteDecisionRecord = api(
  { method: "DELETE", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(decisionRecords)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(decisionRecords.id, BigInt(id)), isNull(decisionRecords.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`decision record with id ${id} not found`);
    return { success: true };
  }
);
