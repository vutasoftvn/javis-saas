import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { DECISION_RECORDED, makeDomainEvent } from "../../../shared/events";
import { buildDecisionRecord, StrategyDecision } from "../services/decision-recording.service";

const { decisionRecords, gateEvaluations, evidence } = schema;

export interface DecisionRecord {
  id: number;
  companyId: number;
  workspaceId: number;
  projectId: number;
  gateEvaluationId: number | null;
  decision: string;
  actorWorkforceMemberId: number | null;
  evidenceSnapshot: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDecisionRecordParams {
  companyId: number;
  workspaceId: number;
  projectId: number;
  gateEvaluationId?: number;
  decision: StrategyDecision;
  actorWorkforceMemberId?: number;
  notes?: string;
}

export interface ListDecisionRecordsParams {
  workspaceId?: number;
  companyId?: number;
  projectId?: number;
}

export const createDecisionRecord = api(
  { method: "POST", path: "/operations/strategy/decision-records", expose: true },
  async (params: CreateDecisionRecordParams): Promise<DecisionRecord> => {
    if (!params.workspaceId || !params.companyId || !params.projectId || !params.decision) {
      throw APIError.invalidArgument("companyId, workspaceId, projectId, and decision are required");
    }

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
      actorWorkforceMemberId: params.actorWorkforceMemberId,
      evidenceList: evidenceRows.map((e) => ({
        id: Number(e.id),
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
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        gateEvaluationId: params.gateEvaluationId ? BigInt(params.gateEvaluationId) : null,
        decision: params.decision,
        actorWorkforceMemberId: params.actorWorkforceMemberId ? BigInt(params.actorWorkforceMemberId) : null,
        evidenceSnapshot: built.evidenceSnapshot as Record<string, any>,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create decision record");

    // 5. Emit domain event
    const event = makeDomainEvent(DECISION_RECORDED, {
      decisionRecordId: Number(row.id),
      projectId: Number(row.projectId),
      gateEvaluationId: row.gateEvaluationId ? Number(row.gateEvaluationId) : null,
      decision: row.decision,
      actorWorkforceMemberId: row.actorWorkforceMemberId ? Number(row.actorWorkforceMemberId) : null,
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
    });
    console.log(`[DomainEvent] ${DECISION_RECORDED}:`, JSON.stringify(event));

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      gateEvaluationId: row.gateEvaluationId ? Number(row.gateEvaluationId) : null,
      decision: row.decision,
      actorWorkforceMemberId: row.actorWorkforceMemberId ? Number(row.actorWorkforceMemberId) : null,
      evidenceSnapshot: row.evidenceSnapshot as Record<string, any>,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getDecisionRecord = api(
  { method: "GET", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ id }: { id: number }): Promise<DecisionRecord> => {
    const [row] = await db
      .select()
      .from(decisionRecords)
      .where(and(eq(decisionRecords.id, BigInt(id)), isNull(decisionRecords.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`decision record with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      gateEvaluationId: row.gateEvaluationId ? Number(row.gateEvaluationId) : null,
      decision: row.decision,
      actorWorkforceMemberId: row.actorWorkforceMemberId ? Number(row.actorWorkforceMemberId) : null,
      evidenceSnapshot: row.evidenceSnapshot as Record<string, any>,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listDecisionRecords = api(
  { method: "GET", path: "/operations/strategy/decision-records", expose: true },
  async (params: ListDecisionRecordsParams): Promise<{ items: DecisionRecord[] }> => {
    const conditions = [isNull(decisionRecords.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(decisionRecords.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(decisionRecords.companyId, BigInt(params.companyId)));
    }
    if (params.projectId) {
      conditions.push(eq(decisionRecords.projectId, BigInt(params.projectId)));
    }

    const rows = await db
      .select()
      .from(decisionRecords)
      .where(and(...conditions));

    return {
      items: rows.map((row) => ({
        id: Number(row.id),
        companyId: Number(row.companyId),
        workspaceId: Number(row.workspaceId),
        projectId: Number(row.projectId),
        gateEvaluationId: row.gateEvaluationId ? Number(row.gateEvaluationId) : null,
        decision: row.decision,
        actorWorkforceMemberId: row.actorWorkforceMemberId ? Number(row.actorWorkforceMemberId) : null,
        evidenceSnapshot: row.evidenceSnapshot as Record<string, any>,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const deleteDecisionRecord = api(
  { method: "DELETE", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ id }: { id: number }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(decisionRecords)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(decisionRecords.id, BigInt(id)), isNull(decisionRecords.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`decision record with id ${id} not found`);
    return { success: true };
  }
);
