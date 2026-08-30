import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { evaluateGate, BlockingRiskItem } from "../services/gate-evaluation.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const { gateEvaluations, stagePolicies, evidence } = schema;

export interface GateEvaluation {
  id: string;
  workspaceId: string;
  projectId: string;
  stagePolicyId: string | null;
  requirementsMet: boolean;
  evidenceScore: number;
  blockingRisks: any[];
  result: string;
  rationale: string;
  humanOverride: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RunGateEvaluationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  stagePolicyId: string | number;
  blockingRisks?: BlockingRiskItem[];
}

export interface ListGateEvaluationsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
}

function toGateEvaluation(row: typeof gateEvaluations.$inferSelect): GateEvaluation {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    stagePolicyId: row.stagePolicyId ? row.stagePolicyId.toString() : null,
    requirementsMet: row.requirementsMet,
    evidenceScore: row.evidenceScore,
    blockingRisks: row.blockingRisks as any[],
    result: row.result,
    rationale: row.rationale,
    humanOverride: row.humanOverride,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export const runGateEvaluation = api(
  { method: "POST", path: "/operations/strategy/gate-evaluations", expose: true },
  async (params: RunGateEvaluationParams): Promise<GateEvaluation> => {
    if (!params.projectId || !params.stagePolicyId) {
      throw APIError.invalidArgument("projectId and stagePolicyId are required");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    // Xác nhận project thuộc workspace này
    await getProjectInWorkspace(params.projectId, ctx);

    // 1. Fetch stage policy from workspace
    const [policyRow] = await db
      .select()
      .from(stagePolicies)
      .where(and(eq(stagePolicies.id, BigInt(params.stagePolicyId)), eq(stagePolicies.workspaceId, wsId), isNull(stagePolicies.deletedAt)))
      .limit(1);

    if (!policyRow) throw APIError.notFound("Stage policy not found");

    // 2. Fetch project evidence from workspace
    const evidenceRows = await db
      .select()
      .from(evidence)
      .where(and(eq(evidence.projectId, BigInt(params.projectId)), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)));

    // 3. Evaluate deterministically without LLM - recommendation only
    const evaluation = evaluateGate({
      policy: {
        id: policyRow.id.toString(),
        stageKey: policyRow.stageKey,
        minimumEvidenceScore: policyRow.minimumEvidenceScore,
        requirements: policyRow.requirements as any[],
        blockingRiskRules: policyRow.blockingRiskRules as any[],
      },
      evidenceList: evidenceRows.map((e) => ({
        id: e.id.toString(),
        sourceType: e.sourceType,
        strength: e.strength,
        confidence: e.confidence,
        supportsOrRefutes: e.supportsOrRefutes,
      })),
      blockingRisks: params.blockingRisks,
      humanOverride: false,
    });

    // 4. Save evaluation record (recommendation-only: never alters project stage or writes outbox)
    const [saved] = await db
      .insert(gateEvaluations)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: BigInt(params.projectId),
        stagePolicyId: BigInt(params.stagePolicyId),
        requirementsMet: evaluation.requirementsMet,
        evidenceScore: evaluation.evidenceScore,
        blockingRisks: evaluation.blockingRisks as any[],
        result: evaluation.result,
        rationale: evaluation.rationale,
        humanOverride: false,
      })
      .returning();

    if (!saved) throw APIError.internal("failed to save gate evaluation");

    return toGateEvaluation(saved);
  }
);

export const getGateEvaluation = api(
  { method: "GET", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<GateEvaluation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(gateEvaluations)
      .where(and(eq(gateEvaluations.id, BigInt(id)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Gate evaluation not found");
    return toGateEvaluation(row);
  }
);

export const listGateEvaluations = api(
  { method: "GET", path: "/operations/strategy/gate-evaluations", expose: true },
  async (params: ListGateEvaluationsParams): Promise<{ items: GateEvaluation[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const conditions = [eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)];

    if (params.projectId) {
      conditions.push(eq(gateEvaluations.projectId, BigInt(params.projectId)));
    }

    const rows = await db
      .select()
      .from(gateEvaluations)
      .where(and(...conditions));

    return {
      items: rows.map(toGateEvaluation),
    };
  }
);

export const updateGateEvaluation = api(
  { method: "PATCH", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ authorization, workspaceId, id, humanOverride, rationale }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string; humanOverride?: boolean; rationale?: string }): Promise<GateEvaluation> => {
    if (humanOverride !== undefined) {
      throw APIError.invalidArgument("Gate evaluation cannot be overridden directly; use stage transition endpoint with approval");
    }

    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (rationale !== undefined) updateValues.rationale = rationale;

    const [row] = await db
      .update(gateEvaluations)
      .set(updateValues)
      .where(and(eq(gateEvaluations.id, BigInt(id)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Gate evaluation not found");
    return toGateEvaluation(row);
  }
);

export const deleteGateEvaluation = api(
  { method: "DELETE", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(gateEvaluations)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(gateEvaluations.id, BigInt(id)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Gate evaluation not found");
    return { success: true };
  }
);

