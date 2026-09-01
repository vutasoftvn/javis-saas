import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const { interviews } = schema;

export interface Interview {
  id: string;
  workspaceId: string;
  projectId: string;
  contactRef: string | null;
  notes: string;
  conductedAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateInterviewInput {
  projectId: string | number;
  contactRef?: string | number;
  notes: string;
  conductedAt?: string;
}

export interface ListInterviewsInput {
  projectId?: string | number;
}

export interface UpdateInterviewInput {
  contactRef?: string | number;
  notes?: string;
  conductedAt?: string;
}

export function toInterview(row: typeof interviews.$inferSelect): Interview {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    contactRef: row.contactRef ? row.contactRef.toString() : null,
    notes: row.notes,
    conductedAt: row.conductedAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createInterviewInWorkspace(
  ctx: TenantContext,
  params: CreateInterviewInput
): Promise<Interview> {
  if (!params.projectId || !params.notes) {
    throw APIError.invalidArgument("projectId and notes are required");
  }
  const wsId = BigInt(ctx.workspaceId);

  // Xác nhận project thuộc workspace này
  await getProjectInWorkspace(params.projectId, ctx);

  const [row] = await db
    .insert(interviews)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      contactRef: params.contactRef ? BigInt(params.contactRef) : null,
      notes: params.notes,
      conductedAt: params.conductedAt ? new Date(params.conductedAt) : new Date(),
    })
    .returning();

  if (!row) throw APIError.internal("failed to create interview record");
  return toInterview(row);
}

export async function getInterviewInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<Interview> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(interviews)
    .where(and(eq(interviews.id, BigInt(id)), eq(interviews.workspaceId, wsId), isNull(interviews.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Interview not found");
  return toInterview(row);
}

export async function listInterviewsInWorkspace(
  ctx: TenantContext,
  params: ListInterviewsInput
): Promise<{ items: Interview[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(interviews.workspaceId, wsId), isNull(interviews.deletedAt)];

  if (params.projectId) {
    conditions.push(eq(interviews.projectId, BigInt(params.projectId)));
  }

  const rows = await db
    .select()
    .from(interviews)
    .where(and(...conditions));

  return {
    items: rows.map(toInterview),
  };
}

export async function updateInterviewInWorkspace(
  ctx: TenantContext,
  id: string | number,
  params: UpdateInterviewInput
): Promise<Interview> {
  const wsId = BigInt(ctx.workspaceId);

  const updateValues: Record<string, any> = { updatedAt: new Date() };
  if (params.notes !== undefined) updateValues.notes = params.notes;
  if (params.contactRef !== undefined) {
    updateValues.contactRef = params.contactRef ? BigInt(params.contactRef) : null;
  }
  if (params.conductedAt !== undefined) updateValues.conductedAt = new Date(params.conductedAt);

  const [row] = await db
    .update(interviews)
    .set(updateValues)
    .where(and(eq(interviews.id, BigInt(id)), eq(interviews.workspaceId, wsId), isNull(interviews.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Interview not found");
  return toInterview(row);
}

export async function deleteInterviewInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .update(interviews)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(interviews.id, BigInt(id)), eq(interviews.workspaceId, wsId), isNull(interviews.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Interview not found");
  return { success: true };
}
