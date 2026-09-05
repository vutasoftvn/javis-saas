import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { computeKeyResultProgress, computeObjectiveScore, KrScoringType } from "./okr-scoring.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mvpList, mvpItem, MvpSuccess } from "../../shared/contracts/mvp-response";
import { TenantContext } from "../../shared/types/tenant_context";

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
  authorization?: string;
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
  authorization?: string;
}

export interface KeyResult {
  id: string;
  objectiveId: string;
  title: string | null;
  targetValue: number | null;
  currentValue: number | null;
  baselineValue: number | null;
  scoringType: string;
  unit: string | null;
  status: string;
  createdAt: string;
}

export interface AddKeyResultParams {
  objectiveId: string;
  title: string;
  targetValue: number;
  // IA22: trước đây không có cách nào set baseline/scoringType qua API nên
  // mọi KR mặc định LINEAR_INCREASE baseline=0 — một KR mục tiêu GIẢM (vd
  // churn) bị tính điểm như thể mục tiêu là TĂNG, cho điểm sai hoàn toàn.
  baselineValue?: number;
  scoringType?: KrScoringType;
  unit?: string;
  authorization?: string;
}

export interface ObjectiveProgress {
  objectiveId: string;
  score: number;
  keyResults: { id: string; title: string | null; score: number }[];
}

function toOkrCycle(row: typeof okrCycles.$inferSelect): OkrCycle {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    name: row.name,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

function toKeyResult(row: typeof keyResults.$inferSelect): KeyResult {
  return {
    id: row.id.toString(),
    objectiveId: row.objectiveId.toString(),
    title: row.title,
    targetValue: row.targetValue,
    currentValue: row.currentValue,
    baselineValue: row.baselineValue,
    scoringType: row.scoringType,
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
  await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
  await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
  await requireWorkspaceAccess(params.authorization, objective.workspaceId.toString());

  const [row] = await db
    .insert(keyResults)
    .values({
      id: generateSnowflake(),
      workspaceId: objective.workspaceId,
      objectiveId: BigInt(params.objectiveId),
      title: params.title,
      targetValue: params.targetValue,
      currentValue: 0,
      baselineValue: params.baselineValue ?? null,
      scoringType: params.scoringType ?? "LINEAR_INCREASE",
      unit: params.unit || "count",
    })
    .returning();

  if (!row) throw APIError.internal("failed to create key result");
  return toKeyResult(row);
}

export async function checkinService(
  id: string,
  value: number,
  authorization?: string
): Promise<KeyResult> {
  // Resolve workspace của key result qua objective rồi mới cho ghi.
  const [kr] = await db
    .select({ objectiveId: keyResults.objectiveId })
    .from(keyResults)
    .where(eq(keyResults.id, BigInt(id)))
    .limit(1);
  if (!kr) throw APIError.notFound(`key result ${id} not found`);
  const [obj] = await db
    .select({ workspaceId: okrObjectives.workspaceId })
    .from(okrObjectives)
    .where(eq(okrObjectives.id, kr.objectiveId))
    .limit(1);
  if (!obj) throw APIError.notFound(`objective for key result ${id} not found`);
  await requireWorkspaceAccess(authorization, obj.workspaceId.toString());

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

export async function getObjectiveProgressService(
  objectiveId: string,
  ctx?: TenantContext
): Promise<ObjectiveProgress> {
  const objId = BigInt(objectiveId);
  if (ctx) {
    const wsId = BigInt(ctx.workspaceId);
    const [obj] = await db
      .select()
      .from(okrObjectives)
      .where(and(eq(okrObjectives.id, objId), eq(okrObjectives.workspaceId, wsId)));
    if (!obj) throw APIError.notFound(`Objective ${objectiveId} not found`);
  }

  const rows = await db
    .select()
    .from(keyResults)
    .where(eq(keyResults.objectiveId, objId));

  const resultKeyResults: { id: string; title: string | null; score: number }[] = rows.map((row) => ({
    id: row.id.toString(),
    title: row.title,
    // IA22: dùng computeKeyResultProgress (baseline + scoringType aware) thay
    // vì tỷ lệ current/target thô — KR mục tiêu GIẢM (LINEAR_DECREASE, vd
    // baseline=10 target=5 current=8) trước đây tính score=1 (sai), giờ đúng
    // 0.4 theo hướng tiến bộ thật.
    score:
      computeKeyResultProgress({
        baseline: row.baselineValue,
        target: row.targetValue,
        current: row.currentValue,
        scoringType: row.scoringType as KrScoringType,
      }) ?? 0,
  }));

  const score = computeObjectiveScore(resultKeyResults.map((kr) => kr.score));
  return { objectiveId: String(objectiveId), score, keyResults: resultKeyResults };
}

export async function listOkrCyclesService(ctx: TenantContext): Promise<MvpSuccess<readonly OkrCycle[]>> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(okrCycles)
    .where(eq(okrCycles.workspaceId, wsId))
    .orderBy(desc(okrCycles.createdAt));

  return mvpList(
    rows.map(toOkrCycle),
    [{ kind: "company_db", ref: "operating.okr_cycles" }]
  );
}

export async function listObjectivesService(ctx: TenantContext): Promise<MvpSuccess<readonly Objective[]>> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(okrObjectives)
    .where(eq(okrObjectives.workspaceId, wsId))
    .orderBy(desc(okrObjectives.createdAt));

  const objectivesList: Objective[] = [];
  const { listObjectiveProjects } = await import("./project-link.service");

  for (const row of rows) {
    const pIds = await listObjectiveProjects(ctx, row.id.toString());
    objectivesList.push(toObjective(row, pIds));
  }

  return mvpList(
    objectivesList,
    [{ kind: "company_db", ref: "operating.okr_objectives" }]
  );
}

export async function deleteObjectiveService(ctx: TenantContext, idStr: string): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [existing] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, id), eq(okrObjectives.workspaceId, wsId)));

  if (!existing) {
    throw APIError.notFound(`Objective ${idStr} not found`);
  }

  await db
    .delete(okrObjectives)
    .where(and(eq(okrObjectives.id, id), eq(okrObjectives.workspaceId, wsId)));
}
