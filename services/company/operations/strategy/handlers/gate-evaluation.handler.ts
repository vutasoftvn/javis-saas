import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull, inArray } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { GATE_EVALUATED } from "../../../shared/events";
import { evaluateGate, BlockingRiskItem } from "../services/gate-evaluation.service";
import { assessProjectStage } from "../services/stage-assessment.service";
import { buildProjectPhaseChangedEvent } from "../events/venture-stage-events";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const { gateEvaluations, stagePolicies, evidence, projects } = schema;

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
  humanOverride?: boolean;
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

    // 3. Evaluate deterministically without LLM
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
      humanOverride: params.humanOverride,
    });

    // 4. Save evaluation record and update project phase if passed
    const row = await db.transaction(async (tx) => {
      const [saved] = await tx
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
          humanOverride: evaluation.humanOverride,
        })
        .returning();

      if (!saved) throw APIError.internal("failed to save gate evaluation");

      if (evaluation.result === "passed") {
        const [projectRow] = await tx
          .select()
          .from(projects)
          .where(and(eq(projects.id, BigInt(params.projectId)), eq(projects.workspaceId, wsId)))
          .limit(1);

        if (projectRow) {
          const passedGateRows = await tx
            .select({
              stagePolicyId: gateEvaluations.stagePolicyId,
              result: gateEvaluations.result,
            })
            .from(gateEvaluations)
            .where(
              and(
                eq(gateEvaluations.projectId, BigInt(params.projectId)),
                eq(gateEvaluations.result, "passed"),
                isNull(gateEvaluations.deletedAt)
              )
            );

          const policyIds = [...new Set(passedGateRows.map((g) => g.stagePolicyId).filter((id): id is bigint => id !== null))];
          const policyMap = new Map<string, string>();
          if (policyIds.length > 0) {
            const pRows = await tx
              .select({ id: stagePolicies.id, stageKey: stagePolicies.stageKey })
              .from(stagePolicies)
              .where(inArray(stagePolicies.id, policyIds));
            pRows.forEach((p) => policyMap.set(p.id.toString(), p.stageKey));
          }

          const passedGateSummaries = passedGateRows.map((g) => ({
            stageKey: (g.stagePolicyId ? policyMap.get(g.stagePolicyId.toString()) : undefined) || policyRow.stageKey,
            result: g.result,
          }));

          const assessment = assessProjectStage({
            currentStage: projectRow.phase || "S0_GENESIS",
            evidenceList: evidenceRows.map((e) => ({
              id: e.id,
              sourceType: e.sourceType,
              strength: e.strength,
              confidence: e.confidence,
              supportsOrRefutes: e.supportsOrRefutes,
            })),
            passedGates: passedGateSummaries,
          });

          if (assessment.recommendedStage && assessment.recommendedStage !== projectRow.phase) {
            await tx
              .update(projects)
              .set({
                phase: assessment.recommendedStage,
                updatedAt: new Date(),
              })
              .where(eq(projects.id, projectRow.id));

            const event = buildProjectPhaseChangedEvent({
              projectId: projectRow.id.toString(),
              workspaceId: wsId.toString(),
              fromPhase: projectRow.phase || "S0_GENESIS",
              toPhase: assessment.recommendedStage,
              actorMemberId: ctx.userId ?? null,
            });
            await appendOutboxEvent(tx, event);
          }
        }
      }

      return saved;
    });

    return toGateEvaluation(row);
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
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (humanOverride !== undefined) {
      updateValues.humanOverride = humanOverride;
      if (humanOverride) updateValues.result = "passed";
    }
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
