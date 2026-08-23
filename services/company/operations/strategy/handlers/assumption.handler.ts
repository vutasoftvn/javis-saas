import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { rankAssumptions } from "../services/assumption-ranking.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

const { assumptions, projects } = schema;

export interface Assumption {
  id: string;
  companyId: string;
  workspaceId: string;
  projectId: string;
  statement: string;
  importance: number;
  uncertainty: number;
  riskScore: number;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAssumptionParams {
  companyId: string | number;
  workspaceId: string | number;
  projectId: string | number;
  statement: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export interface ListAssumptionsParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId?: string | number;
  status?: string;
}

export interface UpdateAssumptionParams {
  statement?: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export const createAssumption = api(
  { method: "POST", path: "/operations/strategy/assumptions", expose: true },
  async (params: CreateAssumptionParams): Promise<Assumption> => {
    if (!params.workspaceId || !params.companyId || !params.projectId || !params.statement) {
      throw APIError.invalidArgument("companyId, workspaceId, projectId, and statement are required");
    }

    const importance = Math.max(1, Math.min(10, params.importance ?? 1));
    const uncertainty = Math.max(1, Math.min(10, params.uncertainty ?? 1));
    const riskScore = importance * uncertainty;

    const [row] = await db
      .insert(assumptions)
      .values({
        id: generateSnowflake(),
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        statement: params.statement,
        importance,
        uncertainty,
        riskScore,
        status: params.status ?? "untested",
      })
      .returning();

    if (!row) throw APIError.internal("failed to create assumption");

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      statement: row.statement,
      importance: row.importance,
      uncertainty: row.uncertainty,
      riskScore: row.riskScore,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getAssumption = api(
  { method: "GET", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ id }: { id: string }): Promise<Assumption> => {
    const [row] = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.id, BigInt(id)), isNull(assumptions.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`assumption with id ${id} not found`);

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      statement: row.statement,
      importance: row.importance,
      uncertainty: row.uncertainty,
      riskScore: row.riskScore,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listAssumptions = api(
  { method: "GET", path: "/operations/strategy/assumptions", expose: true },
  async (params: ListAssumptionsParams): Promise<{ items: Assumption[] }> => {
    const conditions = [isNull(assumptions.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(assumptions.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(assumptions.companyId, BigInt(params.companyId)));
    }
    if (params.projectId) {
      conditions.push(eq(assumptions.projectId, BigInt(params.projectId)));
    }
    if (params.status) {
      conditions.push(eq(assumptions.status, params.status));
    }

    const rows = await db
      .select()
      .from(assumptions)
      .where(and(...conditions));

    return {
      items: rows.map((row) => ({
        id: row.id.toString(),
        companyId: row.companyId.toString(),
        workspaceId: row.workspaceId.toString(),
        projectId: row.projectId.toString(),
        statement: row.statement,
        importance: row.importance,
        uncertainty: row.uncertainty,
        riskScore: row.riskScore,
        status: row.status,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateAssumption = api(
  { method: "PATCH", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ id, ...params }: UpdateAssumptionParams & { id: string }): Promise<Assumption> => {
    const [existing] = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.id, BigInt(id)), isNull(assumptions.deletedAt)))
      .limit(1);

    if (!existing) throw APIError.notFound(`assumption with id ${id} not found`);

    const importance = params.importance !== undefined ? Math.max(1, Math.min(10, params.importance)) : existing.importance;
    const uncertainty = params.uncertainty !== undefined ? Math.max(1, Math.min(10, params.uncertainty)) : existing.uncertainty;
    const riskScore = importance * uncertainty;

    const updateValues: Record<string, any> = {
      importance,
      uncertainty,
      riskScore,
      updatedAt: new Date(),
    };
    if (params.statement !== undefined) updateValues.statement = params.statement;
    if (params.status !== undefined) updateValues.status = params.status;

    const [row] = await db
      .update(assumptions)
      .set(updateValues)
      .where(eq(assumptions.id, BigInt(id)))
      .returning();

    return {
      id: row.id.toString(),
      companyId: row.companyId.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId.toString(),
      statement: row.statement,
      importance: row.importance,
      uncertainty: row.uncertainty,
      riskScore: row.riskScore,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const deleteAssumption = api(
  { method: "DELETE", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(assumptions)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(assumptions.id, BigInt(id)), isNull(assumptions.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`assumption with id ${id} not found`);
    return { success: true };
  }
);

export const getRankedAssumptionsByProject = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/ranked-assumptions", expose: true },
  async ({ projectId }: { projectId: string }) => {
    const rows = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.projectId, BigInt(projectId)), isNull(assumptions.deletedAt)));

    const ranked = rankAssumptions(
      rows.map((r) => ({
        id: r.id.toString(),
        projectId: r.projectId.toString(),
        statement: r.statement,
        importance: r.importance,
        uncertainty: r.uncertainty,
        status: r.status,
      }))
    );

    return { items: ranked };
  }
);
