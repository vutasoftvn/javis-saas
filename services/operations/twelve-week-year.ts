import { api, APIError } from "encore.dev/api";
import { SQLDatabase } from "encore.dev/storage/sqldb";

const db = SQLDatabase.named("operations");

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

    const row = await db.queryRow<TwelveWeekCycle>`
      INSERT INTO operating.twelve_week_cycles (
        workspace_id, brain_id, project_id, theme, vision_statement,
        stage_at_start, duration_weeks, start_date, end_date, commitment_level
      ) VALUES (
        ${req.workspaceId}, ${req.brainId ?? null}, ${req.projectId ?? null},
        ${req.theme ?? null}, ${req.visionStatement ?? ""},
        ${req.stageAtStart ?? "S1_PROBLEM_VALIDATION"}, ${req.durationWeeks ?? 12},
        ${req.startDate ?? null}, ${req.endDate ?? null}, ${req.commitmentLevel ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", brain_id as "brainId", project_id as "projectId",
        theme, vision_statement as "visionStatement", stage_at_start as "stageAtStart",
        current_week as "currentWeek", duration_weeks as "durationWeeks",
        overall_execution_score as "overallExecutionScore",
        start_date as "startDate", end_date as "endDate",
        commitment_level as "commitmentLevel", status, created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create twelve week cycle");
    return row;
  }
);

export const listCycles = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/cycles" },
  async (params: { workspaceId: number }): Promise<{ cycles: TwelveWeekCycle[] }> => {
    const rows = db.query<TwelveWeekCycle>`
      SELECT
        id, workspace_id as "workspaceId", brain_id as "brainId", project_id as "projectId",
        theme, vision_statement as "visionStatement", stage_at_start as "stageAtStart",
        current_week as "currentWeek", duration_weeks as "durationWeeks",
        overall_execution_score as "overallExecutionScore",
        start_date as "startDate", end_date as "endDate",
        commitment_level as "commitmentLevel", status, created_at as "createdAt"
      FROM operating.twelve_week_cycles
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY id DESC
    `;
    const cycles: TwelveWeekCycle[] = [];
    for await (const row of rows) cycles.push(row);
    return { cycles };
  }
);

// ─── Weekly Plans Endpoints ───

export const createWeeklyPlan = api(
  { expose: true, method: "POST", path: "/operations/weekly-plans" },
  async (req: CreateWeeklyPlanRequest): Promise<WeeklyPlan> => {
    if (!req.workspaceId || !req.cycleId || !req.weekNo) {
      throw APIError.invalidArgument("workspaceId, cycleId, and weekNo are required");
    }

    const row = await db.queryRow<WeeklyPlan>`
      INSERT INTO operating.weekly_plans (
        workspace_id, cycle_id, week_no, start_date, end_date, focus, mission
      ) VALUES (
        ${req.workspaceId}, ${req.cycleId}, ${req.weekNo},
        ${req.startDate ?? null}, ${req.endDate ?? null},
        ${req.focus ?? null}, ${req.mission ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", cycle_id as "cycleId", week_no as "weekNo",
        start_date as "startDate", end_date as "endDate",
        focus, mission, execution_score as "executionScore",
        outcome_score as "outcomeScore", reflection, created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create weekly plan");
    return row;
  }
);

// ─── Weekly Commitments Endpoints ───

export const createWeeklyCommitment = api(
  { expose: true, method: "POST", path: "/operations/weekly-commitments" },
  async (req: CreateWeeklyCommitmentRequest): Promise<WeeklyCommitment> => {
    if (!req.workspaceId || !req.weeklyPlanId || !req.title) {
      throw APIError.invalidArgument("workspaceId, weeklyPlanId, and title are required");
    }

    const row = await db.queryRow<WeeklyCommitment>`
      INSERT INTO operating.weekly_commitments (
        workspace_id, weekly_plan_id, initiative_id, title, planned_effort,
        commitment_owner_type, execution_mode
      ) VALUES (
        ${req.workspaceId}, ${req.weeklyPlanId}, ${req.initiativeId ?? null},
        ${req.title}, ${req.plannedEffort ?? null},
        ${req.commitmentOwnerType ?? "FOUNDER"}, ${req.executionMode ?? "MANUAL"}
      )
      RETURNING
        id, workspace_id as "workspaceId", weekly_plan_id as "weeklyPlanId",
        initiative_id as "initiativeId", title, status,
        planned_effort as "plannedEffort",
        commitment_owner_type as "commitmentOwnerType",
        execution_mode as "executionMode", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create weekly commitment");
    return row;
  }
);
