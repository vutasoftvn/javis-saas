import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { legalChecklistItems } = schema;

export interface LegalChecklistItem {
  id: string;
  workspaceId: string;
  title: string;
  status: string;
  evidenceArtifactId: string | null;
  createdAt: string;
}

export interface CreateChecklistItemParams {
  workspaceId: string | number;
  title: string;
}

function toChecklistItem(row: typeof legalChecklistItems.$inferSelect): LegalChecklistItem {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    title: row.title,
    status: row.status,
    evidenceArtifactId: row.evidenceArtifactId ? String(row.evidenceArtifactId) : null,
    createdAt: row.createdAt.toISOString(),
  };
}

async function getChecklistItemRow(id: string | number) {
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
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(legalChecklistItems)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create checklist item");
  return toChecklistItem(row);
}

export async function getChecklistItemService(
  id: string | number,
  authorization: string | undefined
): Promise<LegalChecklistItem> {
  const row = await getChecklistItemRow(id);
  await requireWorkspaceAccess(authorization, row.workspaceId);
  return toChecklistItem(row);
}

export async function completeChecklistItemService(
  id: string | number,
  authorization: string | undefined
): Promise<LegalChecklistItem> {
  const existing = await getChecklistItemRow(id);
  await requireWorkspaceAccess(authorization, String(existing.workspaceId));

  const [row] = await db
    .update(legalChecklistItems)
    .set({ status: "DONE" })
    .where(eq(legalChecklistItems.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`checklist item ${id} not found`);
  return toChecklistItem(row);
}
