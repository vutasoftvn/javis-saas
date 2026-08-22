import { api, APIError } from "encore.dev/api";
import { okrDB } from "./db";

export interface Objective {
  id: number;
  workspaceId: string;
  title: string;
  period: string;
  owner: string;
  createdAt: string;
}

export interface KeyResult {
  id: number;
  objectiveId: number;
  title: string;
  targetValue: number;
  currentValue: number;
  unit: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateObjectiveParams {
  workspaceId: string;
  title: string;
  period: string;
  owner: string;
}

export interface AddKeyResultParams {
  objectiveId: number;
  title: string;
  targetValue: number;
  unit?: string;
}

interface ObjectiveRow {
  id: number;
  workspace_id: string;
  title: string;
  period: string;
  owner: string;
  created_at: Date;
}

interface KeyResultRow {
  id: number;
  objective_id: number;
  title: string;
  target_value: number;
  current_value: number;
  unit: string;
  created_at: Date;
  updated_at: Date;
}

function rowToObjective(row: ObjectiveRow): Objective {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    period: row.period,
    owner: row.owner,
    createdAt: row.created_at.toISOString(),
  };
}

export function rowToKeyResult(row: KeyResultRow): KeyResult {
  return {
    id: row.id,
    objectiveId: row.objective_id,
    title: row.title,
    targetValue: row.target_value,
    currentValue: row.current_value,
    unit: row.unit,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createObjective = api(
  { method: "POST", path: "/objectives", expose: true },
  async (params: CreateObjectiveParams): Promise<Objective> => {
    const row = await okrDB.queryRow<ObjectiveRow>`
      INSERT INTO objectives (workspace_id, title, period, owner)
      VALUES (${params.workspaceId}, ${params.title}, ${params.period}, ${params.owner})
      RETURNING id, workspace_id, title, period, owner, created_at
    `;
    if (!row) throw APIError.internal("failed to create objective");
    return rowToObjective(row);
  }
);

export const addKeyResult = api(
  { method: "POST", path: "/objectives/:objectiveId/key-results", expose: true },
  async (params: AddKeyResultParams): Promise<KeyResult> => {
    const row = await okrDB.queryRow<KeyResultRow>`
      INSERT INTO key_results (objective_id, title, target_value, unit)
      VALUES (${params.objectiveId}, ${params.title}, ${params.targetValue}, ${params.unit ?? "count"})
      RETURNING id, objective_id, title, target_value, current_value, unit, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to add key result");
    return rowToKeyResult(row);
  }
);
