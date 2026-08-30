import { eq, and, lte, gte, sql, count, inArray } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db, schema } from "../models/db";
import { scheduleTask } from "./control-plane-scheduler.service";

const {
  workspaceScheduleDefinitions,
  workspaceScheduleExecutions,
} = schema;

export type ScheduleKind = "one_time" | "daily" | "weekdays";
export type ScheduleState = "enabled" | "paused" | "archived";
export type ScheduleExecutionState =
  | "queued"
  | "enqueue_retry"
  | "enqueue_failed"
  | "running"
  | "succeeded"
  | "failed"
  | "blocked_reauth"
  | "cancelled";

export const MAX_ACTIVE_SCHEDULES_PER_WORKSPACE = parseInt(
  process.env.COSA_SCHEDULE_MAX_ACTIVE_PER_WORKSPACE || "10",
  10
);
export const MAX_EXECUTIONS_24H = parseInt(
  process.env.COSA_SCHEDULE_MAX_EXECUTIONS_24H || "50",
  10
);
export const DEFAULT_DISPATCH_BATCH_SIZE = parseInt(
  process.env.COSA_SCHEDULE_DISPATCH_BATCH_SIZE || "25",
  10
);
export const MAX_ENQUEUE_RETRIES = parseInt(
  process.env.COSA_SCHEDULE_MAX_ENQUEUE_RETRIES || "5",
  10
);
// Cap backoff giữa các lần retry enqueue — cùng giá trị với
// MAX_BACKOFF_SEC của control-plane-scheduler.service.ts (low-level task
// queue) để nhất quán hành vi retry trong toàn bộ control plane.
const MAX_ENQUEUE_BACKOFF_SEC = 300;

/**
 * Exponential backoff cho retry enqueue: lần thất bại đầu tiên retry ngay ở
 * tick kế tiếp (0s — hầu hết lỗi enqueue là transient, giữ dispatcher phản
 * hồi nhanh), từ lần thất bại thứ 2 trở đi mới giãn cách 5s, 10s, 20s, ...
 * cap 5 phút để tránh dồn tải khi lỗi kéo dài (vd. hạ tầng đang down).
 */
function computeEnqueueBackoffSeconds(attemptCount: number): number {
  if (attemptCount <= 1) return 0;
  return Math.min(5 * 2 ** (attemptCount - 2), MAX_ENQUEUE_BACKOFF_SEC);
}

/**
 * Không có pipeline metrics riêng trong services/cosa (chỉ console.error/warn
 * template string ở các chỗ khác) — dùng một dòng log có cấu trúc (JSON) làm
 * "metric" thay thế, đủ correlation field (execution id, attempt, next
 * attempt, queue age) để dashboard log-based (vd. Grafana Loki/CloudWatch
 * Insights) query được mà không cần thêm dependency mới.
 */
function logEnqueueRetryMetric(fields: {
  event: "enqueue_retry_scheduled" | "enqueue_failed_terminal";
  executionId: string;
  definitionId: string;
  attemptCount: number;
  maxAttempts: number;
  nextAttemptAt: Date | null;
  queueAgeMs: number;
  error: string;
}): void {
  console.warn(
    `[ScheduleDispatcher] metric=${JSON.stringify({
      ...fields,
      nextAttemptAt: fields.nextAttemptAt?.toISOString() ?? null,
    })}`
  );
}

export function validateIanaTimezone(tz: string): void {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: tz });
  } catch {
    throw APIError.invalidArgument(`invalid IANA timezone: '${tz}'`);
  }
}

/**
 * Calculates next run date in UTC given timezone, hour, minute, and optional weekdays (1-7, Mon-Sun).
 */
export function calculateNextRun(
  kind: ScheduleKind,
  tz: string,
  hour?: number | null,
  minute?: number | null,
  weekdays?: number[] | null,
  now: Date = new Date()
): Date | null {
  if (kind === "one_time") {
    return null;
  }

  validateIanaTimezone(tz);
  const h = hour ?? 0;
  const m = minute ?? 0;
  if (h < 0 || h > 23 || m < 0 || m > 59) {
    throw APIError.invalidArgument(`invalid hour (${h}) or minute (${m})`);
  }

  // Iterate up to 14 days ahead to find the next matching slot
  const candidate = new Date(now.getTime());
  // Start from today or tomorrow
  for (let offsetDays = 0; offsetDays <= 14; offsetDays++) {
    const testDate = new Date(now.getTime() + offsetDays * 86400000);
    
    // Format testDate in target timezone to get YYYY-MM-DD
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "narrow",
    });
    
    const parts = formatter.formatToParts(testDate);
    const partMap: Record<string, string> = {};
    for (const p of parts) {
      partMap[p.type] = p.value;
    }
    const year = parseInt(partMap.year, 10);
    const month = parseInt(partMap.month, 10) - 1;
    const day = parseInt(partMap.day, 10);

    // Build date in target timezone using Date.UTC approximation with timezone offset
    // A reliable way: format a test string and parse
    const tzTargetStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}T${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00`;
    
    // Convert wall time in target tz to UTC Date
    const targetUtc = getUtcDateFromTzWallClock(year, month, day, h, m, tz);

    if (targetUtc > now) {
      if (kind === "daily") {
        return targetUtc;
      }
      if (kind === "weekdays" && weekdays && weekdays.length > 0) {
        // Get day of week in target timezone (1=Mon, ..., 7=Sun)
        const dayOfWeekTz = getTzDayOfWeek(targetUtc, tz);
        if (weekdays.includes(dayOfWeekTz)) {
          return targetUtc;
        }
      }
    }
  }

  return null;
}

function getUtcDateFromTzWallClock(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  tz: string
): Date {
  const baseUtc = new Date(Date.UTC(year, month, day, hour, minute, 0));
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const parts = formatter.formatToParts(baseUtc);
  const partMap: Record<string, string> = {};
  for (const p of parts) partMap[p.type] = p.value;
  let hTz = parseInt(partMap.hour, 10);
  if (hTz === 24) hTz = 0;
  const mTz = parseInt(partMap.minute, 10);
  const yTz = parseInt(partMap.year, 10);
  const monTz = parseInt(partMap.month, 10) - 1;
  const dTz = parseInt(partMap.day, 10);

  const asUtc = Date.UTC(yTz, monTz, dTz, hTz, mTz, 0);
  const offsetMs = asUtc - baseUtc.getTime();
  return new Date(baseUtc.getTime() - offsetMs);
}


function getTzDayOfWeek(date: Date, tz: string): number {
  const dayStr = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short",
  }).format(date);
  const map: Record<string, number> = {
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
    Sun: 7,
  };
  return map[dayStr] || 1;
}

export async function createWorkspaceSchedule(input: {
  workspaceId: string;
  createdBy: string;
  scheduleKind: ScheduleKind;
  timezone?: string;
  runAt?: Date | null;
  hour?: number | null;
  minute?: number | null;
  weekdays?: number[];
  promptTemplate: string;
  agentProfile?: string;
  connectorGrantIds?: string[];
}) {
  const tz = input.timezone || "Asia/Ho_Chi_Minh";
  validateIanaTimezone(tz);

  if (!input.promptTemplate || !input.promptTemplate.trim()) {
    throw APIError.invalidArgument("promptTemplate cannot be empty");
  }

  // Check active schedule quota
  const [{ value: activeCount }] = await db
    .select({ value: count() })
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.workspaceId, input.workspaceId),
        eq(workspaceScheduleDefinitions.state, "enabled")
      )
    );

  if (Number(activeCount) >= MAX_ACTIVE_SCHEDULES_PER_WORKSPACE) {
    throw APIError.resourceExhausted(
      `active schedule quota exceeded: maximum of ${MAX_ACTIVE_SCHEDULES_PER_WORKSPACE} enabled schedules allowed per workspace`
    );
  }

  let nextRunAt: Date | null = null;
  if (input.scheduleKind === "one_time") {
    if (!input.runAt || input.runAt <= new Date()) {
      throw APIError.invalidArgument("one_time schedule requires runAt in the future");
    }
    nextRunAt = input.runAt;
  } else {
    nextRunAt = calculateNextRun(
      input.scheduleKind,
      tz,
      input.hour,
      input.minute,
      input.weekdays
    );
  }

  const id = `sched_def_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const [created] = await db
    .insert(workspaceScheduleDefinitions)
    .values({
      id,
      workspaceId: input.workspaceId,
      createdBy: input.createdBy,
      scheduleKind: input.scheduleKind,
      timezone: tz,
      runAt: input.runAt || null,
      hour: input.hour ?? null,
      minute: input.minute ?? null,
      weekdays: input.weekdays || [],
      promptTemplate: input.promptTemplate,
      agentProfile: input.agentProfile || "operations",
      connectorGrantIds: input.connectorGrantIds || [],
      state: "enabled",
      nextRunAt,
    })
    .returning();

  return created;
}

/**
 * Claim due 'enqueue_retry' rows atomically via `FOR UPDATE SKIP LOCKED` (cùng
 * pattern `pollDueTasks` trong control-plane-scheduler.service.ts) rồi bump
 * `nextAttemptAt` vào một mốc gần trong tương lai làm "giữ chỗ": SKIP LOCKED
 * chỉ bảo vệ hàng trong lúc transaction này còn mở — sau khi commit, một tick
 * dispatch khác chạy đồng thời (nhiều replica control-plane) có thể poll lại
 * đúng lúc `scheduleTask()` (I/O ngoài transaction) còn đang chạy. Bump
 * `nextAttemptAt` đóng cửa sổ race đó mà không cần giữ transaction mở qua cả
 * lệnh gọi mạng.
 */
async function claimDueEnqueueRetries(
  now: Date,
  limit: number
): Promise<(typeof workspaceScheduleExecutions.$inferSelect)[]> {
  return db.transaction(async (tx) => {
    const dueRows = await tx
      .select({ id: workspaceScheduleExecutions.id })
      .from(workspaceScheduleExecutions)
      .where(
        and(
          eq(workspaceScheduleExecutions.state, "enqueue_retry"),
          sql`${workspaceScheduleExecutions.taskId} IS NULL`,
          sql`(${workspaceScheduleExecutions.nextAttemptAt} IS NULL OR ${workspaceScheduleExecutions.nextAttemptAt} <= ${now})`
        )
      )
      .limit(limit)
      .for("update", { skipLocked: true });

    if (dueRows.length === 0) return [];

    const ids = dueRows.map((r) => r.id);
    const claimHoldUntil = new Date(now.getTime() + 60_000);
    await tx
      .update(workspaceScheduleExecutions)
      .set({ nextAttemptAt: claimHoldUntil })
      .where(inArray(workspaceScheduleExecutions.id, ids));

    return tx
      .select()
      .from(workspaceScheduleExecutions)
      .where(inArray(workspaceScheduleExecutions.id, ids));
  });
}

/**
 * Ghi nhận một lần enqueue thất bại: tăng attempt_count, và nếu đã chạm
 * MAX_ENQUEUE_RETRIES thì chốt terminal 'enqueue_failed' (không retry nữa —
 * occurrence này cần can thiệp thủ công), ngược lại lên lịch retry tiếp theo
 * với exponential backoff. Đây là điểm duy nhất chuyển state sang
 * enqueue_retry/enqueue_failed nên attempt-count luôn nhất quán dù lỗi xảy ra
 * ở lượt tạo occurrence đầu tiên hay ở một lượt retry sau đó.
 */
async function recordEnqueueFailure(params: {
  executionId: string;
  definitionId: string;
  priorAttemptCount: number;
  createdAt: Date;
  err: unknown;
  now: Date;
}): Promise<void> {
  const { executionId, definitionId, priorAttemptCount, createdAt, err, now } = params;
  const attemptCount = priorAttemptCount + 1;
  const message = err instanceof Error ? err.message : String(err);
  const queueAgeMs = now.getTime() - createdAt.getTime();

  if (attemptCount >= MAX_ENQUEUE_RETRIES) {
    await db
      .update(workspaceScheduleExecutions)
      .set({
        state: "enqueue_failed",
        attemptCount,
        nextAttemptAt: null,
        error: `enqueue failed permanently after ${attemptCount} attempt(s): ${message}`,
        updatedAt: now,
      })
      .where(eq(workspaceScheduleExecutions.id, executionId));

    logEnqueueRetryMetric({
      event: "enqueue_failed_terminal",
      executionId,
      definitionId,
      attemptCount,
      maxAttempts: MAX_ENQUEUE_RETRIES,
      nextAttemptAt: null,
      queueAgeMs,
      error: message,
    });
    return;
  }

  const nextAttemptAt = new Date(now.getTime() + computeEnqueueBackoffSeconds(attemptCount) * 1000);
  await db
    .update(workspaceScheduleExecutions)
    .set({
      state: "enqueue_retry",
      attemptCount,
      nextAttemptAt,
      error: message,
      updatedAt: now,
    })
    .where(eq(workspaceScheduleExecutions.id, executionId));

  logEnqueueRetryMetric({
    event: "enqueue_retry_scheduled",
    executionId,
    definitionId,
    attemptCount,
    maxAttempts: MAX_ENQUEUE_RETRIES,
    nextAttemptAt,
    queueAgeMs,
    error: message,
  });
}

/**
 * Advance `nextRunAt`/`lastRunAt` của schedule definition — CHỈ được gọi sau
 * khi `taskId` đã lưu durable (đây là điểm mấu chốt sửa lỗi Task 8: trước
 * đây một lần enqueue thất bại vẫn có thể khiến definition tưởng như đã chạy
 * xong occurrence hiện tại).
 */
async function advanceDefinitionAfterDispatch(
  def: typeof workspaceScheduleDefinitions.$inferSelect,
  now: Date
): Promise<void> {
  let nextNextRun: Date | null = null;
  let nextState: ScheduleState = def.state as ScheduleState;

  if (def.scheduleKind === "one_time") {
    nextNextRun = null;
    nextState = "paused";
  } else {
    nextNextRun = calculateNextRun(
      def.scheduleKind as ScheduleKind,
      def.timezone,
      def.hour,
      def.minute,
      def.weekdays as number[],
      now
    );
  }

  await db
    .update(workspaceScheduleDefinitions)
    .set({
      lastRunAt: now,
      nextRunAt: nextNextRun,
      state: nextState,
      updatedAt: new Date(),
    })
    .where(eq(workspaceScheduleDefinitions.id, def.id));
}

export async function dispatchDueWorkspaceSchedules(
  now: Date = new Date(),
  limit: number = DEFAULT_DISPATCH_BATCH_SIZE
): Promise<number> {
  let dispatchedCount = 0;

  // 1. Re-attempt due 'enqueue_retry' executions with null taskId. Rows are
  // claimed (FOR UPDATE SKIP LOCKED) before we touch scheduleTask() so two
  // concurrent dispatch ticks never both retry the same occurrence.
  const retryExecutions = await claimDueEnqueueRetries(now, limit);

  for (const execution of retryExecutions) {
    try {
      const task = await scheduleTask({
        targetSpecId: "cosa.schedule-execution",
        targetSpecKind: "agent",
        coalescingKey: `schedule-execution:${execution.id}`,
        inputPayload: {
          task_type: "scheduled_session",
          schedule_execution_id: execution.id,
        },
      });

      await db
        .update(workspaceScheduleExecutions)
        .set({ taskId: task.id, state: "queued", error: null, nextAttemptAt: null, updatedAt: new Date() })
        .where(eq(workspaceScheduleExecutions.id, execution.id));

      // Advance schedule definition nextRunAt if not advanced yet
      const [def] = await db
        .select()
        .from(workspaceScheduleDefinitions)
        .where(eq(workspaceScheduleDefinitions.id, execution.definitionId));

      if (def && (!def.lastRunAt || def.lastRunAt < execution.scheduledFor)) {
        await advanceDefinitionAfterDispatch(def, now);
      }

      dispatchedCount++;
    } catch (retryErr) {
      console.error(`[ScheduleDispatcher] Retry enqueue failed for execution ${execution.id}:`, retryErr);
      await recordEnqueueFailure({
        executionId: execution.id,
        definitionId: execution.definitionId,
        priorAttemptCount: execution.attemptCount,
        createdAt: execution.createdAt,
        err: retryErr,
        now,
      });
    }
  }

  // 2. Dispatch due definitions
  const dueDefinitions = await db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.state, "enabled"),
        lte(workspaceScheduleDefinitions.nextRunAt, now)
      )
    )
    .limit(limit);

  for (const def of dueDefinitions) {
    const scheduledFor = def.nextRunAt || now;

    // Check rolling 24h quota
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 3600000);
    const [{ value: executions24h }] = await db
      .select({ value: count() })
      .from(workspaceScheduleExecutions)
      .where(
        and(
          eq(workspaceScheduleExecutions.workspaceId, def.workspaceId),
          gte(workspaceScheduleExecutions.createdAt, twentyFourHoursAgo)
        )
      );

    if (Number(executions24h) >= MAX_EXECUTIONS_24H) {
      console.warn(
        `[ScheduleDispatcher] Quota reached for workspace ${def.workspaceId} (>= ${MAX_EXECUTIONS_24H} in 24h)`
      );
      continue;
    }

    const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    let execution: any = null;

    try {
      const [inserted] = await db
        .insert(workspaceScheduleExecutions)
        .values({
          id: execId,
          definitionId: def.id,
          workspaceId: def.workspaceId,
          scheduledFor,
          promptTemplateSnapshot: def.promptTemplate,
          agentProfileSnapshot: def.agentProfile,
          connectorGrantIdsSnapshot: def.connectorGrantIds || [],
          state: "queued",
        })
        .onConflictDoNothing({ target: [workspaceScheduleExecutions.definitionId, workspaceScheduleExecutions.scheduledFor] })
        .returning();

      if (!inserted) {
        // Idempotency: occurrence for this (definitionId, scheduledFor) slot
        // already exists — whether it's queued, terminal, or pending retry,
        // ownership of retrying it belongs exclusively to the claimed
        // enqueue_retry pass above (step 1), which takes the row via
        // `FOR UPDATE SKIP LOCKED`. Grabbing it again here (without a lock)
        // would race with a concurrent dispatch tick and double-enqueue it —
        // this is exactly the bug a prior version of this function had.
        continue;
      }
      execution = inserted;

      // Enqueue to low-level scheduled_tasks with fixed target
      const task = await scheduleTask({
        targetSpecId: "cosa.schedule-execution",
        targetSpecKind: "agent",
        coalescingKey: `schedule-execution:${execution.id}`,
        inputPayload: {
          task_type: "scheduled_session",
          schedule_execution_id: execution.id,
        },
      });

      await db
        .update(workspaceScheduleExecutions)
        .set({ taskId: task.id, state: "queued", error: null, nextAttemptAt: null, updatedAt: new Date() })
        .where(eq(workspaceScheduleExecutions.id, execution.id));

      // Advance next_run_at only after durable storage of taskId
      await advanceDefinitionAfterDispatch(def, now);

      dispatchedCount++;
    } catch (err) {
      console.error(`[ScheduleDispatcher] Error dispatching schedule ${def.id}:`, err);
      if (execution) {
        await recordEnqueueFailure({
          executionId: execution.id,
          definitionId: def.id,
          priorAttemptCount: execution.attemptCount ?? 0,
          createdAt: execution.createdAt ?? now,
          err,
          now,
        });
      }
    }
  }

  return dispatchedCount;
}

export async function runScheduleNow(input: {
  scheduleId: string;
  workspaceId: string;
  principalId: string;
}) {
  const [def] = await db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.id, input.scheduleId),
        eq(workspaceScheduleDefinitions.workspaceId, input.workspaceId)
      )
    );

  if (!def) {
    throw APIError.notFound("schedule definition not found in workspace");
  }

  const now = new Date();
  const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  const [execution] = await db
    .insert(workspaceScheduleExecutions)
    .values({
      id: execId,
      definitionId: def.id,
      workspaceId: def.workspaceId,
      scheduledFor: now,
      promptTemplateSnapshot: def.promptTemplate,
      agentProfileSnapshot: def.agentProfile,
      connectorGrantIdsSnapshot: def.connectorGrantIds || [],
      state: "queued",
    })
    .returning();

  const task = await scheduleTask({
    targetSpecId: "cosa.schedule-execution",
    targetSpecKind: "agent",
    coalescingKey: `schedule-execution:${execution.id}`,
    inputPayload: {
      task_type: "scheduled_session",
      schedule_execution_id: execution.id,
    },
  });

  await db
    .update(workspaceScheduleExecutions)
    .set({ taskId: task.id, updatedAt: new Date() })
    .where(eq(workspaceScheduleExecutions.id, execution.id));

  return execution;
}

export async function completeScheduleExecution(input: {
  executionId: string;
  state: ScheduleExecutionState;
  conversationId?: string;
  runId?: string;
  error?: string;
}) {
  const [updated] = await db
    .update(workspaceScheduleExecutions)
    .set({
      state: input.state,
      conversationId: input.conversationId || null,
      runId: input.runId || null,
      error: input.error || null,
      updatedAt: new Date(),
    })
    .where(eq(workspaceScheduleExecutions.id, input.executionId))
    .returning();

  return updated || null;
}
