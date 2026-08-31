import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments } = schema;

export interface TwelveWeekCycle {
  id: string;
  workspaceId: string;
  projectId?: string | null;
  theme?: string | null;
  visionStatement: string;
  stageAtStart: string;
  currentWeek: number;
  durationWeeks: number;
  overallExecutionScore: number;
  startDate?: string | null;
  endDate?: string | null;
  commitmentLevel?: string | null;
  status: string;
  createdAt: string;
}

export interface CreateTwelveWeekCycleRequest {
  workspaceId: string | number;
  authorization?: string;
  projectId?: string | number | null;
  theme?: string | null;
  visionStatement?: string;
  stageAtStart?: string;
  durationWeeks?: number;
  startDate?: string | null;
  endDate?: string | null;
  commitmentLevel?: string | null;
}

export interface WeeklyPlan {
  id: string;
  workspaceId: string;
  cycleId: string;
  weekNo: number;
  startDate?: string | null;
  endDate?: string | null;
  focus?: string | null;
  mission?: string | null;
  executionScore?: number | null;
  outcomeScore?: number | null;
  reflection?: string | null;
  createdAt: string;
}

export interface CreateWeeklyPlanRequest {
  workspaceId: string | number;
  authorization?: string;
  cycleId: string | number;
  weekNo: number;
  startDate?: string | null;
  endDate?: string | null;
  focus?: string | null;
  mission?: string | null;
}

export interface WeeklyCommitment {
  id: string;
  workspaceId: string;
  weeklyPlanId: string;
  initiativeId?: string | null;
  title: string;
  status: string;
  plannedEffort?: string | null;
  commitmentOwnerType?: string | null;
  executionMode?: string | null;
  createdAt: string;
}

export interface CreateWeeklyCommitmentRequest {
  workspaceId: string | number;
  authorization?: string;
  weeklyPlanId: string | number;
  initiativeId?: string | number | null;
  title: string;
  plannedEffort?: string | null;
  commitmentOwnerType?: string | null;
  executionMode?: string | null;
}

function toCycle(row: typeof twelveWeekCycles.$inferSelect): TwelveWeekCycle {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId ? row.projectId.toString() : null,
    theme: row.theme,
    visionStatement: row.visionStatement,
    stageAtStart: row.stageAtStart,
    currentWeek: row.currentWeek,
    durationWeeks: row.durationWeeks,
    overallExecutionScore: row.overallExecutionScore,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    commitmentLevel: row.commitmentLevel,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createCycleService(req: CreateTwelveWeekCycleRequest): Promise<TwelveWeekCycle> {
  if (!req.workspaceId) throw APIError.invalidArgument("workspaceId is required");
  await requireWorkspaceAccess(req.authorization, String(req.workspaceId));

  const [row] = await db
    .insert(twelveWeekCycles)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      projectId: req.projectId ? BigInt(req.projectId) : null,
      theme: req.theme || null,
      visionStatement: req.visionStatement ?? "",
      stageAtStart: req.stageAtStart ?? "S1_PROBLEM_VALIDATION",
      durationWeeks: req.durationWeeks ?? 12,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
      commitmentLevel: req.commitmentLevel || null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create twelve week cycle");
  return toCycle(row);
}

export async function listCyclesService(workspaceId: string | number): Promise<TwelveWeekCycle[]> {
  const rows = await db
    .select()
    .from(twelveWeekCycles)
    .where(eq(twelveWeekCycles.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(twelveWeekCycles.id));

  return rows.map(toCycle);
}

export async function createWeeklyPlanService(req: CreateWeeklyPlanRequest): Promise<WeeklyPlan> {
  if (!req.workspaceId || !req.cycleId || !req.weekNo) {
    throw APIError.invalidArgument("workspaceId, cycleId, and weekNo are required");
  }
  await requireWorkspaceAccess(req.authorization, String(req.workspaceId));

  const [row] = await db
    .insert(weeklyPlans)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      cycleId: BigInt(req.cycleId),
      weekNo: req.weekNo,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
      focus: req.focus || null,
      mission: req.mission || null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create weekly plan");
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    cycleId: row.cycleId.toString(),
    weekNo: row.weekNo,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    focus: row.focus,
    mission: row.mission,
    executionScore: row.executionScore,
    outcomeScore: row.outcomeScore,
    reflection: row.reflection,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createWeeklyCommitmentService(req: CreateWeeklyCommitmentRequest): Promise<WeeklyCommitment> {
  if (!req.workspaceId || !req.weeklyPlanId || !req.title) {
    throw APIError.invalidArgument("workspaceId, weeklyPlanId, and title are required");
  }
  await requireWorkspaceAccess(req.authorization, String(req.workspaceId));

  const [row] = await db
    .insert(weeklyCommitments)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      weeklyPlanId: BigInt(req.weeklyPlanId),
      initiativeId: req.initiativeId ? BigInt(req.initiativeId) : null,
      title: req.title,
      plannedEffort: req.plannedEffort || null,
      commitmentOwnerType: req.commitmentOwnerType || "FOUNDER",
      executionMode: req.executionMode || "MANUAL",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create weekly commitment");
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    weeklyPlanId: row.weeklyPlanId.toString(),
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    title: row.title,
    status: row.status,
    plannedEffort: row.plannedEffort,
    commitmentOwnerType: row.commitmentOwnerType,
    executionMode: row.executionMode,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function listTwelveWeekCyclesService(
  workspaceId: string | number,
  authorization?: string
): Promise<import("../../shared/contracts/mvp-response").MvpSuccess<readonly TwelveWeekCycle[]>> {
  const { requireWorkspaceAccess } = await import("../../shared/auth/workspace-access");
  const { mvpList } = await import("../../shared/contracts/mvp-response");
  const ctx = await requireWorkspaceAccess(authorization, String(workspaceId));
  const wsId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(twelveWeekCycles)
    .where(eq(twelveWeekCycles.workspaceId, wsId))
    .orderBy(desc(twelveWeekCycles.createdAt));

  return mvpList(
    rows.map(toCycle),
    [{ kind: "company_db", ref: "operating.twelve_week_cycles" }]
  );
}

export async function listWeeklyPlansService(
  workspaceId: string | number,
  authorization?: string
): Promise<import("../../shared/contracts/mvp-response").MvpSuccess<readonly WeeklyPlan[]>> {
  const { requireWorkspaceAccess } = await import("../../shared/auth/workspace-access");
  const { mvpList } = await import("../../shared/contracts/mvp-response");
  const ctx = await requireWorkspaceAccess(authorization, String(workspaceId));
  const wsId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(weeklyPlans)
    .where(eq(weeklyPlans.workspaceId, wsId))
    .orderBy(desc(weeklyPlans.createdAt));

  const plans: WeeklyPlan[] = rows.map((row) => ({
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    cycleId: row.cycleId.toString(),
    weekNo: row.weekNo,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    focus: row.focus,
    mission: row.mission,
    executionScore: row.executionScore,
    outcomeScore: row.outcomeScore,
    reflection: row.reflection,
    createdAt: row.createdAt.toISOString(),
  }));

  return mvpList(
    plans,
    [{ kind: "company_db", ref: "operating.weekly_plans" }]
  );
}

export async function listWeeklyCommitmentsService(
  workspaceId: string | number,
  authorization?: string
): Promise<import("../../shared/contracts/mvp-response").MvpSuccess<readonly WeeklyCommitment[]>> {
  const { requireWorkspaceAccess } = await import("../../shared/auth/workspace-access");
  const { mvpList } = await import("../../shared/contracts/mvp-response");
  const ctx = await requireWorkspaceAccess(authorization, String(workspaceId));
  const wsId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(weeklyCommitments)
    .where(eq(weeklyCommitments.workspaceId, wsId))
    .orderBy(desc(weeklyCommitments.createdAt));

  const commitments: WeeklyCommitment[] = rows.map((row) => ({
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    weeklyPlanId: row.weeklyPlanId.toString(),
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    title: row.title,
    status: row.status,
    plannedEffort: row.plannedEffort,
    commitmentOwnerType: row.commitmentOwnerType,
    executionMode: row.executionMode,
    createdAt: row.createdAt.toISOString(),
  }));

  return mvpList(
    commitments,
    [{ kind: "company_db", ref: "operating.weekly_commitments" }]
  );
}
