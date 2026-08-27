import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { rankAssumptions } from "../services/assumption-ranking.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const { assumptions, projects } = schema;

export interface Assumption {
  id: string;
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
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  statement: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export interface ListAssumptionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  status?: string;
}

export interface UpdateAssumptionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  statement?: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

function toAssumption(row: typeof assumptions.$inferSelect): Assumption {
  return {
    id: row.id.toString(),
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

export const createAssumption = api(
  { method: "POST", path: "/operations/strategy/assumptions", expose: true },
  async (params: CreateAssumptionParams): Promise<Assumption> => {
    if (!params.projectId || !params.statement) {
      throw APIError.invalidArgument("projectId and statement are required");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    // Xác nhận project thuộc workspace này
    await getProjectInWorkspace(params.projectId, ctx);

    const importance = Math.max(1, Math.min(10, params.importance ?? 1));
    const uncertainty = Math.max(1, Math.min(10, params.uncertainty ?? 1));
    const riskScore = importance * uncertainty;

    const [row] = await db
      .insert(assumptions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: BigInt(params.projectId),
        statement: params.statement,
        importance,
        uncertainty,
        riskScore,
        status: params.status ?? "untested",
      })
      .returning();

    if (!row) throw APIError.internal("failed to create assumption");
    return toAssumption(row);
  }
);

export const getAssumption = api(
  { method: "GET", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Assumption> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.id, BigInt(id)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Assumption not found");
    return toAssumption(row);
  }
);

export const listAssumptions = api(
  { method: "GET", path: "/operations/strategy/assumptions", expose: true },
  async (params: ListAssumptionsParams): Promise<{ items: Assumption[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const conditions = [eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)];

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
      items: rows.map(toAssumption),
    };
  }
);

export const updateAssumption = api(
  { method: "PATCH", path: "/operations/strategy/assumptions/:id", expose: true },
  async (params: UpdateAssumptionParams): Promise<Assumption> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [existing] = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.id, BigInt(params.id)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
      .limit(1);

    if (!existing) throw APIError.notFound("Assumption not found");

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
      .where(and(eq(assumptions.id, BigInt(params.id)), eq(assumptions.workspaceId, wsId)))
      .returning();

    if (!row) throw APIError.notFound("Assumption not found");
    return toAssumption(row);
  }
);

export const deleteAssumption = api(
  { method: "DELETE", path: "/operations/strategy/assumptions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(assumptions)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(assumptions.id, BigInt(id)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Assumption not found");
    return { success: true };
  }
);

export const getRankedAssumptionsByProject = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/ranked-assumptions", expose: true },
  async ({ authorization, workspaceId, projectId }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; projectId: string }) => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    // Verify project belongs to this workspace
    await getProjectInWorkspace(projectId, ctx);

    const rows = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.projectId, BigInt(projectId)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)));

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
