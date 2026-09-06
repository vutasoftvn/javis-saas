import { APIError } from "encore.dev/api";
import { eq, desc, and, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  validateDurationWeeks,
  validateLocalDateString,
  calculateCycleEndDateExclusive,
  getLocalDateFromInstant,
  addDaysToLocalDate,
} from "./execution-calendar";
import { assertInitiativeInWorkspace } from "./initiative.service";
import {
  scheduleInitialCycleReviews,
  rescheduleCycleReviews,
} from "../strategy/services/cycle-review.service";
import { getWorkspaceStrategySettings } from "../strategy/services/workspace-strategy-settings.service";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, cycleRevisions, cycleReviews } = schema;


export interface TwelveWeekCycle {
  id: string;
  workspaceId: string;
  projectId?: string | null;
  displayName?: string | null;
  theme?: string | null;
  visionStatement: string;
  stageAtStart: string;
  currentWeek: number;
  durationWeeks: number;
  overallExecutionScore: number;
  timezone: string;
  startLocalDate?: string | null;
  endLocalDateExclusive?: string | null;
  revision: number;
  calendarState: string;
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
  displayName?: string | null;
  theme?: string | null;
  visionStatement?: string;
  stageAtStart?: string;
  durationWeeks?: number;
  timezone?: string | null;
  startLocalDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  commitmentLevel?: string | null;
}

export interface UpdateTwelveWeekCycleRequest {
  workspaceId: string | number;
  cycleId: string | number;
  authorization?: string;
  expectedVersion?: number;
  displayName?: string | null;
  theme?: string | null;
  visionStatement?: string;
  durationWeeks?: number;
  startLocalDate?: string | null;
  timezone?: string | null;
  status?: string;
  reason?: string | null;
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
  sourceActionId?: string | null;
  sourceRevision?: number;
  revision?: number;
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
    displayName: row.displayName,
    theme: row.theme,
    visionStatement: row.visionStatement,
    stageAtStart: row.stageAtStart,
    currentWeek: row.currentWeek,
    durationWeeks: row.durationWeeks,
    overallExecutionScore: row.overallExecutionScore,
    timezone: row.timezone ?? "UTC",
    startLocalDate: row.startLocalDate ? String(row.startLocalDate) : null,
    endLocalDateExclusive: row.endLocalDateExclusive ? String(row.endLocalDateExclusive) : null,
    revision: row.revision ?? 1,
    calendarState: row.calendarState ?? "READY",
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

  const durationWeeks = req.durationWeeks ?? 12;
  validateDurationWeeks(durationWeeks);

  const timezone = (req.timezone && req.timezone.trim()) || "UTC";
  let startLocalDate: string | null = null;
  let endLocalDateExclusive: string | null = null;
  let calendarState: string = "NEEDS_SETUP";

  if (req.startLocalDate && req.startLocalDate.trim()) {
    const cleanDate = req.startLocalDate.trim();
    validateLocalDateString(cleanDate);
    startLocalDate = cleanDate;
    endLocalDateExclusive = calculateCycleEndDateExclusive(startLocalDate, durationWeeks);
    calendarState = "READY";
  } else if (req.startDate) {
    const parsed = new Date(req.startDate);
    if (!Number.isNaN(parsed.getTime())) {
      startLocalDate = getLocalDateFromInstant(parsed, timezone);
      endLocalDateExclusive = calculateCycleEndDateExclusive(startLocalDate, durationWeeks);
      calendarState = "READY";
    }
  }

  const [row] = await db.transaction(async (tx) => {
    const [inserted] = await tx
      .insert(twelveWeekCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(req.workspaceId),
        projectId: req.projectId ? BigInt(req.projectId) : null,
        displayName: req.displayName || null,
        theme: req.theme || null,
        visionStatement: req.visionStatement ?? "",
        stageAtStart: req.stageAtStart ?? "S1_PROBLEM_VALIDATION",
        durationWeeks,
        timezone,
        startLocalDate: startLocalDate || null,
        endLocalDateExclusive: endLocalDateExclusive || null,
        revision: 1,
        calendarState,
        startDate: req.startDate ? new Date(req.startDate) : (startLocalDate ? new Date(startLocalDate + "T00:00:00Z") : null),
        endDate: req.endDate ? new Date(req.endDate) : (endLocalDateExclusive ? new Date(endLocalDateExclusive + "T00:00:00Z") : null),
        commitmentLevel: req.commitmentLevel || null,
      })
      .returning();

    if (!inserted) throw APIError.internal("Failed to create twelve week cycle");

    await scheduleInitialCycleReviews(tx, {
      id: inserted.id,
      workspaceId: inserted.workspaceId,
      projectId: inserted.projectId,
      durationWeeks: inserted.durationWeeks,
      startLocalDate: inserted.startLocalDate ? String(inserted.startLocalDate) : null,
      timezone: inserted.timezone,
    });

    return [inserted];
  });

  if (!row) throw APIError.internal("Failed to create twelve week cycle");
  return toCycle(row);
}

export async function updateCycleService(req: UpdateTwelveWeekCycleRequest): Promise<TwelveWeekCycle> {
  if (!req.workspaceId || !req.cycleId) throw APIError.invalidArgument("workspaceId and cycleId are required");
  const ctx = await requireWorkspaceAccess(req.authorization, String(req.workspaceId));
  const wsId = BigInt(ctx.workspaceId);
  const cycleIdBig = BigInt(req.cycleId);

  const [existing] = await db
    .select()
    .from(twelveWeekCycles)
    .where(and(eq(twelveWeekCycles.id, cycleIdBig), eq(twelveWeekCycles.workspaceId, wsId), isNull(twelveWeekCycles.deletedAt)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`Cycle ${req.cycleId} not found`);
  }

  if (req.expectedVersion !== undefined && existing.revision !== req.expectedVersion) {
    throw APIError.failedPrecondition(
      `Cycle revision conflict: expected ${req.expectedVersion}, current is ${existing.revision}`
    );
  }

  const nextDuration = req.durationWeeks ?? existing.durationWeeks;
  if (req.durationWeeks !== undefined && req.durationWeeks !== existing.durationWeeks) {
    if (
      (ctx as any).actorKind === "AI_AGENT" ||
      (ctx as any).isAgent === true ||
      ctx.membershipRole === "agent"
    ) {
      throw APIError.permissionDenied("Agents cannot resize execution cycles; human approval required");
    }
  }
  validateDurationWeeks(nextDuration);

  const nextTimezone = req.timezone ?? existing.timezone ?? "UTC";
  let nextStartLocal = existing.startLocalDate ? String(existing.startLocalDate) : null;
  if (req.startLocalDate !== undefined) {
    if (req.startLocalDate) {
      validateLocalDateString(req.startLocalDate.trim());
      nextStartLocal = req.startLocalDate.trim();
    } else {
      nextStartLocal = null;
    }
  }

  let nextEndLocalExclusive: string | null = null;
  let nextCalendarState = existing.calendarState;
  if (nextStartLocal) {
    nextEndLocalExclusive = calculateCycleEndDateExclusive(nextStartLocal, nextDuration);
    nextCalendarState = "READY";
  } else {
    nextCalendarState = "NEEDS_SETUP";
  }

  const nextRevision = (existing.revision ?? 1) + 1;
  const beforeState = {
    displayName: existing.displayName,
    durationWeeks: existing.durationWeeks,
    startLocalDate: existing.startLocalDate,
    endLocalDateExclusive: existing.endLocalDateExclusive,
    revision: existing.revision,
    calendarState: existing.calendarState,
    timezone: existing.timezone,
    status: existing.status,
  };

  const afterState = {
    displayName: req.displayName !== undefined ? req.displayName : existing.displayName,
    durationWeeks: nextDuration,
    startLocalDate: nextStartLocal,
    endLocalDateExclusive: nextEndLocalExclusive,
    revision: nextRevision,
    calendarState: nextCalendarState,
    timezone: nextTimezone,
    status: req.status !== undefined ? req.status : existing.status,
  };

  const [updated] = await db.transaction(async (tx) => {
    if (
      nextDuration !== existing.durationWeeks ||
      nextStartLocal !== (existing.startLocalDate ? String(existing.startLocalDate) : null)
    ) {
      const beforeReviews = await tx
        .select()
        .from(cycleReviews)
        .where(
          and(
            eq(cycleReviews.cycleId, cycleIdBig),
            eq(cycleReviews.workspaceId, wsId),
            isNull(cycleReviews.deletedAt)
          )
        );

      const settings = await getWorkspaceStrategySettings(wsId);
      await rescheduleCycleReviews(
        tx,
        cycleIdBig,
        wsId,
        existing.durationWeeks,
        nextDuration,
        settings,
        nextStartLocal,
        nextTimezone
      );

      const afterReviews = await tx
        .select()
        .from(cycleReviews)
        .where(
          and(
            eq(cycleReviews.cycleId, cycleIdBig),
            eq(cycleReviews.workspaceId, wsId),
            isNull(cycleReviews.deletedAt)
          )
        );

      (beforeState as any).reviewSchedule = beforeReviews.map((r: any) => ({
        id: String(r.id),
        kind: r.kind,
        scheduledWeekNo: r.scheduledWeekNo,
        status: r.status,
      }));
      (afterState as any).reviewSchedule = afterReviews.map((r: any) => ({
        id: String(r.id),
        kind: r.kind,
        scheduledWeekNo: r.scheduledWeekNo,
        status: r.status,
      }));
    }

    await tx.insert(cycleRevisions).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      cycleId: cycleIdBig,
      revision: nextRevision,
      beforeState,
      afterState,
      reason: req.reason || null,
      actorId: ctx.userId || null,
      actorKind: "user",
    });

    return await tx
      .update(twelveWeekCycles)
      .set({
        displayName: req.displayName !== undefined ? req.displayName : existing.displayName,
        theme: req.theme !== undefined ? req.theme : existing.theme,
        visionStatement: req.visionStatement !== undefined ? req.visionStatement : existing.visionStatement,
        durationWeeks: nextDuration,
        timezone: nextTimezone,
        startLocalDate: nextStartLocal || null,
        endLocalDateExclusive: nextEndLocalExclusive || null,
        revision: nextRevision,
        calendarState: nextCalendarState,
        status: req.status !== undefined ? req.status : existing.status,
        updatedAt: new Date(),
      })
      .where(and(eq(twelveWeekCycles.id, cycleIdBig), eq(twelveWeekCycles.workspaceId, wsId)))
      .returning();
  });

  return toCycle(updated!);
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
  const wsId = BigInt(req.workspaceId);
  const cycleIdBig = BigInt(req.cycleId);

  const [cycle] = await db
    .select()
    .from(twelveWeekCycles)
    .where(and(eq(twelveWeekCycles.id, cycleIdBig), eq(twelveWeekCycles.workspaceId, wsId), isNull(twelveWeekCycles.deletedAt)))
    .limit(1);

  if (!cycle) {
    throw APIError.notFound(`Cycle ${req.cycleId} not found`);
  }

  if (req.weekNo < 1 || req.weekNo > cycle.durationWeeks) {
    throw APIError.invalidArgument(
      `weekNo ${req.weekNo} is outside cycle duration of ${cycle.durationWeeks} weeks`
    );
  }

  const [existingPlan] = await db
    .select()
    .from(weeklyPlans)
    .where(and(eq(weeklyPlans.cycleId, cycleIdBig), eq(weeklyPlans.weekNo, req.weekNo), eq(weeklyPlans.workspaceId, wsId)))
    .limit(1);

  if (existingPlan) {
    throw APIError.alreadyExists(`Weekly plan for week ${req.weekNo} already exists in this cycle`);
  }

  let startDate: Date | null = req.startDate ? new Date(req.startDate) : null;
  let endDate: Date | null = req.endDate ? new Date(req.endDate) : null;

  if (cycle.startLocalDate && (!startDate || !endDate)) {
    const startStr = String(cycle.startLocalDate);
    const weekStartLocal = addDaysToLocalDate(startStr, (req.weekNo - 1) * 7);
    const weekEndLocal = addDaysToLocalDate(startStr, req.weekNo * 7);
    if (!startDate) startDate = new Date(weekStartLocal + "T00:00:00Z");
    if (!endDate) endDate = new Date(weekEndLocal + "T00:00:00Z");
  }

  const [row] = await db
    .insert(weeklyPlans)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      cycleId: cycleIdBig,
      weekNo: req.weekNo,
      startDate,
      endDate,
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

export interface UpdateWeeklyPlanRequest {
  workspaceId: string | number;
  authorization?: string;
  executionScore?: number | null;
  outcomeScore?: number | null;
  reflection?: string | null;
}

export async function updateWeeklyPlanService(
  planId: string,
  req: UpdateWeeklyPlanRequest
): Promise<WeeklyPlan> {
  const ctx = await requireWorkspaceAccess(req.authorization, String(req.workspaceId));
  const wsId = BigInt(ctx.workspaceId);
  const planIdBig = BigInt(planId);

  if (req.executionScore !== undefined && req.executionScore !== null) {
    if (req.executionScore < 0 || req.executionScore > 100) {
      throw APIError.invalidArgument("executionScore must be between 0 and 100");
    }
  }
  if (req.outcomeScore !== undefined && req.outcomeScore !== null) {
    if (req.outcomeScore < 0 || req.outcomeScore > 100) {
      throw APIError.invalidArgument("outcomeScore must be between 0 and 100");
    }
  }

  const [existing] = await db
    .select()
    .from(weeklyPlans)
    .where(and(eq(weeklyPlans.id, planIdBig), eq(weeklyPlans.workspaceId, wsId)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`weekly plan ${planId} not found`);
  }

  const [updated] = await db
    .update(weeklyPlans)
    .set({
      executionScore: req.executionScore !== undefined ? req.executionScore : existing.executionScore,
      outcomeScore: req.outcomeScore !== undefined ? req.outcomeScore : existing.outcomeScore,
      reflection: req.reflection !== undefined ? req.reflection : existing.reflection,
      updatedAt: new Date(),
    })
    .where(and(eq(weeklyPlans.id, planIdBig), eq(weeklyPlans.workspaceId, wsId)))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    cycleId: updated.cycleId.toString(),
    weekNo: updated.weekNo,
    startDate: updated.startDate ? updated.startDate.toISOString() : null,
    endDate: updated.endDate ? updated.endDate.toISOString() : null,
    focus: updated.focus,
    mission: updated.mission,
    executionScore: updated.executionScore,
    outcomeScore: updated.outcomeScore,
    reflection: updated.reflection,
    createdAt: updated.createdAt.toISOString(),
  };
}

export async function createWeeklyCommitmentService(req: CreateWeeklyCommitmentRequest): Promise<WeeklyCommitment> {
  if (!req.workspaceId || !req.weeklyPlanId || !req.title) {
    throw APIError.invalidArgument("workspaceId, weeklyPlanId, and title are required");
  }
  await requireWorkspaceAccess(req.authorization, String(req.workspaceId));

  if (req.initiativeId) {
    await assertInitiativeInWorkspace(req.initiativeId, req.workspaceId, true);
  }

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
    .where(and(eq(weeklyCommitments.workspaceId, wsId), isNull(weeklyCommitments.deletedAt)))
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
