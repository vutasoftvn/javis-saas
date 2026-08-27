import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { buildOkrProgressUpdatedEvent, okrEvents } from "./okr-events.service";
import { computeKeyResultScore, computeObjectiveScore } from "./okr-scoring.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { okrCycles, okrObjectives, keyResults } = schema;

export interface OkrCycle {
  id: string;
  workspaceId: string;
  name: string;
  status: string;
  createdAt: string;
}

export interface CreateOkrCycleParams {
  workspaceId: string;
  name: string;
}

export interface Objective {
  id: string;
  workspaceId: string;
  cycleId: string;
  title: string;
  why: string | null;
  ownerMemberId: string | null;
  status: string;
  projectIds: string[];
  createdAt: string;
}

export interface CreateObjectiveParams {
  workspaceId: string;
  cycleId: string;
  title: string;
  why?: string;
  ownerMemberId?: string;
}

export interface KeyResult {
  id: string;
  objectiveId: string;
  title: string | null;
  targetValue: number | null;
  currentValue: number | null;
  unit: string | null;
  status: string;
  createdAt: string;
}

export interface AddKeyResultParams {
  objectiveId: string;
  title: string;
  targetValue: number;
  unit?: string;
}

export interface ObjectiveProgress {
  objectiveId: string;
  score: number;
  keyResults: { id: string; title: string | null; score: number }[];
}

function toKeyResult(row: typeof keyResults.$inferSelect): KeyResult {
  return {
    id: row.id.toString(),
    objectiveId: row.objectiveId.toString(),
    title: row.title,
    targetValue: row.targetValue,
    currentValue: row.currentValue,
    unit: row.unit,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

function toObjective(row: typeof okrObjectives.$inferSelect, projectIds: string[] = []): Objective {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    cycleId: row.cycleId.toString(),
    title: row.title,
    why: row.why,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    status: row.status,
    projectIds,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createOkrCycleService(params: CreateOkrCycleParams): Promise<OkrCycle> {
  await getWorkspace({ id: params.workspaceId });
  const [row] = await db
    .insert(okrCycles)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      name: params.name,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create okr cycle");
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    name: row.name,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createObjectiveService(params: CreateObjectiveParams): Promise<Objective> {
  await getWorkspace({ id: params.workspaceId });
  const [row] = await db
    .insert(okrObjectives)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      cycleId: BigInt(params.cycleId),
      title: params.title,
      why: params.why || null,
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create objective");
  return toObjective(row);
}

export async function addKeyResultService(params: AddKeyResultParams): Promise<KeyResult> {
  const [objective] = await db
    .select({ workspaceId: okrObjectives.workspaceId })
    .from(okrObjectives)
    .where(eq(okrObjectives.id, BigInt(params.objectiveId)))
    .limit(1);

  if (!objective) throw APIError.notFound(`objective ${params.objectiveId} not found`);

  const [row] = await db
    .insert(keyResults)
    .values({
      id: generateSnowflake(),
      workspaceId: objective.workspaceId,
      objectiveId: BigInt(params.objectiveId),
      title: params.title,
      targetValue: params.targetValue,
      currentValue: 0,
      unit: params.unit || "count",
    })
    .returning();

  if (!row) throw APIError.internal("failed to create key result");
  return toKeyResult(row);
}

export async function checkinService(id: string, value: number): Promise<KeyResult> {
  const [row] = await db
    .update(keyResults)
    .set({ currentValue: value })
    .where(eq(keyResults.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`key result ${id} not found`);
  return toKeyResult(row);
}

export async function getObjectiveService(id: string, authorization: string | undefined): Promise<Objective> {
  const [row] = await db
    .select()
    .from(okrObjectives)
    .where(eq(okrObjectives.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`objective ${id} not found`);

  // Verify caller has access to this objective's workspace
  await requireWorkspaceAccess(authorization, row.workspaceId.toString());

  // Populate projectIds from link table
  const { listObjectiveProjects } = await import("./project-link.service");
  const ctx: any = { workspaceId: row.workspaceId.toString() };
  const projectIds = await listObjectiveProjects(ctx, id);

  return toObjective(row, projectIds);
}

export async function getObjectiveProgressService(objectiveId: string): Promise<ObjectiveProgress> {
  const rows = await db
    .select()
    .from(keyResults)
    .where(eq(keyResults.objectiveId, BigInt(objectiveId)));

  const resultKeyResults: { id: string; title: string | null; score: number }[] = rows.map((row) => ({
    id: row.id.toString(),
    title: row.title,
    score: computeKeyResultScore(row.targetValue ?? 0, row.currentValue ?? 0),
  }));

  const score = computeObjectiveScore(resultKeyResults.map((kr) => kr.score));
  await okrEvents.publish(buildOkrProgressUpdatedEvent(objectiveId, score));
  return { objectiveId: String(objectiveId), score, keyResults: resultKeyResults };
}
