import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { legalChecklistItems } = schema;

export interface LegalChecklistItem {
  id: number;
  workspaceId: number;
  title: string;
  status: string;
  evidenceArtifactId: number | null;
  createdAt: string;
}

export interface CreateChecklistItemParams {
  workspaceId: number;
  title: string;
}

function toChecklistItem(row: typeof legalChecklistItems.$inferSelect): LegalChecklistItem {
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    title: row.title,
    status: row.status,
    evidenceArtifactId: row.evidenceArtifactId ? Number(row.evidenceArtifactId) : null,
    createdAt: row.createdAt.toISOString(),
  };
}

async function getChecklistItemRow(id: number) {
  const [row] = await db
    .select()
    .from(legalChecklistItems)
    .where(eq(legalChecklistItems.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`checklist item ${id} not found`);
  return row;
}

export async function createChecklistItemService(
  params: CreateChecklistItemParams,
  authorization: string | undefined
): Promise<LegalChecklistItem> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const [row] = await db
    .insert(legalChecklistItems)
    .values({
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create checklist item");
  return toChecklistItem(row);
}

export async function getChecklistItemService(
  id: number,
  authorization: string | undefined
): Promise<LegalChecklistItem> {
  const row = await getChecklistItemRow(id);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toChecklistItem(row);
}

export async function completeChecklistItemService(
  id: number,
  authorization: string | undefined
): Promise<LegalChecklistItem> {
  const existing = await getChecklistItemRow(id);
  await requireWorkspaceAccess(authorization, Number(existing.workspaceId));

  const [row] = await db
    .update(legalChecklistItems)
    .set({ status: "DONE" })
    .where(eq(legalChecklistItems.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`checklist item ${id} not found`);
  return toChecklistItem(row);
}
