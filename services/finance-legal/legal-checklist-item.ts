import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface LegalChecklistItemRow {
  id: number;
  workspace_id: number;
  title: string;
  status: string;
  evidence_artifact_id: number | null;
  created_at: Date;
}

function rowToChecklistItem(row: LegalChecklistItemRow): LegalChecklistItem {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    status: row.status,
    evidenceArtifactId: row.evidence_artifact_id,
    createdAt: row.created_at.toISOString(),
  };
}

export const createChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items", expose: true },
  async (params: CreateChecklistItemParams): Promise<LegalChecklistItem> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<LegalChecklistItemRow>`
      INSERT INTO legal.legal_checklist_items (workspace_id, title)
      VALUES (${params.workspaceId}, ${params.title})
      RETURNING id, workspace_id, title, status, evidence_artifact_id, created_at
    `;
    if (!row) throw APIError.internal("failed to create checklist item");
    return rowToChecklistItem(row);
  }
);

export const getChecklistItem = api(
  { method: "GET", path: "/finance-legal/checklist-items/:id", expose: true },
  async ({ id }: { id: number }): Promise<LegalChecklistItem> => {
    const row = await financeLegalDB.queryRow<LegalChecklistItemRow>`
      SELECT id, workspace_id, title, status, evidence_artifact_id, created_at
      FROM legal.legal_checklist_items WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`checklist item ${id} not found`);
    return rowToChecklistItem(row);
  }
);

export const completeChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items/:id/complete", expose: true },
  async ({ id }: { id: number }): Promise<LegalChecklistItem> => {
    const row = await financeLegalDB.queryRow<LegalChecklistItemRow>`
      UPDATE legal.legal_checklist_items SET status = 'DONE'
      WHERE id = ${id}
      RETURNING id, workspace_id, title, status, evidence_artifact_id, created_at
    `;
    if (!row) throw APIError.notFound(`checklist item ${id} not found`);
    return rowToChecklistItem(row);
  }
);
