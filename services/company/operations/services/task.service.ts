import { APIError } from "encore.dev/api";
import { eq, desc, and, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { getWorkforceMember } from "../../identity/handlers/workforce.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { buildTaskCompletedEvent, buildTaskCreatedEvent, EventContext } from "./task-events.service";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import {
  taskExecutionRecords,
  executionPlans,
  executionPlanItems,
  workspaceExecutionSettings,
} from "../../shared/db/schema/operations";
import { sql, inArray } from "drizzle-orm";

const { tasks } = schema;

export type TaskStatus = "todo" | "in_progress" | "waiting_approval" | "blocked" | "done" | "cancelled";
export const TASK_STATUSES: readonly TaskStatus[] = ["todo", "in_progress", "waiting_approval", "blocked", "done", "cancelled"];

export interface Task {
  id: string;
  workspaceId: string;
  title: string;
  idempotencyKey: string | null;
  status: TaskStatus;
  priority: "low" | "medium" | "high" | "urgent";
  plannedStartAt: string | null;
  dueAt: string | null;
  timezone: string;
  source: string | null;
  completionPolicy: string | null;
  initiativeId: string | null;
  weeklyCommitmentId: string | null;
  sortKey: number | null;
  assigneeMemberId: string | null;
  ownerMemberId: string | null;
  executionMode: "HUMAN" | "AGENT" | "HYBRID" | null;
  function: string | null;
  projectIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskParams {
  workspaceId: string;
  title: string;
  priority?: "low" | "medium" | "high" | "urgent";
  dueAt?: string;
  initiativeId?: string;
  assigneeMemberId?: string;
  ownerMemberId?: string;
  executionMode?: "HUMAN" | "AGENT" | "HYBRID";
  function?: string;
  idempotencyKey?: string;
  correlationId?: string;
  actor?: { kind: "user" | "agent" | "system"; id: string };
}

function toTask(row: typeof tasks.$inferSelect, projectIds: string[] = []): Task {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    idempotencyKey: row.idempotencyKey,
    status: row.status as TaskStatus,
    priority: row.priority as Task["priority"],
    plannedStartAt: row.plannedStartAt ? row.plannedStartAt.toISOString() : null,
    dueAt: row.dueAt ? row.dueAt.toISOString() : null,
    timezone: row.timezone,
    source: row.source,
    completionPolicy: row.completionPolicy,
    initiativeId: row.initiativeId ? row.initiativeId.toString() : null,
    weeklyCommitmentId: row.weeklyCommitmentId ? row.weeklyCommitmentId.toString() : null,
    sortKey: row.sortKey,
    assigneeMemberId: row.assigneeMemberId ? row.assigneeMemberId.toString() : null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    executionMode: row.executionMode as Task["executionMode"],
    function: row.function,
    projectIds,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createTaskService(
  params: CreateTaskParams,
  authorization: string | undefined
): Promise<Task> {
  const authCtx = await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });
  if (params.assigneeMemberId !== undefined) {
    await getWorkforceMember({
      id: params.assigneeMemberId,
      workspaceId: params.workspaceId,
      authorization,
    });
  }
  if (params.ownerMemberId !== undefined) {
    await getWorkforceMember({
      id: params.ownerMemberId,
      workspaceId: params.workspaceId,
      authorization,
    });
  }

  if (params.idempotencyKey) {
    const [existing] = await db
      .select()
      .from(tasks)
      .where(
        and(
          eq(tasks.workspaceId, BigInt(params.workspaceId)),
          eq(tasks.idempotencyKey, params.idempotencyKey)
        )
      )
      .limit(1);

    if (existing) {
      return toTask(existing);
    }
  }

  const actor = params.actor || (authCtx.userId ? { kind: "user" as const, id: authCtx.userId } : { kind: "system" as const, id: "operations" });
  const eventCtx: EventContext = {
    correlationId: params.correlationId,
    actor,
  };

  const task = await db.transaction(async (tx) => {
    const [row] = await tx
      .insert(tasks)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(params.workspaceId),
        title: params.title,
        priority: params.priority || "medium",
        dueAt: params.dueAt ? new Date(params.dueAt) : null,
        initiativeId: params.initiativeId ? BigInt(params.initiativeId) : null,
        assigneeMemberId: params.assigneeMemberId ? BigInt(params.assigneeMemberId) : null,
        ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,
        executionMode: params.executionMode || null,
        function: params.function || null,
        idempotencyKey: params.idempotencyKey || null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create task");

    const t = toTask(row);
    await appendOutboxEvent(tx, buildTaskCreatedEvent(t, eventCtx));
    return t;
  });

  return task;
}

export async function getTaskService(id: string, ctx: TenantContext): Promise<Task> {
  const [row] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`task ${id} not found`);

  // Populate projectIds from link table
  const { listTaskProjects } = await import("./project-link.service");
  const projectIds = await listTaskProjects(ctx, id);

  return toTask(row, projectIds);
}

export async function listTasksService(
  workspaceId: string,
  authorization: string | undefined
): Promise<Task[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.workspaceId, BigInt(workspaceId)), isNull(tasks.deletedAt)))
    .orderBy(desc(tasks.createdAt));

  return rows.map((row) => toTask(row));
}

export async function updateTaskStatusService(
  id: string,
  status: TaskStatus,
  ctx: TenantContext,
  eventCtx?: EventContext
): Promise<Task> {
  if (!TASK_STATUSES.includes(status)) {
    throw APIError.invalidArgument(`status must be one of ${TASK_STATUSES.join(", ")}`);
  }

  const actor = eventCtx?.actor || (ctx.userId ? { kind: "user" as const, id: ctx.userId } : { kind: "system" as const, id: "operations" });
  const finalEventCtx: EventContext = {
    correlationId: eventCtx?.correlationId,
    actor,
  };

  const task = await db.transaction(async (tx) => {
    const [row] = await tx
      .update(tasks)
      .set({
        status,
        updatedAt: new Date(),
      })
      .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
      .returning();

    if (!row) throw APIError.notFound(`task ${id} not found`);
    const t = toTask(row);

    if (status === "done") {
      await appendOutboxEvent(tx, buildTaskCompletedEvent(t, finalEventCtx));
    }
    return t;
  });

  return task;
}

export async function updateTaskScheduleService(
  id: string,
  plannedStartAt: string | null,
  ctx: TenantContext
): Promise<Task> {
  let parsedPlannedStartAt: Date | null = null;
  if (plannedStartAt !== null && plannedStartAt !== undefined) {
    parsedPlannedStartAt = new Date(plannedStartAt);
    if (Number.isNaN(parsedPlannedStartAt.getTime())) {
      throw APIError.invalidArgument("plannedStartAt phải là ISO date hợp lệ");
    }
  }

  const [row] = await db
    .update(tasks)
    .set({ plannedStartAt: parsedPlannedStartAt, updatedAt: new Date() })
    .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
    .returning();

  if (!row) throw APIError.notFound(`task ${id} not found`);
  return toTask(row);
}

export type AgentAdvanceStatus = "in_progress" | "waiting_approval" | "done" | "blocked";
const AGENT_ADVANCE_STATUSES: readonly AgentAdvanceStatus[] = [
  "in_progress",
  "waiting_approval",
  "done",
  "blocked",
];

export interface AdvanceTaskByAgentParams {
  taskId: string;
  toStatus: AgentAdvanceStatus;
  runId: string;
  note?: string;
}

/**
 * Đường DUY NHẤT cho agent đổi trạng thái task — chỉ áp dụng cho task do một
 * AI_AGENT member đảm nhận. Cho phép 'in_progress' | 'waiting_approval' | 'done'
 * | 'blocked' (không 'cancelled'/'todo' — huỷ là việc người). 'waiting_approval'
 * dùng khi run nền gặp checkpoint cần founder duyệt (WGA). 'done' chỉ hợp lệ khi
 * task đang 'in_progress' hoặc 'waiting_approval'. Mọi lần gọi ghi 1
 * task_execution_records.
 */
export async function advanceTaskByAgentService(
  params: AdvanceTaskByAgentParams,
  ctx: TenantContext
): Promise<Task> {
  if (!AGENT_ADVANCE_STATUSES.includes(params.toStatus)) {
    throw APIError.invalidArgument(
      `toStatus phải là một trong ${AGENT_ADVANCE_STATUSES.join(", ")}`
    );
  }
  if (!params.runId || !params.runId.trim()) {
    throw APIError.invalidArgument("runId là bắt buộc");
  }

  const wsId = BigInt(ctx.workspaceId);
  const taskIdBig = BigInt(params.taskId);

  return await db.transaction(async (tx) => {
    const [row] = await tx
      .select()
      .from(tasks)
      .where(and(eq(tasks.id, taskIdBig), eq(tasks.workspaceId, wsId)))
      .limit(1);
    if (!row) throw APIError.notFound(`task ${params.taskId} not found`);

    if (!row.assigneeMemberId) {
      throw APIError.permissionDenied("task không được gán cho AI member");
    }
    const [member] = await tx
      .select({ memberType: identityWorkforceMembers.memberType })
      .from(identityWorkforceMembers)
      .where(
        and(
          eq(identityWorkforceMembers.id, row.assigneeMemberId),
          eq(identityWorkforceMembers.workspaceId, wsId)
        )
      )
      .limit(1);
    if (!member || member.memberType !== "AI_AGENT") {
      throw APIError.permissionDenied("task không được gán cho AI member");
    }

    if (params.toStatus === "done" && row.status !== "in_progress" && row.status !== "waiting_approval") {
      throw APIError.invalidArgument(
        `không thể hoàn thành task từ trạng thái ${row.status}`
      );
    }

    const [updated] = await tx
      .update(tasks)
      .set({ status: params.toStatus, updatedAt: new Date() })
      .where(and(eq(tasks.id, taskIdBig), eq(tasks.workspaceId, wsId)))
      .returning();

    await tx.insert(taskExecutionRecords).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      taskId: taskIdBig,
      runId: params.runId,
      capabilityId: "operations.task.advance",
      triggeredByKind: "agent",
      status: params.toStatus === "blocked" ? "FAILED" : "SUCCESS",
      errorDetails: params.note ? { note: params.note } : null,
    });

    const t = toTask(updated!);
    if (params.toStatus === "done") {
      await appendOutboxEvent(
        tx,
        buildTaskCompletedEvent(t, { actor: { kind: "agent", id: params.runId } })
      );
    }
    return t;
  });
}

export interface AgentClaimableTask {
  taskId: string;
  workspaceId: string;
  title: string;
  priority: string;
  autonomyClass: "AUTO" | "NEEDS_APPROVAL";
  ownerAgentProfile: string | null;
  expectedCapability: string | null;
  decisionReason: string;
  evidenceRefs: string[];
  planItemId: string;
  planId: string;
}

/**
 * Tập task để worker task-executor nhận (kind=goal_decomposition không đụng vào
 * đây). JOIN ngược execution_plan_items để lấy autonomy_class chính xác. Loại
 * task còn dependency chưa 'done'. KHÔNG lọc kill-switch / hạn mức runs/ngày —
 * executor tự lọc 2 điều kiện đó (cần RPC sang services/cosa).
 */
export async function listAgentClaimableTasksService(
  workspaceId: string,
  limit: number,
  authorization: string | undefined,
  ctxOverride?: TenantContext
): Promise<AgentClaimableTask[]> {
  if (!ctxOverride) {
    await requireWorkspaceAccess(authorization, workspaceId);
  }
  const wsId = BigInt(ctxOverride?.workspaceId ?? workspaceId);
  const cap = Math.max(1, Math.min(limit || 5, 50));

  // WGA #2 — kill-switch per-workspace: founder tắt -> không trả task nào (task
  // vẫn ở trạng thái todo, chỉ không tự chạy).
  const [settings] = await db
    .select({ sweepEnabled: workspaceExecutionSettings.sweepEnabled })
    .from(workspaceExecutionSettings)
    .where(eq(workspaceExecutionSettings.workspaceId, wsId))
    .limit(1);
  if (settings && settings.sweepEnabled === false) return [];

  // WGA #4 — rate-limit: đếm số task-execution run (distinct run_id do agent
  // ghi vào task_execution_records) trong 24h; vượt hạn -> không trả task mới.
  const maxRunsPerDay = Number(process.env.WGA_MAX_TASK_RUNS_PER_WORKSPACE_PER_DAY || "50");
  const [runCount] = await db
    .select({ n: sql<number>`count(distinct ${taskExecutionRecords.runId})::int` })
    .from(taskExecutionRecords)
    .where(
      and(
        eq(taskExecutionRecords.workspaceId, wsId),
        eq(taskExecutionRecords.triggeredByKind, "agent"),
        sql`${taskExecutionRecords.createdAt} >= now() - interval '24 hours'`
      )
    );
  if (runCount && runCount.n >= maxRunsPerDay) return [];

  const rows = await db
    .select({
      taskId: tasks.id,
      workspaceId: tasks.workspaceId,
      title: tasks.title,
      priority: tasks.priority,
      autonomyClass: executionPlanItems.autonomyClass,
      ownerAgentProfile: executionPlanItems.ownerAgentProfile,
      expectedCapability: executionPlanItems.expectedCapability,
      decisionReason: executionPlanItems.decisionReason,
      evidenceRefs: executionPlanItems.evidenceRefs,
      planItemId: executionPlanItems.id,
      planId: executionPlanItems.planId,
      sortKey: executionPlanItems.sortKey,
    })
    .from(tasks)
    .innerJoin(executionPlanItems, eq(executionPlanItems.materializedTaskId, tasks.id))
    .innerJoin(executionPlans, eq(executionPlans.id, executionPlanItems.planId))
    .where(
      and(
        eq(tasks.workspaceId, wsId),
        isNull(tasks.deletedAt),
        eq(tasks.status, "todo"),
        eq(tasks.source, "ai_agent_proposal"),
        eq(executionPlanItems.status, "accepted"),
        eq(executionPlans.status, "accepted"),
        inArray(executionPlanItems.autonomyClass, ["AUTO", "NEEDS_APPROVAL"]),
        sql`${tasks.assigneeMemberId} IN (
          SELECT id FROM core.workforce_members
          WHERE member_type = 'AI_AGENT' AND workspace_id = ${wsId}
        )`,
        sql`NOT EXISTS (
          SELECT 1 FROM operating.task_dependencies d
          JOIN operating.tasks dep ON dep.id = d.depends_on_task_id
          WHERE d.task_id = ${tasks.id} AND dep.status <> 'done' AND dep.deleted_at IS NULL
        )`
      )
    )
    .orderBy(tasks.priority, executionPlanItems.sortKey)
    .limit(cap);

  return rows.map((r) => ({
    taskId: r.taskId.toString(),
    workspaceId: r.workspaceId.toString(),
    title: r.title,
    priority: r.priority,
    autonomyClass: r.autonomyClass as "AUTO" | "NEEDS_APPROVAL",
    ownerAgentProfile: r.ownerAgentProfile,
    expectedCapability: r.expectedCapability,
    decisionReason: r.decisionReason,
    evidenceRefs: Array.isArray(r.evidenceRefs) ? (r.evidenceRefs as string[]) : [],
    planItemId: r.planItemId.toString(),
    planId: r.planId.toString(),
  }));
}

export interface StageRosterEntry {
  taskId: string;
  title: string;
  priority: string;
  status: string;
  projectId: string;
}

export interface StageRosterView {
  stage: { stageCode: string; taskCount: number };
  roster: StageRosterEntry[];
  summary: { total: number; highPriority: number; medium: number; locked: number };
}

/**
 * Roster của 1 stage tăng trưởng (vd "P0_DISCOVERY"): toàn bộ task thuộc các project
 * đang chọn stage đó trong workspace (project_operating_setups.selected_stage).
 * Dùng cho workforce dashboard bên apps/cosa
 * (GET /agent/workforce/stage-roster/{stage_code}).
 *
 * Lưu ý: `stageCode` chỉ khớp khi trùng đúng 1 trong 2 giá trị CHECK
 * constraint hiện có trên `selected_stage` ('P0_DISCOVERY' |
 * 'P1_PROBLEM_VALIDATION') — xem
 * migrations/34_project_operating_setups.up.sql. Giá trị khác không lỗi,
 * chỉ khiến `projects` rỗng và roster trả về rỗng.
 */
export async function listStageRosterService(
  workspaceId: string,
  stageCode: string
): Promise<StageRosterView> {
  const wsId = BigInt(workspaceId);

  const projects = await db
    .select({
      projectId: schema.projectOperatingSetups.projectId,
      status: schema.projectOperatingSetups.status,
    })
    .from(schema.projectOperatingSetups)
    .where(
      and(
        eq(schema.projectOperatingSetups.workspaceId, wsId),
        eq(schema.projectOperatingSetups.selectedStage, stageCode)
      )
    );

  if (projects.length === 0) {
    return {
      stage: { stageCode, taskCount: 0 },
      roster: [],
      summary: { total: 0, highPriority: 0, medium: 0, locked: 0 },
    };
  }

  // "locked" = task thuộc project chưa IN_PROGRESS — định nghĩa MVP tạm, xem
  // spec Phase 3 (workforce dashboard).
  const lockedProjectIds = new Set(
    projects.filter((p) => p.status !== "IN_PROGRESS").map((p) => p.projectId.toString())
  );
  const projectIds = projects.map((p) => p.projectId);

  const rows = await db
    .select({
      taskId: tasks.id,
      title: tasks.title,
      priority: tasks.priority,
      status: tasks.status,
      projectId: schema.taskProjects.projectId,
    })
    .from(schema.taskProjects)
    .innerJoin(tasks, eq(tasks.id, schema.taskProjects.taskId))
    .where(
      and(
        eq(schema.taskProjects.workspaceId, wsId),
        inArray(schema.taskProjects.projectId, projectIds)
      )
    );

  const roster: StageRosterEntry[] = rows.map((r) => ({
    taskId: r.taskId.toString(),
    title: r.title,
    priority: r.priority,
    status: r.status,
    projectId: r.projectId.toString(),
  }));

  return {
    stage: { stageCode, taskCount: roster.length },
    roster,
    summary: {
      total: roster.length,
      highPriority: roster.filter((r) => r.priority === "high").length,
      medium: roster.filter((r) => r.priority === "medium").length,
      locked: roster.filter((r) => lockedProjectIds.has(r.projectId)).length,
    },
  };
}

export interface FounderInboxTask {
  taskId: string;
  title: string;
  status: TaskStatus;
  priority: string;
  reason: "founder_only" | "blocked";
  updatedAt: string;
}

/**
 * WGA #6a — "Việc của bạn": task founder cần tự làm (FOUNDER_ONLY, execution_mode
 * 'HUMAN') + task AI bị chặn (status 'blocked'), đều từ nguồn ai_agent_proposal.
 */
export async function listFounderInboxTasksService(
  workspaceId: string,
  authorization: string | undefined
): Promise<FounderInboxTask[]> {
  await requireWorkspaceAccess(authorization, workspaceId);
  const rows = await db
    .select()
    .from(tasks)
    .where(
      and(
        eq(tasks.workspaceId, BigInt(workspaceId)),
        isNull(tasks.deletedAt),
        eq(tasks.source, "ai_agent_proposal"),
        sql`(${tasks.executionMode} = 'HUMAN' OR ${tasks.status} = 'blocked')`,
        sql`${tasks.status} NOT IN ('done', 'cancelled')`
      )
    )
    .orderBy(desc(tasks.updatedAt))
    .limit(50);
  return rows.map((r) => ({
    taskId: r.id.toString(),
    title: r.title,
    status: r.status as TaskStatus,
    priority: r.priority,
    reason: r.status === "blocked" ? ("blocked" as const) : ("founder_only" as const),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

export interface WorkspaceExecutionSettingsView {
  workspaceId: string;
  sweepEnabled: boolean;
}

export async function getWorkspaceExecutionSettingsService(
  workspaceId: string,
  authorization: string | undefined
): Promise<WorkspaceExecutionSettingsView> {
  await requireWorkspaceAccess(authorization, workspaceId);
  const [row] = await db
    .select()
    .from(workspaceExecutionSettings)
    .where(eq(workspaceExecutionSettings.workspaceId, BigInt(workspaceId)))
    .limit(1);
  return { workspaceId, sweepEnabled: row ? row.sweepEnabled : true };
}

export async function setWorkspaceExecutionSettingsService(
  workspaceId: string,
  sweepEnabled: boolean,
  ctx: TenantContext
): Promise<WorkspaceExecutionSettingsView> {
  const wsId = BigInt(workspaceId);
  await db
    .insert(workspaceExecutionSettings)
    .values({
      workspaceId: wsId,
      sweepEnabled,
      updatedBy: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      updatedAt: new Date(),
    })
    .onConflictDoUpdate({
      target: workspaceExecutionSettings.workspaceId,
      set: {
        sweepEnabled,
        updatedBy: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        updatedAt: new Date(),
      },
    });
  return { workspaceId, sweepEnabled };
}
