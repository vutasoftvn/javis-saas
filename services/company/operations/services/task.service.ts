import { APIError } from "encore.dev/api";
import { eq, desc, and, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspaceRecord } from "../../identity/services/workspace.service";
import { getWorkforceMember } from "../../identity/handlers/workforce.handler";
import { requireWorkspaceAccess, requireFounderCommand } from "../../shared/auth/workspace-access";
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
  weeklyCommitments,
  initiatives,
} from "../../shared/db/schema/operations";
import { sql, inArray } from "drizzle-orm";
import { assertInitiativeInWorkspace } from "./initiative.service";
import { verifyProjectInWorkspace } from "./project-operating-loop.service";
import {
  CreateTaskOutcomeContractInput,
  TaskOutcomeContractView,
  insertContractRevision,
} from "./task-outcome-contract.service";

const { tasks } = schema;

// Queue gate (spec §6.1) — re-export để handler/test dùng một điểm.
export { assertTaskCanEnterQueue, validateTaskOutcomeContractForQueue, createTaskOutcomeProposal } from "./task-outcome-contract.service";


// "draft" — task do AI đề xuất, chưa được manager/founder xác nhận (spec §6.1).
// Không có DB CHECK constraint trên tasks.status; danh sách này là nguồn chuẩn
// ở tầng ứng dụng.
export type TaskStatus =
  | "draft"
  | "todo"
  | "in_progress"
  | "waiting_approval"
  | "blocked"
  | "done"
  | "cancelled";
export const TASK_STATUSES: readonly TaskStatus[] = [
  "draft",
  "todo",
  "in_progress",
  "waiting_approval",
  "blocked",
  "done",
  "cancelled",
];

export interface Task {
  id: string;
  workspaceId: string;
  projectId: string;
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
  weeklyPlanId?: string;
  keyResultId?: string;
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
  // 2026-09-14 remediation — bắt buộc, không còn suy diễn "project đầu tiên"
  // khi thiếu. Caller phải biết chính xác Task thuộc Project nào.
  projectId: string;
  title: string;
  priority?: "low" | "medium" | "high" | "urgent";
  dueAt?: string;
  initiativeId?: string;
  weeklyCommitmentId?: string;
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
    projectId: row.projectId.toString(),
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
    weeklyPlanId: row.weeklyPlanId ? row.weeklyPlanId.toString() : undefined,
    keyResultId: row.keyResultId ? row.keyResultId.toString() : undefined,
    sortKey: row.sortKey,
    assigneeMemberId: row.assigneeMemberId ? row.assigneeMemberId.toString() : null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    executionMode: row.executionMode as Task["executionMode"],
    function: row.function,
    projectIds: [row.projectId.toString()],
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createTaskService(
  params: CreateTaskParams,
  authorization: string | undefined
): Promise<Task> {
  // Fail closed ngay khi thiếu Project — không bao giờ suy diễn/chọn project
  // đầu tiên của workspace thay caller.
  if (!params.projectId) {
    throw APIError.invalidArgument(
      "PROJECT_CONTEXT_REQUIRED: projectId is required to create a task"
    );
  }

  const authCtx = await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspaceRecord(params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const resolvedProjectId = BigInt(params.projectId);
  await verifyProjectInWorkspace(wsId, resolvedProjectId);

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

  let resolvedInitiativeId = params.initiativeId;
  let commitmentRow: typeof weeklyCommitments.$inferSelect | undefined;
  if (params.weeklyCommitmentId) {
    const [commitment] = await db
      .select()
      .from(weeklyCommitments)
      .where(
        and(
          eq(weeklyCommitments.id, BigInt(params.weeklyCommitmentId)),
          eq(weeklyCommitments.workspaceId, BigInt(params.workspaceId)),
          isNull(weeklyCommitments.deletedAt)
        )
      )
      .limit(1);

    if (!commitment) {
      throw APIError.notFound(`Weekly commitment ${params.weeklyCommitmentId} not found in workspace`);
    }

    // Khoá task theo đúng Project — một weekly commitment thuộc Project khác
    // không được âm thầm kéo task sang project đó.
    if (commitment.projectId !== resolvedProjectId) {
      throw APIError.invalidArgument(
        `Weekly commitment ${params.weeklyCommitmentId} does not belong to project ${params.projectId}`
      );
    }

    commitmentRow = commitment;
    if (commitment.initiativeId) {
      resolvedInitiativeId = commitment.initiativeId.toString();
    }
  }

  // Denormalize weeklyPlanId/keyResultId lên Task lúc tạo để đọc không cần
  // join lại qua chuỗi commitment/initiative mỗi lần (spec workspace/project
  // foundation, Task 3). Ưu tiên purposeRef của weeklyCommitment nếu
  // purposeType là "KR"; fallback sang keyResultId của initiative khi task
  // gắn trực tiếp initiative (không qua weeklyCommitment).
  let resolvedWeeklyPlanId: bigint | null = null;
  let resolvedKeyResultId: bigint | null = null;
  if (commitmentRow) {
    resolvedWeeklyPlanId = commitmentRow.weeklyPlanId;
    if (commitmentRow.purposeType === "KR" && commitmentRow.purposeRef) {
      resolvedKeyResultId = BigInt(commitmentRow.purposeRef);
    }
  }
  if (!resolvedKeyResultId && resolvedInitiativeId) {
    const [init] = await db
      .select({ keyResultId: initiatives.keyResultId })
      .from(initiatives)
      .where(eq(initiatives.id, BigInt(resolvedInitiativeId)))
      .limit(1);
    if (init) resolvedKeyResultId = init.keyResultId;
  }

  // Task 2 (2026-09-14 remediation): projectId luôn tường minh từ caller
  // (resolvedProjectId ở trên) — không còn suy diễn từ commitment/initiative
  // hay chọn project đầu tiên. Mọi initiativeId cung cấp (trực tiếp hoặc qua
  // commitment) phải thuộc đúng resolvedProjectId, không thì reject.
  if (resolvedInitiativeId) {
    const initRow = await assertInitiativeInWorkspace(resolvedInitiativeId, params.workspaceId, false);
    if (initRow.projectId !== resolvedProjectId) {
      throw APIError.invalidArgument(
        `Initiative ${resolvedInitiativeId} does not belong to project ${params.projectId}`
      );
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
        projectId: resolvedProjectId,
        title: params.title,
        priority: params.priority || "medium",
        dueAt: params.dueAt ? new Date(params.dueAt) : null,
        initiativeId: resolvedInitiativeId ? BigInt(resolvedInitiativeId) : null,
        weeklyCommitmentId: params.weeklyCommitmentId ? BigInt(params.weeklyCommitmentId) : null,
        weeklyPlanId: resolvedWeeklyPlanId,
        keyResultId: resolvedKeyResultId,
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

export interface CreateAiTaskProposalParams {
  workspaceId: string;
  // 2026-09-14 remediation — bắt buộc, cùng lý do với CreateTaskParams.projectId.
  projectId: string;
  title: string;
  proposedByAgentInstanceId: string;
  contract: Omit<CreateTaskOutcomeContractInput, "workspaceId" | "taskId">;
  priority?: "low" | "medium" | "high" | "urgent";
  initiativeId?: string;
}

export interface AiTaskProposalView {
  task: Task;
  contract: TaskOutcomeContractView;
}

/**
 * Đường NỘI BỘ cho AI đề xuất một task + Outcome Contract. Tạo task ở status
 * 'draft' (source 'ai_agent_proposal') và contract revision 1 DRAFT trong CÙNG
 * transaction. KHÔNG tạo queue entry / work package (spec §6.1). Manager/founder
 * xác nhận qua Task 2 mới atomically chuyển sang CONFIRMED + QUEUED.
 */
export async function createAiTaskProposalService(
  params: CreateAiTaskProposalParams,
  ctx: TenantContext
): Promise<AiTaskProposalView> {
  if (params.workspaceId !== ctx.workspaceId) {
    throw APIError.permissionDenied("workspace mismatch");
  }
  if (!params.projectId) {
    throw APIError.invalidArgument(
      "PROJECT_CONTEXT_REQUIRED: projectId is required to create an AI task proposal"
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(params.projectId);
  await verifyProjectInWorkspace(wsId, pId);

  if (params.initiativeId) {
    const init = await assertInitiativeInWorkspace(params.initiativeId, ctx.workspaceId, false);
    if (init.projectId !== pId) {
      throw APIError.invalidArgument(
        `Initiative ${params.initiativeId} does not belong to project ${params.projectId}`
      );
    }
  }

  return db.transaction(async (tx) => {
    const [row] = await tx
      .insert(tasks)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(ctx.workspaceId),
        projectId: pId,
        title: params.title,
        status: "draft",
        priority: params.priority || "medium",
        source: "ai_agent_proposal",
        initiativeId: params.initiativeId ? BigInt(params.initiativeId) : null,
      })
      .returning();
    if (!row) throw APIError.internal("failed to create task proposal");
    const task = toTask(row);

    const contract = await insertContractRevision(
      tx,
      {
        ...params.contract,
        workspaceId: ctx.workspaceId,
        taskId: task.id,
        initiativeId: params.contract.initiativeId ?? params.initiativeId,
      },
      { status: "DRAFT", revision: 1, proposedByAgentInstanceId: params.proposedByAgentInstanceId }
    );

    return { task, contract };
  });
}

export async function getTaskService(id: string, ctx: TenantContext): Promise<Task> {
  const [row] = await db
    .select()
    .from(tasks)
    .where(
      and(
        eq(tasks.id, BigInt(id)),
        eq(tasks.workspaceId, BigInt(ctx.workspaceId)),
        isNull(tasks.deletedAt)
      )
    )
    .limit(1);

  if (!row) throw APIError.notFound(`task ${id} not found`);

  // Startup Core: task thuộc đúng một project qua cột trực tiếp
  // `tasks.project_id` — không còn M:N link table.
  return toTask(row);
}

/**
 * Soft-delete task: set deletedAt, không xoá cứng — giữ audit trail cho
 * Weekly Commitment / Executive Board evidence tham chiếu ngược.
 */
export async function deleteTaskService(
  id: string,
  ctx: TenantContext
): Promise<{ id: string; deletedAt: string }> {
  const wsId = BigInt(ctx.workspaceId);
  const taskId = BigInt(id);

  const [updated] = await db
    .update(tasks)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId), isNull(tasks.deletedAt)))
    .returning({ id: tasks.id, deletedAt: tasks.deletedAt });

  if (!updated) {
    throw APIError.notFound(`Task ${id} not found`);
  }

  return { id: updated.id.toString(), deletedAt: updated.deletedAt!.toISOString() };
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
      projectId: tasks.projectId,
    })
    .from(tasks)
    .where(
      and(
        eq(tasks.workspaceId, wsId),
        inArray(tasks.projectId, projectIds),
        isNull(tasks.deletedAt)
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
  requireFounderCommand(ctx, "agent.sweep.manage");
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
