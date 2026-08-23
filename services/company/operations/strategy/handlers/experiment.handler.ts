import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { EXPERIMENT_CREATED, makeDomainEvent } from "../../../shared/events";
import { rankAssumptions } from "../services/assumption-ranking.service";
import { proposeExperimentsForAssumptions } from "../services/experiment-proposal.service";

const { experiments, assumptions } = schema;

export interface Experiment {
  id: string;
  companyId: string;
  workspaceId: string;
  projectId: string;
  assumptionId: number | null;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget: number;
  ownerWorkforceMemberId: number | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateExperimentParams {
  companyId: string;
  workspaceId: string;
  projectId: string;
  assumptionId?: number;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget?: number;
  ownerWorkforceMemberId?: number;
  status?: string;
}

export interface ListExperimentsParams {
  workspaceId?: number;
  companyId?: number;
  projectId?: number;
  status?: string;
}

export interface UpdateExperimentParams {
  hypothesis?: string;
  method?: string;
  successCriteria?: string;
  budget?: number;
  ownerWorkforceMemberId?: number;
  status?: string;
}

export const createExperiment = api(
  { method: "POST", path: "/operations/strategy/experiments", expose: true },
  async (params: CreateExperimentParams): Promise<Experiment> => {
    if (!params.workspaceId || !params.companyId || !params.projectId || !params.hypothesis || !params.method || !params.successCriteria) {
      throw APIError.invalidArgument("companyId, workspaceId, projectId, hypothesis, method, and successCriteria are required");
    }

    const [row] = await db
      .insert(experiments)
      .values({
        id: generateSnowflake(),
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        assumptionId: params.assumptionId ? BigInt(params.assumptionId) : null,
        hypothesis: params.hypothesis,
        method: params.method,
        successCriteria: params.successCriteria,
        budget: params.budget ?? 0.0,
        ownerWorkforceMemberId: params.ownerWorkforceMemberId ? BigInt(params.ownerWorkforceMemberId) : null,
        status: params.status ?? "draft",
      })
      .returning();

    if (!row) throw APIError.internal("failed to create experiment");

    // Emit domain event
    const event = makeDomainEvent(EXPERIMENT_CREATED, {
      experimentId: row.id.toString(),
      projectId: row.projectId.toString(),
      assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
    });
    // Structured log / event emission
    console.log(`[DomainEvent] ${EXPERIMENT_CREATED}:`, JSON.stringify(event));

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
      hypothesis: row.hypothesis,
      method: row.method,
      successCriteria: row.successCriteria,
      budget: row.budget,
      ownerWorkforceMemberId: row.ownerWorkforceMemberId ? row.ownerWorkforceMemberId.toString() : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getExperiment = api(
  { method: "GET", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ id }: { id: string }): Promise<Experiment> => {
    const [row] = await db
      .select()
      .from(experiments)
      .where(and(eq(experiments.id, BigInt(id)), isNull(experiments.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`experiment with id ${id} not found`);

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
      hypothesis: row.hypothesis,
      method: row.method,
      successCriteria: row.successCriteria,
      budget: row.budget,
      ownerWorkforceMemberId: row.ownerWorkforceMemberId ? row.ownerWorkforceMemberId.toString() : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listExperiments = api(
  { method: "GET", path: "/operations/strategy/experiments", expose: true },
  async (params: ListExperimentsParams): Promise<{ items: Experiment[] }> => {
    const conditions = [isNull(experiments.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(experiments.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(experiments.companyId, BigInt(params.companyId)));
    }
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

    return {
      items: rows.map((row) => ({
        id: row.id.toString(),
        companyId: row.companyId.toString(),
        workspaceId: row.workspaceId.toString(),
        projectId: row.projectId.toString(),
        assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
        hypothesis: row.hypothesis,
        method: row.method,
        successCriteria: row.successCriteria,
        budget: row.budget,
        ownerWorkforceMemberId: row.ownerWorkforceMemberId ? row.ownerWorkforceMemberId.toString() : null,
        status: row.status,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateExperiment = api(
  { method: "PATCH", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ id, ...params }: UpdateExperimentParams & { id: string }): Promise<Experiment> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.hypothesis !== undefined) updateValues.hypothesis = params.hypothesis;
    if (params.method !== undefined) updateValues.method = params.method;
    if (params.successCriteria !== undefined) updateValues.successCriteria = params.successCriteria;
    if (params.budget !== undefined) updateValues.budget = params.budget;
    if (params.ownerWorkforceMemberId !== undefined) {
      updateValues.ownerWorkforceMemberId = params.ownerWorkforceMemberId ? BigInt(params.ownerWorkforceMemberId) : null;
    }
    if (params.status !== undefined) updateValues.status = params.status;

    const [row] = await db
      .update(experiments)
      .set(updateValues)
      .where(and(eq(experiments.id, BigInt(id)), isNull(experiments.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`experiment with id ${id} not found`);

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
      hypothesis: row.hypothesis,
      method: row.method,
      successCriteria: row.successCriteria,
      budget: row.budget,
      ownerWorkforceMemberId: row.ownerWorkforceMemberId ? row.ownerWorkforceMemberId.toString() : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const deleteExperiment = api(
  { method: "DELETE", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(experiments)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(experiments.id, BigInt(id)), isNull(experiments.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`experiment with id ${id} not found`);
    return { success: true };
  }
);

export const proposeExperiments = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/proposed-experiments", expose: true },
  async ({ projectId }: { projectId: string }) => {
    const assumptionRows = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.projectId, BigInt(projectId)), isNull(assumptions.deletedAt)));

    const experimentRows = await db
      .select({ assumptionId: experiments.assumptionId })
      .from(experiments)
      .where(and(eq(experiments.projectId, BigInt(projectId)), isNull(experiments.deletedAt)));

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
