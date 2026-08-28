import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { EXPERIMENT_CREATED } from "../../../shared/events";
import { rankAssumptions } from "../services/assumption-ranking.service";
import { proposeExperimentsForAssumptions } from "../services/experiment-proposal.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

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

export interface CreateExperimentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  assumptionId?: string | number;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget?: number;
  ownerMemberId?: string | number;
  status?: string;
}

export interface ListExperimentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  status?: string;
}

export interface UpdateExperimentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  hypothesis?: string;
  method?: string;
  successCriteria?: string;
  budget?: number;
  ownerMemberId?: string | number;
  status?: string;
}

function toExperiment(row: typeof experiments.$inferSelect): Experiment {
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

export const createExperiment = api(
  { method: "POST", path: "/operations/strategy/experiments", expose: true },
  async (params: CreateExperimentParams): Promise<Experiment> => {
    if (!params.projectId || !params.hypothesis || !params.method || !params.successCriteria) {
      throw APIError.invalidArgument("projectId, hypothesis, method, and successCriteria are required");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const getExperiment = api(
  { method: "GET", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Experiment> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(experiments)
      .where(and(eq(experiments.id, BigInt(id)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Experiment not found");
    return toExperiment(row);
  }
);

export const listExperiments = api(
  { method: "GET", path: "/operations/strategy/experiments", expose: true },
  async (params: ListExperimentsParams): Promise<{ items: Experiment[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const updateExperiment = api(
  { method: "PATCH", path: "/operations/strategy/experiments/:id", expose: true },
  async (params: UpdateExperimentParams): Promise<Experiment> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
      .where(and(eq(experiments.id, BigInt(params.id)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Experiment not found");
    return toExperiment(row);
  }
);

export const deleteExperiment = api(
  { method: "DELETE", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(experiments)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(experiments.id, BigInt(id)), eq(experiments.workspaceId, wsId), isNull(experiments.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Experiment not found");
    return { success: true };
  }
);

export const proposeExperiments = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/proposed-experiments", expose: true },
  async ({ authorization, workspaceId, projectId }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; projectId: string }) => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
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

    const rankedAssumptions = rankAssumptions(
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
      rankedAssumptions,
      experimentRows.map((e) => ({ assumptionId: e.assumptionId ? e.assumptionId.toString() : null }))
    );

    return { items: proposals };
  }
);
