import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

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

export const createChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items", expose: true },
  async (params: CreateChecklistItemParams): Promise<LegalChecklistItem> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(legalChecklistItems)
      .values({
        workspaceId: BigInt(params.workspaceId),
        title: params.title,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create checklist item");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      status: row.status,
      evidenceArtifactId: row.evidenceArtifactId ? Number(row.evidenceArtifactId) : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getChecklistItem = api(
  { method: "GET", path: "/finance-legal/checklist-items/:id", expose: true },
  async ({ id }: { id: number }): Promise<LegalChecklistItem> => {
    const [row] = await db
      .select()
      .from(legalChecklistItems)
      .where(eq(legalChecklistItems.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`checklist item ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      status: row.status,
      evidenceArtifactId: row.evidenceArtifactId ? Number(row.evidenceArtifactId) : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const completeChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items/:id/complete", expose: true },
  async ({ id }: { id: number }): Promise<LegalChecklistItem> => {
    const [row] = await db
      .update(legalChecklistItems)
      .set({ status: "DONE" })
      .where(eq(legalChecklistItems.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`checklist item ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      status: row.status,
      evidenceArtifactId: row.evidenceArtifactId ? Number(row.evidenceArtifactId) : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
