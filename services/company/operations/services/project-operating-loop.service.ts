import { APIError } from "encore.dev/api";
import { eq, and, isNull, desc, inArray } from "drizzle-orm";
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
  cycleWeekEvents,
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
  // OKR→Weekly generator (Task 5): cycle sinh ra từ 1 Objective đã publish —
  // null khi cycle được tạo thủ công (không qua generator).
  sourceObjectiveId?: string | null;
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

// Task 5 (2026-09-14 remediation) — 1 entry timeline append-only cho state
// machine Weekly. `payload` chỉ mang dữ liệu mô tả (vd. reflection/scores lúc
// WEEK_CLOSED); không phải nguồn sự thật cho currentWeek/status — nguồn sự
// thật luôn là row `twelveWeekCycles`/`weeklyPlans` hiện tại.
export interface CycleWeekEventDto {
  id: string;
  workspaceId: string;
  projectId: string;
  cycleId: string;
  weekNo: number;
  eventType: string;
  actorId?: string | null;
  expectedCurrentWeek: number;
  payload?: unknown;
  occurredAt: string;
}

export interface AdvanceCycleWeekResultDto {
  cycle: CycleDto;
  week: WeeklyPlanDto;
  event: CycleWeekEventDto;
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
  // Denormalized lúc tạo task (xem task.service.ts) từ weeklyCommitment/
  // initiative — cho phép đọc trực tiếp task theo tuần/KR mà không cần join.
  weeklyPlanId?: string | null;
  keyResultId?: string | null;
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
    // Task 13 (frontend) — giữ đồng bộ với toProject() trong project.service.ts.
    stageVersion: row.stageVersion,
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
    sourceObjectiveId: row.sourceObjectiveId ? row.sourceObjectiveId.toString() : null,
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

function toCycleWeekEvent(row: typeof cycleWeekEvents.$inferSelect): CycleWeekEventDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    cycleId: row.cycleId.toString(),
    weekNo: row.weekNo,
    eventType: row.eventType,
    actorId: row.actorId ? row.actorId.toString() : null,
    expectedCurrentWeek: row.expectedCurrentWeek,
    payload: row.payload ?? null,
    occurredAt: row.occurredAt.toISOString(),
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
    weeklyPlanId: row.weeklyPlanId ? row.weeklyPlanId.toString() : null,
    keyResultId: row.keyResultId ? row.keyResultId.toString() : null,
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
    // Fix (2026-09-15) — trước đây 2 field này không có cách nào set qua API
    // công khai, khiến publishObjectiveService (yêu cầu cả 2 non-null) luôn
    // reject bất kỳ Key Result nào tạo qua endpoint này. Default 0 khi không
    // truyền, giống cách `scoringType` đã default "LINEAR_INCREASE" ở dưới.
    baselineValue?: number | null;
    currentValue?: number | null;
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
      baselineValue: req.baselineValue ?? 0,
      currentValue: req.currentValue ?? 0,
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
    // Task 5 (2026-09-14 remediation) — cho phép gắn sourceObjectiveId ngay
    // lúc tạo, thay vì tạo-rồi-update riêng lẻ như okr-weekly-generator cũ
    // (2 bước đó tạo ra 1 khoảng hở nơi cycle tồn tại mà chưa gắn objective).
    sourceObjectiveId?: string | null;
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

  // Task 5 — cycle + toàn bộ weekly_plans rỗng (tuần 1..durationWeeks) phải
  // xuất hiện cùng lúc trong 1 transaction: không có trạng thái quan sát được
  // từ bên ngoài nơi cycle tồn tại nhưng thiếu tuần nào. Trước đây caller
  // (vd. okr-weekly-generator) tự lặp gọi createWeeklyPlanAuthorized N lần
  // sau khi cycle đã commit — 2 bước tách rời, không atomic.
  return db.transaction(async (tx) => {
    const [row] = await tx
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
        sourceObjectiveId: req.sourceObjectiveId ? BigInt(req.sourceObjectiveId) : null,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create operating cycle");

    await tx.insert(weeklyPlans).values(
      Array.from({ length: durationWeeks }, (_unused, i) => ({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: pId,
        cycleId: row.id,
        weekNo: i + 1,
      }))
    );

    return toCycle(row);
  });
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

  // Task 5 (2026-09-14 remediation) — createCycleAuthorized giờ tự
  // materialize toàn bộ weekly_plans 1..durationWeeks lúc tạo cycle, nên tại
  // đây hầu như luôn có sẵn đúng 1 row cho (cycleId, weekNo). Đổi ngữ nghĩa
  // hàm này từ "tạo mới" sang "upsert nội dung tuần" (set focus/mission) —
  // tránh tạo row trùng cho cùng tuần. `uix_weekly_plans_cycle_week_alive`
  // (migration 027) là lớp chặn cứng ở DB nếu có code path nào khác lỡ cố
  // insert lần 2.
  const [existing] = await db
    .select()
    .from(weeklyPlans)
    .where(
      and(
        eq(weeklyPlans.cycleId, cycleId),
        eq(weeklyPlans.weekNo, req.weekNo),
        isNull(weeklyPlans.deletedAt)
      )
    );

  if (existing) {
    const [updated] = await db
      .update(weeklyPlans)
      .set({
        focus: req.focus !== undefined ? req.focus : existing.focus,
        mission: req.mission !== undefined ? req.mission : existing.mission,
        startDate: req.startDate ? new Date(req.startDate) : existing.startDate,
        endDate: req.endDate ? new Date(req.endDate) : existing.endDate,
        updatedAt: new Date(),
      })
      .where(eq(weeklyPlans.id, existing.id))
      .returning();

    if (!updated) throw APIError.internal("Failed to update weekly plan");
    return toWeeklyPlan(updated);
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

/**
 * Task 5 (2026-09-14 remediation) — đóng tuần hiện tại của 1 Operating Cycle
 * và tiến state machine, có optimistic-concurrency control (CAS) trên
 * `twelveWeekCycles.currentWeek` + `status`.
 *
 * Trong 1 transaction:
 *   1. Đọc cycle theo (workspace, project, cycle) — sai bất kỳ vế nào ⇒
 *      notFound, KHÔNG ghi gì.
 *   2. Kiểm tra `status === 'ACTIVE'` và `currentWeek === expectedCurrentWeek`
 *      — sai ⇒ aborted, KHÔNG ghi gì (chưa có UPDATE/INSERT nào chạy trước
 *      điểm này).
 *   3. UPDATE có điều kiện (CAS thật, giống transitionProjectLifecycle) trên
 *      `twelveWeekCycles` — nếu đây là tuần cuối (`currentWeek ===
 *      durationWeeks`) thì set `status = 'COMPLETED'` và GIỮ NGUYÊN
 *      `currentWeek` ở N (quyết định: không tăng currentWeek vượt quá N vì
 *      sẽ trỏ tới 1 weekNo không có weekly_plans nào); ngược lại tăng
 *      `currentWeek + 1`. `updated.length !== 1` ⇒ race đã xảy ra, abort —
 *      TOÀN BỘ transaction rollback, không có weekly_plans nào bị sửa, không
 *      event nào được tạo.
 *   4. Chỉ sau khi CAS ở bước 3 thành công mới UPDATE review fields của đúng
 *      weekly_plans của tuần đang đóng, rồi append đúng 2 event:
 *      `WEEK_CLOSED` (luôn luôn) + `WEEK_ADVANCED` hoặc `CYCLE_COMPLETED`.
 *   Hàm này KHÔNG bao giờ đụng tới `projects.lifecycleStage` — lifecycle
 *   Project (P0..P6) là 1 trục hoàn toàn khác, transition riêng qua
 *   `transitionProjectLifecycle`.
 */
export async function advanceCycleWeekAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    cycleId: string;
    expectedCurrentWeek: number;
    reflection: string;
    executionScore?: number | null;
    outcomeScore?: number | null;
  }
): Promise<AdvanceCycleWeekResultDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const cycleId = BigInt(req.cycleId);
  await verifyProjectInWorkspace(wsId, pId);

  if (!req.reflection || !req.reflection.trim()) {
    throw APIError.invalidArgument("reflection is required");
  }

  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  return db.transaction(async (tx) => {
    // Đọc trước để biết durationWeeks/weekNo hiện tại — đây chỉ là read,
    // không phải nguồn CAS thật (CAS thật nằm ở UPDATE...WHERE bên dưới).
    const [cycle] = await tx
      .select()
      .from(twelveWeekCycles)
      .where(
        and(
          eq(twelveWeekCycles.id, cycleId),
          eq(twelveWeekCycles.workspaceId, wsId),
          eq(twelveWeekCycles.projectId, pId),
          isNull(twelveWeekCycles.deletedAt)
        )
      );

    if (!cycle) {
      throw APIError.notFound("Operating cycle not found in project/workspace");
    }
    if (cycle.status !== "ACTIVE") {
      throw APIError.aborted("Operating cycle is not ACTIVE");
    }
    if (cycle.currentWeek !== req.expectedCurrentWeek) {
      throw APIError.aborted("Cycle currentWeek changed; reload before retrying");
    }

    const [currentWeekPlan] = await tx
      .select()
      .from(weeklyPlans)
      .where(
        and(
          eq(weeklyPlans.cycleId, cycleId),
          eq(weeklyPlans.weekNo, cycle.currentWeek),
          isNull(weeklyPlans.deletedAt)
        )
      );

    if (!currentWeekPlan) {
      throw APIError.internal("Current week plan missing for cycle");
    }

    const isLastWeek = cycle.currentWeek >= cycle.durationWeeks;
    const casWhere = and(
      eq(twelveWeekCycles.id, cycleId),
      eq(twelveWeekCycles.workspaceId, wsId),
      eq(twelveWeekCycles.projectId, pId),
      eq(twelveWeekCycles.status, "ACTIVE"),
      eq(twelveWeekCycles.currentWeek, req.expectedCurrentWeek)
    );

    // Bước CAS thật — chạy TRƯỚC mọi write khác. Nếu update.length !== 1,
    // ném lỗi ngay để transaction rollback trước khi weekly_plans hay
    // cycle_week_events bị đụng tới, đảm bảo 1 CAS thất bại không bao giờ để
    // lại event mồ côi.
    const updatedCycleRows = await tx
      .update(twelveWeekCycles)
      .set(
        isLastWeek
          ? { status: "COMPLETED", updatedAt: new Date() }
          : { currentWeek: cycle.currentWeek + 1, updatedAt: new Date() }
      )
      .where(casWhere)
      .returning();

    if (updatedCycleRows.length !== 1) {
      throw APIError.aborted("Operating cycle changed; reload before retrying");
    }
    const updatedCycleRow = updatedCycleRows[0];

    const [updatedWeek] = await tx
      .update(weeklyPlans)
      .set({
        reflection: req.reflection.trim(),
        executionScore: req.executionScore ?? currentWeekPlan.executionScore,
        outcomeScore: req.outcomeScore ?? currentWeekPlan.outcomeScore,
        updatedAt: new Date(),
      })
      .where(eq(weeklyPlans.id, currentWeekPlan.id))
      .returning();

    if (!updatedWeek) throw APIError.internal("Failed to update weekly plan");

    await tx.insert(cycleWeekEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      cycleId,
      weekNo: cycle.currentWeek,
      eventType: "WEEK_CLOSED",
      actorId,
      expectedCurrentWeek: req.expectedCurrentWeek,
      payload: {
        reflection: req.reflection.trim(),
        executionScore: req.executionScore ?? null,
        outcomeScore: req.outcomeScore ?? null,
      },
    });

    const [advanceEvent] = await tx
      .insert(cycleWeekEvents)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: pId,
        cycleId,
        weekNo: cycle.currentWeek,
        eventType: isLastWeek ? "CYCLE_COMPLETED" : "WEEK_ADVANCED",
        actorId,
        expectedCurrentWeek: req.expectedCurrentWeek,
        payload: null,
      })
      .returning();

    if (!advanceEvent) throw APIError.internal("Failed to append cycle week event");

    return {
      cycle: toCycle(updatedCycleRow),
      week: toWeeklyPlan(updatedWeek),
      event: toCycleWeekEvent(advanceEvent),
    };
  });
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
  let commitmentRow: typeof weeklyCommitments.$inferSelect | null = null;
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
    commitmentRow = com;
  }

  let initiativeId: bigint | null = null;
  let initiativeRow: typeof initiatives.$inferSelect | null = null;
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
    initiativeRow = init;
  }

  // Denormalize weeklyPlanId/keyResultId lên Task lúc tạo — đồng nhất với
  // pattern đã có ở task.service.ts::createTaskService cho cùng bảng `tasks`,
  // cùng thứ tự ưu tiên (2 endpoint cùng ghi bảng `tasks` không được lệch
  // nhau với cùng input logic):
  //   1. purposeRef của weeklyCommitment khi purposeType là "KR"
  //   2. keyResultId của initiative — ưu tiên initiative tường minh
  //      (req.initiativeId), fallback sang initiativeId riêng của
  //      weeklyCommitment khi request KHÔNG truyền initiativeId tường minh
  //      (vd. commitment tạo trước, gắn sẵn 1 initiative không phải "KR").
  let resolvedWeeklyPlanId: bigint | null = null;
  let resolvedKeyResultId: bigint | null = null;
  if (commitmentRow) {
    resolvedWeeklyPlanId = commitmentRow.weeklyPlanId;
    if (commitmentRow.purposeType === "KR" && commitmentRow.purposeRef) {
      resolvedKeyResultId = BigInt(commitmentRow.purposeRef);
    }
  }
  if (!resolvedKeyResultId) {
    if (initiativeRow) {
      resolvedKeyResultId = initiativeRow.keyResultId;
    } else if (commitmentRow?.initiativeId) {
      const [inferredInit] = await db
        .select({ keyResultId: initiatives.keyResultId })
        .from(initiatives)
        .where(eq(initiatives.id, commitmentRow.initiativeId))
        .limit(1);
      if (inferredInit) resolvedKeyResultId = inferredInit.keyResultId;
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
      weeklyPlanId: resolvedWeeklyPlanId,
      keyResultId: resolvedKeyResultId,
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
    projectId: string;
    taskId: string;
    status: string;
  }
): Promise<TaskDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const taskId = BigInt(req.taskId);

  // Khoá task theo đúng (workspace, project) — một task ID trùng nhưng thuộc
  // Project khác không được phép advance qua URL của Project này.
  const [task] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId), eq(tasks.projectId, pId), isNull(tasks.deletedAt)));

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
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId), eq(tasks.projectId, pId), isNull(tasks.deletedAt)))
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
          inArray(keyResults.objectiveId, objIds),
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
