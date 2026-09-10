import { APIError } from "encore.dev/api";
import { eq, and, isNull, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { Project } from "./project.service";

const {
  projects,
  okrObjectives,
  keyResults,
  initiatives,
  twelveWeekCycles,
  weeklyPlans,
  weeklyCommitments,
  tasks,
} = schema;

export interface OkrObjectiveDto {
  id: string;
  workspaceId: string;
  projectId: string;
  title: string;
  why?: string | null;
  ownerMemberId?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface KeyResultDto {
  id: string;
  workspaceId: string;
  objectiveId: string;
  title: string | null;
  metricId?: string | null;
  baselineValue?: number | null;
  currentValue?: number | null;
  targetValue?: number | null;
  unit?: string | null;
  cadence?: string | null;
  metricType?: string | null;
  scoringType: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface InitiativeDto {
  id: string;
  workspaceId: string;
  projectId: string;
  keyResultId: string;
  title: string;
  status: string;
  ownerMemberId?: string | null;
  description?: string | null;
  intendedOutcome?: string | null;
  startDate?: string | null;
  targetDate?: string | null;
  approvalStatus: string;
  createdAt: string;
  updatedAt: string;
}

export interface CycleDto {
  id: string;
  workspaceId: string;
  projectId: string;
  currentWeek: number;
  durationWeeks: number;
  theme?: string | null;
  visionStatement: string;
  status: string;
  timezone: string;
  startLocalDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface WeeklyPlanDto {
  id: string;
  workspaceId: string;
  projectId: string;
  cycleId: string;
  weekNo: number;
  focus?: string | null;
  mission?: string | null;
  executionScore?: number | null;
  outcomeScore?: number | null;
  reflection?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface WeeklyCommitmentDto {
  id: string;
  workspaceId: string;
  projectId: string;
  weeklyPlanId: string;
  initiativeId?: string | null;
  title: string;
  status: string;
  plannedEffort?: string | null;
  purposeType: string;
  purposeRef?: string | null;
  ownerMemberId?: string | null;
  executionMode?: string | null;
  committedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TaskDto {
  id: string;
  workspaceId: string;
  projectId: string;
  weeklyCommitmentId?: string | null;
  initiativeId?: string | null;
  title: string;
  status: string;
  priority: string;
  plannedStartAt?: string | null;
  dueAt?: string | null;
  timezone: string;
  assigneeMemberId?: string | null;
  executionMode?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectOperatingLoop {
  project: Project;
  activeCycle: CycleDto | null;
  currentWeek: WeeklyPlanDto | null;
  commitments: WeeklyCommitmentDto[];
  objectives: Array<{
    objective: OkrObjectiveDto;
    keyResults: Array<{
      keyResult: KeyResultDto;
      initiatives: InitiativeDto[];
    }>;
  }>;
  tasks: TaskDto[];
}

function toProject(row: typeof projects.$inferSelect): Project {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    description: row.description,
    lifecycleStage: row.lifecycleStage,
    stageEnteredAt: row.stageEnteredAt ? row.stageEnteredAt.toISOString() : null,
    status: row.status,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    projectType: row.projectType,
    strategicPriority: row.strategicPriority,
    portfolioId: row.portfolioId ? row.portfolioId.toString() : null,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

function toObjective(row: typeof okrObjectives.$inferSelect): OkrObjectiveDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    title: row.title,
    why: row.why,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toKeyResult(row: typeof keyResults.$inferSelect): KeyResultDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    objectiveId: row.objectiveId.toString(),
    title: row.title,
    metricId: row.metricId ? row.metricId.toString() : null,
    baselineValue: row.baselineValue,
    currentValue: row.currentValue,
    targetValue: row.targetValue,
    unit: row.unit,
    cadence: row.cadence,
    metricType: row.metricType,
    scoringType: row.scoringType,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toInitiative(row: typeof initiatives.$inferSelect): InitiativeDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    keyResultId: row.keyResultId.toString(),
    title: row.title,
    status: row.status,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    description: row.description,
    intendedOutcome: row.intendedOutcome,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    targetDate: row.targetDate ? row.targetDate.toISOString() : null,
    approvalStatus: row.approvalStatus,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toCycle(row: typeof twelveWeekCycles.$inferSelect): CycleDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    currentWeek: row.currentWeek,
    durationWeeks: row.durationWeeks,
    theme: row.theme,
    visionStatement: row.visionStatement,
    status: row.status,
    timezone: row.timezone,
    startLocalDate: row.startLocalDate ? row.startLocalDate.toString() : null,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toWeeklyPlan(row: typeof weeklyPlans.$inferSelect): WeeklyPlanDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    cycleId: row.cycleId.toString(),
    weekNo: row.weekNo,
    focus: row.focus,
    mission: row.mission,
    executionScore: row.executionScore,
    outcomeScore: row.outcomeScore,
    reflection: row.reflection,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toWeeklyCommitment(row: typeof weeklyCommitments.$inferSelect): WeeklyCommitmentDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    weeklyPlanId: row.weeklyPlanId.toString(),
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    title: row.title,
    status: row.status,
    plannedEffort: row.plannedEffort,
    purposeType: row.purposeType,
    purposeRef: row.purposeRef,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    executionMode: row.executionMode,
    committedAt: row.committedAt ? row.committedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toTask(row: typeof tasks.$inferSelect): TaskDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    weeklyCommitmentId: row.weeklyCommitmentId ? row.weeklyCommitmentId.toString() : null,
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    title: row.title,
    status: row.status,
    priority: row.priority,
    plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
    dueAt: row.dueAt ? row.dueAt.toISOString() : null,
    timezone: row.timezone,
    assigneeMemberId: row.assigneeMemberId ? row.assigneeMemberId.toString() : null,
    executionMode: row.executionMode,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function verifyProjectInWorkspace(wsId: bigint, pId: bigint) {
  const [project] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)));
  if (!project) {
    throw APIError.notFound("Project not found in workspace");
  }
  return project;
}

export async function createObjectiveAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    title: string;
    why?: string | null;
    ownerMemberId?: string | null;
  }
): Promise<OkrObjectiveDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  await verifyProjectInWorkspace(wsId, pId);

  if (!req.title || !req.title.trim()) {
    throw APIError.invalidArgument("title is required");
  }

  const [row] = await db
    .insert(okrObjectives)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      title: req.title.trim(),
      why: req.why || null,
      ownerMemberId: req.ownerMemberId ? BigInt(req.ownerMemberId) : null,
      status: "draft",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create objective");
  return toObjective(row);
}

export async function createKeyResultAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    objectiveId: string;
    title: string;
    metricId?: string | null;
    targetValue?: number | null;
    unit?: string | null;
  }
): Promise<KeyResultDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const objId = BigInt(req.objectiveId);
  await verifyProjectInWorkspace(wsId, pId);

  const [obj] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, objId), eq(okrObjectives.workspaceId, wsId), eq(okrObjectives.projectId, pId)));

  if (!obj) {
    throw APIError.invalidArgument("Objective does not belong to project/workspace");
  }

  const [row] = await db
    .insert(keyResults)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      objectiveId: objId,
      title: req.title,
      metricId: req.metricId ? BigInt(req.metricId) : null,
      targetValue: req.targetValue ?? null,
      unit: req.unit || null,
      scoringType: "LINEAR_INCREASE",
      status: "draft",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create key result");
  return toKeyResult(row);
}

export async function createInitiativeAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    keyResultId: string;
    title: string;
    description?: string | null;
    intendedOutcome?: string | null;
    ownerMemberId?: string | null;
  }
): Promise<InitiativeDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const krId = BigInt(req.keyResultId);
  await verifyProjectInWorkspace(wsId, pId);

  const [krWithObj] = await db
    .select({ kr: keyResults, obj: okrObjectives })
    .from(keyResults)
    .innerJoin(okrObjectives, eq(keyResults.objectiveId, okrObjectives.id))
    .where(
      and(
        eq(keyResults.id, krId),
        eq(keyResults.workspaceId, wsId),
        eq(okrObjectives.projectId, pId)
      )
    );

  if (!krWithObj) {
    throw APIError.invalidArgument("Key result does not belong to the specified project and workspace");
  }

  const [row] = await db
    .insert(initiatives)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      keyResultId: krId,
      title: req.title,
      description: req.description || null,
      intendedOutcome: req.intendedOutcome || null,
      ownerMemberId: req.ownerMemberId ? BigInt(req.ownerMemberId) : null,
      status: "active",
      approvalStatus: "DRAFT",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create initiative");
  return toInitiative(row);
}

export async function createCycleAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    theme?: string | null;
    visionStatement?: string | null;
    durationWeeks?: number;
    timezone?: string;
    startLocalDate?: string;
    startDate?: string;
    endDate?: string;
  }
): Promise<CycleDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  await verifyProjectInWorkspace(wsId, pId);

  const durationWeeks = req.durationWeeks ?? 12;
  if (durationWeeks < 1 || durationWeeks > 12) {
    throw APIError.invalidArgument("duration_weeks must be between 1 and 12");
  }

  const [existingActive] = await db
    .select()
    .from(twelveWeekCycles)
    .where(
      and(
        eq(twelveWeekCycles.workspaceId, wsId),
        eq(twelveWeekCycles.projectId, pId),
        eq(twelveWeekCycles.status, "ACTIVE"),
        isNull(twelveWeekCycles.deletedAt)
      )
    );

  if (existingActive) {
    throw APIError.failedPrecondition("Project already has an active operating cycle");
  }

  const [row] = await db
    .insert(twelveWeekCycles)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      theme: req.theme || null,
      visionStatement: req.visionStatement || "",
      durationWeeks,
      timezone: req.timezone || "UTC",
      status: "ACTIVE",
      startLocalDate: req.startLocalDate || null,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create operating cycle");
  return toCycle(row);
}

export async function createWeeklyPlanAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    cycleId: string;
    weekNo: number;
    focus?: string | null;
    mission?: string | null;
    startDate?: string;
    endDate?: string;
  }
): Promise<WeeklyPlanDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const cycleId = BigInt(req.cycleId);
  await verifyProjectInWorkspace(wsId, pId);

  const [cycle] = await db
    .select()
    .from(twelveWeekCycles)
    .where(
      and(
        eq(twelveWeekCycles.id, cycleId),
        eq(twelveWeekCycles.workspaceId, wsId),
        eq(twelveWeekCycles.projectId, pId)
      )
    );

  if (!cycle) {
    throw APIError.invalidArgument("Cycle does not belong to project/workspace");
  }

  if (req.weekNo < 1 || req.weekNo > cycle.durationWeeks) {
    throw APIError.invalidArgument("week_no must be within cycle duration");
  }

  const [row] = await db
    .insert(weeklyPlans)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      cycleId,
      weekNo: req.weekNo,
      focus: req.focus || null,
      mission: req.mission || null,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create weekly plan");
  return toWeeklyPlan(row);
}

export async function createWeeklyCommitmentAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    weeklyPlanId: string;
    title: string;
    initiativeId?: string | null;
    plannedEffort?: string | null;
    ownerMemberId?: string | null;
    purposeType?: string;
    purposeRef?: string | null;
  }
): Promise<WeeklyCommitmentDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const planId = BigInt(req.weeklyPlanId);
  await verifyProjectInWorkspace(wsId, pId);

  const [plan] = await db
    .select()
    .from(weeklyPlans)
    .where(
      and(
        eq(weeklyPlans.id, planId),
        eq(weeklyPlans.workspaceId, wsId),
        eq(weeklyPlans.projectId, pId)
      )
    );

  if (!plan) {
    throw APIError.invalidArgument("Weekly plan does not belong to project/workspace");
  }

  let initiativeId: bigint | null = null;
  if (req.initiativeId) {
    initiativeId = BigInt(req.initiativeId);
    const [init] = await db
      .select()
      .from(initiatives)
      .where(
        and(
          eq(initiatives.id, initiativeId),
          eq(initiatives.workspaceId, wsId),
          eq(initiatives.projectId, pId)
        )
      );
    if (!init) {
      throw APIError.invalidArgument("Initiative does not belong to project/workspace");
    }
  }

  const [row] = await db
    .insert(weeklyCommitments)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      weeklyPlanId: planId,
      initiativeId,
      title: req.title,
      plannedEffort: req.plannedEffort || null,
      purposeType: req.purposeType || "KR",
      purposeRef: req.purposeRef || null,
      ownerMemberId: req.ownerMemberId ? BigInt(req.ownerMemberId) : null,
      status: "todo",
      committedAt: new Date(),
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create weekly commitment");
  return toWeeklyCommitment(row);
}

export async function createTaskAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    title: string;
    weeklyCommitmentId?: string | null;
    initiativeId?: string | null;
    priority?: string;
    plannedStartAt?: string;
    dueAt?: string;
    status?: string;
  }
): Promise<TaskDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  await verifyProjectInWorkspace(wsId, pId);

  let weeklyCommitmentId: bigint | null = null;
  if (req.weeklyCommitmentId) {
    weeklyCommitmentId = BigInt(req.weeklyCommitmentId);
    const [com] = await db
      .select()
      .from(weeklyCommitments)
      .where(
        and(
          eq(weeklyCommitments.id, weeklyCommitmentId),
          eq(weeklyCommitments.workspaceId, wsId),
          eq(weeklyCommitments.projectId, pId)
        )
      );
    if (!com) {
      throw APIError.invalidArgument("Weekly commitment does not belong to project/workspace");
    }
  }

  let initiativeId: bigint | null = null;
  if (req.initiativeId) {
    initiativeId = BigInt(req.initiativeId);
    const [init] = await db
      .select()
      .from(initiatives)
      .where(
        and(
          eq(initiatives.id, initiativeId),
          eq(initiatives.workspaceId, wsId),
          eq(initiatives.projectId, pId)
        )
      );
    if (!init) {
      throw APIError.invalidArgument("Initiative does not belong to project/workspace");
    }
  }

  const initialStatus = req.status || "todo";
  if (
    (initialStatus === "IN_PROGRESS" || initialStatus === "in_progress") &&
    !weeklyCommitmentId
  ) {
    throw APIError.failedPrecondition("Task must belong to an active weekly commitment before it can start");
  }

  const [row] = await db
    .insert(tasks)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      weeklyCommitmentId,
      initiativeId,
      title: req.title,
      status: initialStatus,
      priority: req.priority || "medium",
      plannedStartAt: req.plannedStartAt ? new Date(req.plannedStartAt) : null,
      dueAt: req.dueAt ? new Date(req.dueAt) : null,
      timezone: "UTC",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create task");
  return toTask(row);
}

export async function advanceTaskService(
  ctx: TenantContext,
  req: {
    taskId: string;
    status: string;
  }
): Promise<TaskDto> {
  const wsId = BigInt(ctx.workspaceId);
  const taskId = BigInt(req.taskId);

  const [task] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)));

  if (!task) {
    throw APIError.notFound("Task not found");
  }

  const nextStatus = req.status;
  if (
    (nextStatus === "IN_PROGRESS" || nextStatus === "in_progress") &&
    task.weeklyCommitmentId === null
  ) {
    throw APIError.failedPrecondition("Task must belong to an active weekly commitment before it can start");
  }

  const [updated] = await db
    .update(tasks)
    .set({
      status: nextStatus,
      updatedAt: new Date(),
    })
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)))
    .returning();

  if (!updated) throw APIError.internal("Failed to update task");
  return toTask(updated);
}

export async function getProjectOperatingLoop(
  ctx: TenantContext,
  projectId: string
): Promise<ProjectOperatingLoop> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  const projectRow = await verifyProjectInWorkspace(wsId, pId);

  // Active cycle
  const [activeCycleRow] = await db
    .select()
    .from(twelveWeekCycles)
    .where(
      and(
        eq(twelveWeekCycles.workspaceId, wsId),
        eq(twelveWeekCycles.projectId, pId),
        eq(twelveWeekCycles.status, "ACTIVE"),
        isNull(twelveWeekCycles.deletedAt)
      )
    );

  let currentWeekPlan: WeeklyPlanDto | null = null;
  let commitmentsList: WeeklyCommitmentDto[] = [];

  if (activeCycleRow) {
    const [currentWeekRow] = await db
      .select()
      .from(weeklyPlans)
      .where(
        and(
          eq(weeklyPlans.workspaceId, wsId),
          eq(weeklyPlans.projectId, pId),
          eq(weeklyPlans.cycleId, activeCycleRow.id),
          eq(weeklyPlans.weekNo, activeCycleRow.currentWeek),
          isNull(weeklyPlans.deletedAt)
        )
      );

    if (currentWeekRow) {
      currentWeekPlan = toWeeklyPlan(currentWeekRow);
      const commitmentRows = await db
        .select()
        .from(weeklyCommitments)
        .where(
          and(
            eq(weeklyCommitments.workspaceId, wsId),
            eq(weeklyCommitments.projectId, pId),
            eq(weeklyCommitments.weeklyPlanId, currentWeekRow.id),
            isNull(weeklyCommitments.deletedAt)
          )
        );
      commitmentsList = commitmentRows.map(toWeeklyCommitment);
    }
  }

  // Objectives, Key Results, Initiatives
  const objRows = await db
    .select()
    .from(okrObjectives)
    .where(
      and(
        eq(okrObjectives.workspaceId, wsId),
        eq(okrObjectives.projectId, pId),
        isNull(okrObjectives.deletedAt)
      )
    );

  const objIds = objRows.map((o) => o.id);
  let krRows: (typeof keyResults.$inferSelect)[] = [];
  if (objIds.length > 0) {
    krRows = await db
      .select()
      .from(keyResults)
      .where(
        and(
          eq(keyResults.workspaceId, wsId),
          isNull(keyResults.deletedAt)
        )
      );
  }

  const initiativeRows = await db
    .select()
    .from(initiatives)
    .where(
      and(
        eq(initiatives.workspaceId, wsId),
        eq(initiatives.projectId, pId),
        isNull(initiatives.deletedAt)
      )
    );

  const objectivesHierarchy = objRows.map((obj) => {
    const krsForObj = krRows.filter((kr) => kr.objectiveId === obj.id);
    return {
      objective: toObjective(obj),
      keyResults: krsForObj.map((kr) => {
        const initsForKr = initiativeRows.filter((init) => init.keyResultId === kr.id);
        return {
          keyResult: toKeyResult(kr),
          initiatives: initsForKr.map(toInitiative),
        };
      }),
    };
  });

  // Tasks
  const taskRows = await db
    .select()
    .from(tasks)
    .where(
      and(
        eq(tasks.workspaceId, wsId),
        eq(tasks.projectId, pId),
        isNull(tasks.deletedAt)
      )
    )
    .orderBy(desc(tasks.createdAt));

  return {
    project: toProject(projectRow),
    activeCycle: activeCycleRow ? toCycle(activeCycleRow) : null,
    currentWeek: currentWeekPlan,
    commitments: commitmentsList,
    objectives: objectivesHierarchy,
    tasks: taskRows.map(toTask),
  };
}
