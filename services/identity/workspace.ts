import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";

export interface Workspace {
  id: number;
  name: string;
  companyStage: string;
  createdAt: string;
}

export interface CreateWorkspaceParams {
  name: string;
}

interface WorkspaceRow {
  id: number;
  name: string;
  company_stage: string;
  created_at: Date;
}

function rowToWorkspace(row: WorkspaceRow): Workspace {
  return {
    id: row.id,
    name: row.name,
    companyStage: row.company_stage,
    createdAt: row.created_at.toISOString(),
  };
}

export const createWorkspace = api(
  { method: "POST", path: "/identity/workspaces", expose: true },
  async (params: CreateWorkspaceParams): Promise<Workspace> => {
    const row = await identityDB.queryRow<WorkspaceRow>`
      INSERT INTO core.workspaces (name)
      VALUES (${params.name})
      RETURNING id, name, company_stage, created_at
    `;
    if (!row) throw APIError.internal("failed to create workspace");
    return rowToWorkspace(row);
  }
);

export const getWorkspace = api(
  { method: "GET", path: "/identity/workspaces/:id", expose: true },
  async ({ id }: { id: number }): Promise<Workspace> => {
    const row = await identityDB.queryRow<WorkspaceRow>`
      SELECT id, name, company_stage, created_at FROM core.workspaces WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`workspace ${id} not found`);
    return rowToWorkspace(row);
  }
);
