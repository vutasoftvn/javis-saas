import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { buildOkrProgressUpdatedEvent, okrEvents } from "../services/okr-events.service";
import { computeKeyResultScore, computeObjectiveScore } from "../services/okr-scoring.service";

const { okrCycles, okrObjectives, keyResults } = schema;

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

export const createOkrCycle = api(
  { method: "POST", path: "/operations/okr-cycles", expose: true },
  async (params: CreateOkrCycleParams): Promise<OkrCycle> => {
    await getWorkspace({ id: params.workspaceId });
    const [row] = await db
      .insert(okrCycles)
      .values({
        workspaceId: BigInt(params.workspaceId),
        name: params.name,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create okr cycle");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      name: row.name,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
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

export const createObjective = api(
  { method: "POST", path: "/operations/objectives", expose: true },
  async (params: CreateObjectiveParams): Promise<Objective> => {
    await getWorkspace({ id: params.workspaceId });
    const [row] = await db
      .insert(okrObjectives)
      .values({
        workspaceId: BigInt(params.workspaceId),
        cycleId: BigInt(params.cycleId),
        title: params.title,
        why: params.why || null,
        ownerId: params.ownerId ? BigInt(params.ownerId) : null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create objective");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      cycleId: Number(row.cycleId),
      title: row.title,
      why: row.why,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
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

export const addKeyResult = api(
  { method: "POST", path: "/operations/objectives/:objectiveId/key-results", expose: true },
  async (params: AddKeyResultParams): Promise<KeyResult> => {
    const [objective] = await db
      .select({ workspaceId: okrObjectives.workspaceId })
      .from(okrObjectives)
      .where(eq(okrObjectives.id, BigInt(params.objectiveId)))
      .limit(1);

    if (!objective) throw APIError.notFound(`objective ${params.objectiveId} not found`);

    const [row] = await db
      .insert(keyResults)
      .values({
        workspaceId: objective.workspaceId,
        objectiveId: BigInt(params.objectiveId),
        title: params.title,
        targetValue: params.targetValue,
        currentValue: 0,
        unit: params.unit || "count",
      })
      .returning();

    if (!row) throw APIError.internal("failed to create key result");
    return {
      id: Number(row.id),
      objectiveId: Number(row.objectiveId),
      title: row.title,
      targetValue: row.targetValue,
      currentValue: row.currentValue,
      unit: row.unit,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const checkin = api(
  { method: "POST", path: "/operations/key-results/:id/checkin", expose: true },
  async ({ id, value }: { id: number; value: number }): Promise<KeyResult> => {
    const [row] = await db
      .update(keyResults)
      .set({ currentValue: value })
      .where(eq(keyResults.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`key result ${id} not found`);
    return {
      id: Number(row.id),
      objectiveId: Number(row.objectiveId),
      title: row.title,
      targetValue: row.targetValue,
      currentValue: row.currentValue,
      unit: row.unit,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getObjectiveProgress = api(
  { method: "GET", path: "/operations/objectives/:objectiveId/progress", expose: true },
  async ({
    objectiveId,
  }: {
    objectiveId: number;
  }): Promise<{ objectiveId: number; score: number; keyResults: { id: number; title: string | null; score: number }[] }> => {
    const rows = await db
      .select()
      .from(keyResults)
      .where(eq(keyResults.objectiveId, BigInt(objectiveId)));

    const resultKeyResults: { id: number; title: string | null; score: number }[] = rows.map((row) => ({
      id: Number(row.id),
      title: row.title,
      score: computeKeyResultScore(row.targetValue ?? 0, row.currentValue ?? 0),
    }));

    const score = computeObjectiveScore(resultKeyResults.map((kr) => kr.score));
    await okrEvents.publish(buildOkrProgressUpdatedEvent(objectiveId, score));
    return { objectiveId, score, keyResults: resultKeyResults };
  }
);
