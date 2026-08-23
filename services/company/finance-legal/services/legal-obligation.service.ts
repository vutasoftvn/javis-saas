import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { legalObligations } = schema;

export interface LegalObligation {
  id: number;
  workspaceId: number;
  title: string;
  description: string | null;
  dueAt: string | null;
  status: string;
  createdAt: string;
}

export interface CreateObligationParams {
  workspaceId: number;
  title: string;
  description?: string;
  dueAt?: string;
}

function toObligation(row: typeof legalObligations.$inferSelect): LegalObligation {
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    title: row.title,
    description: row.description,
    dueAt: row.dueAt ? row.dueAt.toISOString() : null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

async function getObligationRow(id: number) {
  const [row] = await db
    .select()
    .from(legalObligations)
    .where(eq(legalObligations.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`obligation ${id} not found`);
  return row;
}

export async function createObligationService(
  params: CreateObligationParams,
  authorization: string | undefined
): Promise<LegalObligation> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const [row] = await db
    .insert(legalObligations)
    .values({
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
      description: params.description || null,
      dueAt: params.dueAt ? new Date(params.dueAt) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create obligation");
  return toObligation(row);
}

export async function getObligationService(
  id: number,
  authorization: string | undefined
): Promise<LegalObligation> {
  const row = await getObligationRow(id);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toObligation(row);
}

export async function fulfillObligationService(
  id: number,
  authorization: string | undefined
): Promise<LegalObligation> {
  const existing = await getObligationRow(id);
  await requireWorkspaceAccess(authorization, Number(existing.workspaceId));

  const [row] = await db
    .update(legalObligations)
    .set({ status: "FULFILLED" })
    .where(eq(legalObligations.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`obligation ${id} not found`);
  return toObligation(row);
}
