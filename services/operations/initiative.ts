import { api, APIError } from "encore.dev/api";
import { operationsDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface Initiative {
  id: number;
  workspaceId: number;
  brainId: number | null;
  projectId: number | null;
  offeringId: number | null;
  title: string;
  status: string;
  ownerId: number | null;
  createdAt: string;
}

export interface CreateInitiativeParams {
  workspaceId: number;
  title: string;
  ownerId?: number;
}

interface InitiativeRow {
  id: number;
  workspace_id: number;
  brain_id: number | null;
  project_id: number | null;
  offering_id: number | null;
  title: string;
  status: string;
  owner_id: number | null;
  created_at: Date;
}

function rowToInitiative(row: InitiativeRow): Initiative {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    brainId: row.brain_id,
    projectId: row.project_id,
    offeringId: row.offering_id,
    title: row.title,
    status: row.status,
    ownerId: row.owner_id,
    createdAt: row.created_at.toISOString(),
  };
}

export const createInitiative = api(
  { method: "POST", path: "/operations/initiatives", expose: true },
  async (params: CreateInitiativeParams): Promise<Initiative> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await operationsDB.queryRow<InitiativeRow>`
      INSERT INTO strategy.initiatives (workspace_id, title, owner_id)
      VALUES (${params.workspaceId}, ${params.title}, ${params.ownerId ?? null})
      RETURNING id, workspace_id, brain_id, project_id, offering_id, title, status, owner_id, created_at
    `;
    if (!row) throw APIError.internal("failed to create initiative");
    return rowToInitiative(row);
  }
);

export const getInitiative = api(
  { method: "GET", path: "/operations/initiatives/:id", expose: true },
  async ({ id }: { id: number }): Promise<Initiative> => {
    const row = await operationsDB.queryRow<InitiativeRow>`
      SELECT id, workspace_id, brain_id, project_id, offering_id, title, status, owner_id, created_at
      FROM strategy.initiatives WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`initiative ${id} not found`);
    return rowToInitiative(row);
  }
);
