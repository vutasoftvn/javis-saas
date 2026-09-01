import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { RankedAssumption, rankAssumptions } from "./assumption-ranking.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const { assumptions } = schema;

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

export interface CreateAssumptionInput {
  projectId: string | number;
  statement: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export interface ListAssumptionsInput {
  projectId?: string | number;
  status?: string;
}

export interface UpdateAssumptionInput {
  statement?: string;
  importance?: number;
  uncertainty?: number;
  status?: string;
}

export function toAssumption(row: typeof assumptions.$inferSelect): Assumption {
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

export async function createAssumptionInWorkspace(
  ctx: TenantContext,
  params: CreateAssumptionInput
): Promise<Assumption> {
  if (!params.projectId || !params.statement) {
    throw APIError.invalidArgument("projectId and statement are required");
  }
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

export async function getAssumptionInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<Assumption> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(assumptions)
    .where(and(eq(assumptions.id, BigInt(id)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Assumption not found");
  return toAssumption(row);
}

export async function listAssumptionsInWorkspace(
  ctx: TenantContext,
  params: ListAssumptionsInput
): Promise<{ items: Assumption[] }> {
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

export async function updateAssumptionInWorkspace(
  ctx: TenantContext,
  id: string | number,
  params: UpdateAssumptionInput
): Promise<Assumption> {
  const wsId = BigInt(ctx.workspaceId);

  const [existing] = await db
    .select()
    .from(assumptions)
    .where(and(eq(assumptions.id, BigInt(id)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
    .limit(1);

  if (!existing) throw APIError.notFound("Assumption not found");

  const importance = params.importance !== undefined ? Math.max(1, Math.min(10, params.importance)) : existing.importance;
  const uncertainty = params.uncertainty !== undefined ? Math.max(1, Math.min(10, params.uncertainty)) : existing.uncertainty;
  const riskScore = importance * uncertainty;

  const updateValues = {
    importance,
    uncertainty,
    riskScore,
    updatedAt: new Date(),
    ...(params.statement !== undefined ? { statement: params.statement } : {}),
    ...(params.status !== undefined ? { status: params.status } : {}),
  };

  const [row] = await db
    .update(assumptions)
    .set(updateValues)
    .where(and(eq(assumptions.id, BigInt(id)), eq(assumptions.workspaceId, wsId)))
    .returning();

  if (!row) throw APIError.notFound("Assumption not found");
  return toAssumption(row);
}

export async function deleteAssumptionInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .update(assumptions)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(assumptions.id, BigInt(id)), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Assumption not found");
  return { success: true };
}

export async function getRankedAssumptionsByProjectInWorkspace(
  ctx: TenantContext,
  projectId: string | number
): Promise<{ items: RankedAssumption[] }> {
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
