import { api, APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments } = schema;

export interface TwelveWeekCycle {
  id: number;
  workspaceId: number;
  brainId?: number | null;
  projectId?: number | null;
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
  workspaceId: number;
  brainId?: number | null;
  projectId?: number | null;
  theme?: string | null;
  visionStatement?: string;
  stageAtStart?: string;
  durationWeeks?: number;
  startDate?: string | null;
  endDate?: string | null;
  commitmentLevel?: string | null;
}

export interface WeeklyPlan {
  id: number;
  workspaceId: number;
  cycleId: number;
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
  workspaceId: number;
  cycleId: number;
  weekNo: number;
  startDate?: string | null;
  endDate?: string | null;
  focus?: string | null;
  mission?: string | null;
}

export interface WeeklyCommitment {
  id: number;
  workspaceId: number;
  weeklyPlanId: number;
  initiativeId?: number | null;
  title: string;
  status: string;
  plannedEffort?: string | null;
  commitmentOwnerType?: string | null;
  executionMode?: string | null;
  createdAt: string;
}

export interface CreateWeeklyCommitmentRequest {
  workspaceId: number;
  weeklyPlanId: number;
  initiativeId?: number | null;
  title: string;
  plannedEffort?: string | null;
  commitmentOwnerType?: string | null;
  executionMode?: string | null;
}

// ─── 12-Week Cycles Endpoints ───

export const createCycle = api(
  { expose: true, method: "POST", path: "/operations/cycles" },
  async (req: CreateTwelveWeekCycleRequest): Promise<TwelveWeekCycle> => {
    if (!req.workspaceId) throw APIError.invalidArgument("workspaceId is required");

    const [row] = await db
      .insert(twelveWeekCycles)
      .values({
        workspaceId: BigInt(req.workspaceId),
        brainId: req.brainId ? BigInt(req.brainId) : null,
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
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      brainId: row.brainId ? Number(row.brainId) : null,
      projectId: row.projectId ? Number(row.projectId) : null,
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
);

export const listCycles = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/cycles" },
  async (params: { workspaceId: number }): Promise<{ cycles: TwelveWeekCycle[] }> => {
    const rows = await db
      .select()
      .from(twelveWeekCycles)
      .where(eq(twelveWeekCycles.workspaceId, BigInt(params.workspaceId)))
      .orderBy(desc(twelveWeekCycles.id));

    return {
      cycles: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        brainId: row.brainId ? Number(row.brainId) : null,
        projectId: row.projectId ? Number(row.projectId) : null,
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
      })),
    };
  }
);

// ─── Weekly Plans Endpoints ───

export const createWeeklyPlan = api(
  { expose: true, method: "POST", path: "/operations/weekly-plans" },
  async (req: CreateWeeklyPlanRequest): Promise<WeeklyPlan> => {
    if (!req.workspaceId || !req.cycleId || !req.weekNo) {
      throw APIError.invalidArgument("workspaceId, cycleId, and weekNo are required");
    }

    const [row] = await db
      .insert(weeklyPlans)
      .values({
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
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      cycleId: Number(row.cycleId),
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
);

// ─── Weekly Commitments Endpoints ───

export const createWeeklyCommitment = api(
  { expose: true, method: "POST", path: "/operations/weekly-commitments" },
  async (req: CreateWeeklyCommitmentRequest): Promise<WeeklyCommitment> => {
    if (!req.workspaceId || !req.weeklyPlanId || !req.title) {
      throw APIError.invalidArgument("workspaceId, weeklyPlanId, and title are required");
    }

    const [row] = await db
      .insert(weeklyCommitments)
      .values({
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
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      weeklyPlanId: Number(row.weeklyPlanId),
      initiativeId: row.initiativeId ? Number(row.initiativeId) : null,
      title: row.title,
      status: row.status,
      plannedEffort: row.plannedEffort,
      commitmentOwnerType: row.commitmentOwnerType,
      executionMode: row.executionMode,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
