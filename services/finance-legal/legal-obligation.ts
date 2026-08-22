import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface LegalObligationRow {
  id: number;
  workspace_id: number;
  title: string;
  description: string | null;
  due_at: Date | null;
  status: string;
  created_at: Date;
}

function rowToObligation(row: LegalObligationRow): LegalObligation {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    description: row.description,
    dueAt: row.due_at ? row.due_at.toISOString() : null,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const createObligation = api(
  { method: "POST", path: "/finance-legal/obligations", expose: true },
  async (params: CreateObligationParams): Promise<LegalObligation> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<LegalObligationRow>`
      INSERT INTO legal.legal_obligations (workspace_id, title, description, due_at)
      VALUES (${params.workspaceId}, ${params.title}, ${params.description ?? null}, ${params.dueAt ?? null})
      RETURNING id, workspace_id, title, description, due_at, status, created_at
    `;
    if (!row) throw APIError.internal("failed to create obligation");
    return rowToObligation(row);
  }
);

export const getObligation = api(
  { method: "GET", path: "/finance-legal/obligations/:id", expose: true },
  async ({ id }: { id: number }): Promise<LegalObligation> => {
    const row = await financeLegalDB.queryRow<LegalObligationRow>`
      SELECT id, workspace_id, title, description, due_at, status, created_at
      FROM legal.legal_obligations WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`obligation ${id} not found`);
    return rowToObligation(row);
  }
);

export const fulfillObligation = api(
  { method: "POST", path: "/finance-legal/obligations/:id/fulfill", expose: true },
  async ({ id }: { id: number }): Promise<LegalObligation> => {
    const row = await financeLegalDB.queryRow<LegalObligationRow>`
      UPDATE legal.legal_obligations SET status = 'FULFILLED'
      WHERE id = ${id}
      RETURNING id, workspace_id, title, description, due_at, status, created_at
    `;
    if (!row) throw APIError.notFound(`obligation ${id} not found`);
    return rowToObligation(row);
  }
);
