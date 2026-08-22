import { api, APIError } from "encore.dev/api";
import { operationsDB } from "./db";
import { getWorkspace } from "../identity/workspace";
import { buildOkrProgressUpdatedEvent, okrEvents } from "./okr-events";
import { computeKeyResultScore, computeObjectiveScore } from "./okr-scoring";

export interface OkrCycle {
  id: number;
  workspaceId: number;
  name: string;
  status: string;
  createdAt: string;
}

export interface CreateOkrCycleParams {
  workspaceId: number;
  name: string;
}

interface OkrCycleRow {
  id: number;
  workspace_id: number;
  name: string;
  status: string;
  created_at: Date;
}

function rowToOkrCycle(row: OkrCycleRow): OkrCycle {
  return { id: row.id, workspaceId: row.workspace_id, name: row.name, status: row.status, createdAt: row.created_at.toISOString() };
}

export const createOkrCycle = api(
  { method: "POST", path: "/operations/okr-cycles", expose: true },
  async (params: CreateOkrCycleParams): Promise<OkrCycle> => {
    await getWorkspace({ id: params.workspaceId });
    const row = await operationsDB.queryRow<OkrCycleRow>`
      INSERT INTO strategy.okr_cycles (workspace_id, name)
      VALUES (${params.workspaceId}, ${params.name})
      RETURNING id, workspace_id, name, status, created_at
    `;
    if (!row) throw APIError.internal("failed to create okr cycle");
    return rowToOkrCycle(row);
  }
);

export interface Objective {
  id: number;
  workspaceId: number;
  cycleId: number;
  title: string;
  why: string | null;
  ownerId: number | null;
  status: string;
  createdAt: string;
}

export interface CreateObjectiveParams {
  workspaceId: number;
  cycleId: number;
  title: string;
  why?: string;
  ownerId?: number;
}

interface ObjectiveRow {
  id: number;
  workspace_id: number;
  cycle_id: number;
  title: string;
  why: string | null;
  owner_id: number | null;
  status: string;
  created_at: Date;
}

function rowToObjective(row: ObjectiveRow): Objective {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    cycleId: row.cycle_id,
    title: row.title,
    why: row.why,
    ownerId: row.owner_id,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const createObjective = api(
  { method: "POST", path: "/operations/objectives", expose: true },
  async (params: CreateObjectiveParams): Promise<Objective> => {
    await getWorkspace({ id: params.workspaceId });
    const row = await operationsDB.queryRow<ObjectiveRow>`
      INSERT INTO strategy.okr_objectives (workspace_id, cycle_id, title, why, owner_id)
      VALUES (${params.workspaceId}, ${params.cycleId}, ${params.title}, ${params.why ?? null}, ${params.ownerId ?? null})
      RETURNING id, workspace_id, cycle_id, title, why, owner_id, status, created_at
    `;
    if (!row) throw APIError.internal("failed to create objective");
    return rowToObjective(row);
  }
);

export interface KeyResult {
  id: number;
  objectiveId: number;
  title: string | null;
  targetValue: number | null;
  currentValue: number | null;
  unit: string | null;
  status: string;
  createdAt: string;
}

export interface AddKeyResultParams {
  objectiveId: number;
  title: string;
  targetValue: number;
  unit?: string;
}

interface KeyResultRow {
  id: number;
  objective_id: number;
  title: string | null;
  target_value: number | null;
  current_value: number | null;
  unit: string | null;
  status: string;
  created_at: Date;
}

function rowToKeyResult(row: KeyResultRow): KeyResult {
  return {
    id: row.id,
    objectiveId: row.objective_id,
    title: row.title,
    targetValue: row.target_value,
    currentValue: row.current_value,
    unit: row.unit,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const addKeyResult = api(
  { method: "POST", path: "/operations/objectives/:objectiveId/key-results", expose: true },
  async (params: AddKeyResultParams): Promise<KeyResult> => {
    const row = await operationsDB.queryRow<KeyResultRow>`
      INSERT INTO strategy.key_results (workspace_id, objective_id, title, target_value, current_value, unit)
      SELECT workspace_id, ${params.objectiveId}, ${params.title}, ${params.targetValue}, 0, ${params.unit ?? "count"}
      FROM strategy.okr_objectives WHERE id = ${params.objectiveId}
      RETURNING id, objective_id, title, target_value, current_value, unit, status, created_at
    `;
    if (!row) throw APIError.notFound(`objective ${params.objectiveId} not found`);
    return rowToKeyResult(row);
  }
);

export const checkin = api(
  { method: "POST", path: "/operations/key-results/:id/checkin", expose: true },
  async ({ id, value }: { id: number; value: number }): Promise<KeyResult> => {
    const row = await operationsDB.queryRow<KeyResultRow>`
      UPDATE strategy.key_results SET current_value = ${value}
      WHERE id = ${id}
      RETURNING id, objective_id, title, target_value, current_value, unit, status, created_at
    `;
    if (!row) throw APIError.notFound(`key result ${id} not found`);
    return rowToKeyResult(row);
  }
);

export const getObjectiveProgress = api(
  { method: "GET", path: "/operations/objectives/:objectiveId/progress", expose: true },
  async ({
    objectiveId,
  }: {
    objectiveId: number;
  }): Promise<{ objectiveId: number; score: number; keyResults: { id: number; title: string | null; score: number }[] }> => {
    const rows = operationsDB.query<KeyResultRow>`
      SELECT id, objective_id, title, target_value, current_value, unit, status, created_at
      FROM strategy.key_results WHERE objective_id = ${objectiveId}
    `;
    const keyResults: { id: number; title: string | null; score: number }[] = [];
    for await (const row of rows) {
      const kr = rowToKeyResult(row);
      keyResults.push({ id: kr.id, title: kr.title, score: computeKeyResultScore(kr.targetValue ?? 0, kr.currentValue ?? 0) });
    }
    const score = computeObjectiveScore(keyResults.map((kr) => kr.score));
    await okrEvents.publish(buildOkrProgressUpdatedEvent(objectiveId, score));
    return { objectiveId, score, keyResults };
  }
);
