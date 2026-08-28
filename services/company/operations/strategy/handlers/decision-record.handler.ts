import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { DECISION_RECORDED } from "../../../shared/events";
import { buildDecisionRecord, StrategyDecision } from "../services/decision-recording.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

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
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  gateEvaluationId?: string | number;
  decision: StrategyDecision;
  actorMemberId?: string | number;
  notes?: string;
}

export interface ListDecisionRecordsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
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
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const getDecisionRecord = api(
  { method: "GET", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<DecisionRecord> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(decisionRecords)
      .where(and(eq(decisionRecords.id, BigInt(id)), eq(decisionRecords.workspaceId, wsId), isNull(decisionRecords.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Decision record not found");
    return toDecisionRecord(row);
  }
);

export const listDecisionRecords = api(
  { method: "GET", path: "/operations/strategy/decision-records", expose: true },
  async (params: ListDecisionRecordsParams): Promise<{ items: DecisionRecord[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const deleteDecisionRecord = api(
  { method: "DELETE", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(decisionRecords)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(decisionRecords.id, BigInt(id)), eq(decisionRecords.workspaceId, wsId), isNull(decisionRecords.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Decision record not found");
    return { success: true };
  }
);
