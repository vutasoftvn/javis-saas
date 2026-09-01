import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { RankedAssumption, rankAssumptions } from "./assumption-ranking.service";

const { experiments, assumptions } = schema;

export interface Experiment {
  id: string;
  workspaceId: string;
  projectId: string;
  assumptionId: string | null;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget: number;
  ownerMemberId: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateExperimentInput {
  projectId: string | number;
  assumptionId?: string | number;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget?: number;
  ownerMemberId?: string | number;
  status?: string;
}

export interface ListExperimentsInput {
  projectId?: string | number;
  status?: string;
}

export interface UpdateExperimentInput {
  hypothesis?: string;
  method?: string;
  successCriteria?: string;
  budget?: number;
  ownerMemberId?: string | number;
  status?: string;
}

export interface ExperimentProposal {
  assumptionId: number | bigint | string;
  projectId: number | bigint | string;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget: number;
  status: "draft";
  rationale: string;
}

export interface ExistingExperimentSummary {
  assumptionId?: number | bigint | string | null;
}

export function toExperiment(row: typeof experiments.$inferSelect): Experiment {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
    hypothesis: row.hypothesis,
    method: row.method,
    successCriteria: row.successCriteria,
    budget: row.budget,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

/**
 * Đề xuất khung experiment mẫu từ top assumption chưa có experiment liên kết.
 * Service thuần tạo template tất định, không gọi LLM. Các chi tiết cụ thể
 * sẽ được tinh chỉnh bởi agent/skill ở tầng trên nếu cần.
 */
export function proposeExperimentsForAssumptions(
  assumptionsList: RankedAssumption[],
  existingExperiments: ExistingExperimentSummary[] = [],
  maxProposals: number = 3
): ExperimentProposal[] {
  const coveredAssumptionIds = new Set(
    existingExperiments
      .map((e) => e.assumptionId)
      .filter((id): id is number | bigint | string => id !== null && id !== undefined)
      .map((id) => String(id))
  );

  const untestedAssumptions = assumptionsList.filter(
    (a) => !coveredAssumptionIds.has(String(a.id)) && a.status !== "validated" && a.status !== "invalidated"
  );

  const proposals: ExperimentProposal[] = [];

  for (const assumption of untestedAssumptions.slice(0, maxProposals)) {
    let method = "customer_interview";
    let successCriteria = "At least 5 out of 10 targeted customer interviews confirm the problem exists with high severity.";

    if (assumption.importance >= 8 && assumption.uncertainty >= 7) {
      method = "concierge_or_smoke_test";
      successCriteria = "Conversion rate >= 5% on landing page signups or pre-orders.";
    } else if (assumption.importance >= 6) {
      method = "customer_discovery_interviews";
      successCriteria = ">= 70% positive intent across 10 structured stakeholder interviews.";
    }

    proposals.push({
      assumptionId: assumption.id,
      projectId: assumption.projectId,
      hypothesis: `We believe that: "${assumption.statement}". We will know we are right when: ${successCriteria}`,
      method,
      successCriteria,
      budget: 0,
      status: "draft",
      rationale: `Derived deterministically from high-risk assumption (rank #${assumption.rank}, risk score: ${assumption.computedRiskScore}).`,
    });
  }

  return proposals;
}

export async function createExperimentInWorkspace(
  ctx: TenantContext,
  params: CreateExperimentInput
): Promise<Experiment> {
  if (!params.projectId || !params.hypothesis || !params.method || !params.successCriteria) {
    throw APIError.invalidArgument("projectId, hypothesis, method, and successCriteria are required");
  }
  const wsId = BigInt(ctx.workspaceId);

  // Xác nhận project thuộc workspace này
  await getProjectInWorkspace(params.projectId, ctx);

  const [row] = await db
    .insert(experiments)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      assumptionId: params.assumptionId ? BigInt(params.assumptionId) : null,
      hypothesis: params.hypothesis,
      method: params.method,
      successCriteria: params.successCriteria,
      budget: params.budget ?? 0.0,
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,
      status: params.status ?? "draft",
    })
    .returning();

  if (!row) throw APIError.internal("failed to create experiment");
  return toExperiment(row);
}

export async function getExperimentInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<Experiment> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(experiments)
    .where(and(eq(experiments.id, BigInt(id)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Experiment not found");
  return toExperiment(row);
}

export async function listExperimentsInWorkspace(
  ctx: TenantContext,
  params: ListExperimentsInput
): Promise<{ items: Experiment[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)];

  if (params.projectId) {
    conditions.push(eq(experiments.projectId, BigInt(params.projectId)));
  }
  if (params.status) {
    conditions.push(eq(experiments.status, params.status));
  }

  const rows = await db
    .select()
    .from(experiments)
    .where(and(...conditions));

  return { items: rows.map(toExperiment) };
}

export async function updateExperimentInWorkspace(
  ctx: TenantContext,
  id: string | number,
  params: UpdateExperimentInput
): Promise<Experiment> {
  const wsId = BigInt(ctx.workspaceId);

  const updateValues: Record<string, any> = { updatedAt: new Date() };
  if (params.hypothesis !== undefined) updateValues.hypothesis = params.hypothesis;
  if (params.method !== undefined) updateValues.method = params.method;
  if (params.successCriteria !== undefined) updateValues.successCriteria = params.successCriteria;
  if (params.budget !== undefined) updateValues.budget = params.budget;
  if (params.ownerMemberId !== undefined) {
    updateValues.ownerMemberId = params.ownerMemberId ? BigInt(params.ownerMemberId) : null;
  }
  if (params.status !== undefined) updateValues.status = params.status;

  const [row] = await db
    .update(experiments)
    .set(updateValues)
    .where(and(eq(experiments.id, BigInt(id)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Experiment not found");
  return toExperiment(row);
}

export async function deleteExperimentInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .update(experiments)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(experiments.id, BigInt(id)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Experiment not found");
  return { success: true };
}

export async function proposeExperimentsInWorkspace(
  ctx: TenantContext,
  projectId: string | number
): Promise<{ items: ExperimentProposal[] }> {
  const wsId = BigInt(ctx.workspaceId);

  // Verify project belongs to this workspace
  await getProjectInWorkspace(projectId, ctx);

  const assumptionRows = await db
    .select()
    .from(assumptions)
    .where(and(eq(assumptions.projectId, BigInt(projectId)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)));

  const experimentRows = await db
    .select({ assumptionId: experiments.assumptionId })
    .from(experiments)
    .where(and(eq(experiments.projectId, BigInt(projectId)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)));

  const ranked = rankAssumptions(
    assumptionRows.map((r) => ({
      id: r.id.toString(),
      projectId: r.projectId.toString(),
      statement: r.statement,
      importance: r.importance,
      uncertainty: r.uncertainty,
      status: r.status,
    }))
  );

  const proposals = proposeExperimentsForAssumptions(
    ranked,
    experimentRows.map((e) => ({ assumptionId: e.assumptionId ? e.assumptionId.toString() : null }))
  );

  return { items: proposals };
}
