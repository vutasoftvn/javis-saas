import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { GATE_EVALUATED, makeDomainEvent } from "../../../shared/events";
import { evaluateGate, BlockingRiskItem } from "../services/gate-evaluation.service";

const { gateEvaluations, stagePolicies, evidence } = schema;

export interface GateEvaluation {
  id: number;
  companyId: number;
  workspaceId: number;
  projectId: number;
  stagePolicyId: number | null;
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
  companyId: number;
  workspaceId: number;
  projectId: number;
  stagePolicyId: number;
  blockingRisks?: BlockingRiskItem[];
  humanOverride?: boolean;
}

export interface ListGateEvaluationsParams {
  workspaceId?: number;
  companyId?: number;
  projectId?: number;
}

export const runGateEvaluation = api(
  { method: "POST", path: "/operations/strategy/gate-evaluations", expose: true },
  async (params: RunGateEvaluationParams): Promise<GateEvaluation> => {
    if (!params.workspaceId || !params.companyId || !params.projectId || !params.stagePolicyId) {
      throw APIError.invalidArgument("companyId, workspaceId, projectId, and stagePolicyId are required");
    }

    // 1. Fetch stage policy
    const [policyRow] = await db
      .select()
      .from(stagePolicies)
      .where(and(eq(stagePolicies.id, BigInt(params.stagePolicyId)), isNull(stagePolicies.deletedAt)))
      .limit(1);

    if (!policyRow) throw APIError.notFound(`stage policy with id ${params.stagePolicyId} not found`);

    // 2. Fetch project evidence
    const evidenceRows = await db
      .select()
      .from(evidence)
      .where(and(eq(evidence.projectId, BigInt(params.projectId)), isNull(evidence.deletedAt)));

    // 3. Evaluate deterministically without LLM
    const evaluation = evaluateGate({
      policy: {
        id: Number(policyRow.id),
        stageKey: policyRow.stageKey,
        minimumEvidenceScore: policyRow.minimumEvidenceScore,
        requirements: policyRow.requirements as any[],
        blockingRiskRules: policyRow.blockingRiskRules as any[],
      },
      evidenceList: evidenceRows.map((e) => ({
        id: Number(e.id),
        sourceType: e.sourceType,
        strength: e.strength,
        confidence: e.confidence,
        supportsOrRefutes: e.supportsOrRefutes,
      })),
      blockingRisks: params.blockingRisks,
      humanOverride: params.humanOverride,
    });

    // 4. Save evaluation record
    const [row] = await db
      .insert(gateEvaluations)
      .values({
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        stagePolicyId: BigInt(params.stagePolicyId),
        requirementsMet: evaluation.requirementsMet,
        evidenceScore: evaluation.evidenceScore,
        blockingRisks: evaluation.blockingRisks as any[],
        result: evaluation.result,
        rationale: evaluation.rationale,
        humanOverride: evaluation.humanOverride,
      })
      .returning();

    if (!row) throw APIError.internal("failed to save gate evaluation");

    // 5. Emit domain event
    const event = makeDomainEvent(GATE_EVALUATED, {
      gateEvaluationId: Number(row.id),
      projectId: Number(row.projectId),
      stagePolicyId: Number(policyRow.id),
      stageKey: policyRow.stageKey,
      result: row.result,
      requirementsMet: row.requirementsMet,
      evidenceScore: row.evidenceScore,
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
    });
    console.log(`[DomainEvent] ${GATE_EVALUATED}:`, JSON.stringify(event));

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      stagePolicyId: row.stagePolicyId ? Number(row.stagePolicyId) : null,
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
);

export const getGateEvaluation = api(
  { method: "GET", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ id }: { id: number }): Promise<GateEvaluation> => {
    const [row] = await db
      .select()
      .from(gateEvaluations)
      .where(and(eq(gateEvaluations.id, BigInt(id)), isNull(gateEvaluations.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`gate evaluation with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      stagePolicyId: row.stagePolicyId ? Number(row.stagePolicyId) : null,
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
);

export const listGateEvaluations = api(
  { method: "GET", path: "/operations/strategy/gate-evaluations", expose: true },
  async (params: ListGateEvaluationsParams): Promise<{ items: GateEvaluation[] }> => {
    const conditions = [isNull(gateEvaluations.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(gateEvaluations.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(gateEvaluations.companyId, BigInt(params.companyId)));
    }
    if (params.projectId) {
      conditions.push(eq(gateEvaluations.projectId, BigInt(params.projectId)));
    }

    const rows = await db
      .select()
      .from(gateEvaluations)
      .where(and(...conditions));

    return {
      items: rows.map((row) => ({
        id: Number(row.id),
        companyId: Number(row.companyId),
        workspaceId: Number(row.workspaceId),
        projectId: Number(row.projectId),
        stagePolicyId: row.stagePolicyId ? Number(row.stagePolicyId) : null,
        requirementsMet: row.requirementsMet,
        evidenceScore: row.evidenceScore,
        blockingRisks: row.blockingRisks as any[],
        result: row.result,
        rationale: row.rationale,
        humanOverride: row.humanOverride,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateGateEvaluation = api(
  { method: "PATCH", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ id, humanOverride, rationale }: { id: number; humanOverride?: boolean; rationale?: string }): Promise<GateEvaluation> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (humanOverride !== undefined) {
      updateValues.humanOverride = humanOverride;
      if (humanOverride) updateValues.result = "passed";
    }
    if (rationale !== undefined) updateValues.rationale = rationale;

    const [row] = await db
      .update(gateEvaluations)
      .set(updateValues)
      .where(and(eq(gateEvaluations.id, BigInt(id)), isNull(gateEvaluations.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`gate evaluation with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      stagePolicyId: row.stagePolicyId ? Number(row.stagePolicyId) : null,
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
);

export const deleteGateEvaluation = api(
  { method: "DELETE", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ id }: { id: number }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(gateEvaluations)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(gateEvaluations.id, BigInt(id)), isNull(gateEvaluations.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`gate evaluation with id ${id} not found`);
    return { success: true };
  }
);
