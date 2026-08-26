import { randomUUID } from "node:crypto";
import { and, eq, inArray, isNotNull, lte } from "drizzle-orm";
import { db, schema } from "../models/db";

const { scheduledTasks } = schema;

/**
 * Port của packages/agent_core/coordination/scheduler.py::RunScheduler sang
 * durable Postgres (ADR-CONTROLPLANE-001 §2). Bản gốc Python hoàn toàn
 * in-memory (dict + asyncio.Lock trong 1 process).
 *
 * Phase 3 (docs/implementation/production-runtime-closure.md §7) — claim
 * atomic bằng fencing token (`claim_token`), visibility timeout (reclaim khi
 * worker chết giữa chừng), retry với exponential backoff, dead-letter khi
 * vượt `max_attempts`. State machine:
 *   scheduled → processing → { completed | failed(dead-letter) |
 *     scheduled(next_retry_at, reclaimed hoặc failed thường) }
 */

const DEFAULT_VISIBILITY_TIMEOUT_SEC = 120;
const DEFAULT_MAX_ATTEMPTS = 5;
const MAX_BACKOFF_SEC = 300;

export interface ScheduleParams {
  targetSpecId: string;
  inputPayload: Record<string, unknown>;
  coalescingKey?: string;
  runAt?: Date;
  targetSpecKind?: string;
  maxAttempts?: number;
}

export interface ScheduledTaskRow {
  id: string;
  coalescingKey: string | null;
  targetSpecId: string;
  targetSpecKind: string;
  inputPayload: unknown;
  runAt: Date;
  status: string;
  createdAt: Date;
  attemptCount: number;
  maxAttempts: number;
  claimedBy: string | null;
  claimToken: string | null;
  claimedAt: Date | null;
  heartbeatAt: Date | null;
  visibilityTimeoutAt: Date | null;
  lastError: string | null;
  nextRetryAt: Date | null;
  completedAt: Date | null;
  deadLetterReason: string | null;
}

/** Exponential backoff cho retry: 5s, 10s, 20s, 40s, ... cap 5 phút. */
function computeBackoffSeconds(attemptCount: number): number {
  return Math.min(5 * 2 ** Math.max(attemptCount - 1, 0), MAX_BACKOFF_SEC);
}

export async function scheduleTask(params: ScheduleParams): Promise<ScheduledTaskRow> {
  const now = new Date();
  const runAt = params.runAt ?? new Date(now.getTime() - 1000);

  return db.transaction(async (tx) => {
    if (params.coalescingKey) {
      // Khoá đúng row đang "scheduled" với cùng coalescing_key (nếu có) để
      // tránh race giữa 2 request cùng coalesce vào 1 task.
      const existingRows = await tx
        .select()
        .from(scheduledTasks)
        .where(and(eq(scheduledTasks.coalescingKey, params.coalescingKey), eq(scheduledTasks.status, "scheduled")))
        .for("update");
      const existing = existingRows[0];

      if (existing) {
        const mergedPayload = {
          ...(existing.inputPayload as Record<string, unknown>),
          ...params.inputPayload,
        };
        await tx
          .update(scheduledTasks)
          .set({ inputPayload: mergedPayload })
          .where(eq(scheduledTasks.id, existing.id));
        return { ...existing, inputPayload: mergedPayload } as ScheduledTaskRow;
      }
    }

    const id = `task_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
    const row = {
      id,
      coalescingKey: params.coalescingKey ?? null,
      targetSpecId: params.targetSpecId,
      targetSpecKind: params.targetSpecKind ?? "agent",
      inputPayload: params.inputPayload,
      runAt,
      status: "scheduled",
      createdAt: now,
      attemptCount: 0,
      maxAttempts: params.maxAttempts ?? DEFAULT_MAX_ATTEMPTS,
      claimedBy: null,
      claimToken: null,
      claimedAt: null,
      heartbeatAt: null,
      visibilityTimeoutAt: null,
      lastError: null,
      nextRetryAt: null,
      completedAt: null,
      deadLetterReason: null,
    };
    await tx.insert(scheduledTasks).values(row);
    return row as ScheduledTaskRow;
  });
}

export interface ClaimParams {
  workerId: string;
  limit?: number;
  visibilityTimeoutSec?: number;
}

/**
 * Atomic claim: `FOR UPDATE SKIP LOCKED` để nhiều worker poll đồng thời không
 * lấy trùng task, cộng với claim_token (fencing) để phân biệt "worker đang
 * giữ task hợp lệ" khỏi "worker cũ đã bị sweeper reclaim nhưng vẫn cố
 * complete" (crash test #6 trong plan).
 */
export async function pollDueTasks(params: ClaimParams): Promise<ScheduledTaskRow[]> {
  const { workerId, limit = 10, visibilityTimeoutSec = DEFAULT_VISIBILITY_TIMEOUT_SEC } = params;
  const now = new Date();
  const visibilityTimeoutAt = new Date(now.getTime() + visibilityTimeoutSec * 1000);

  return db.transaction(async (tx) => {
    const dueRows = await tx
      .select({ id: scheduledTasks.id })
      .from(scheduledTasks)
      .where(and(eq(scheduledTasks.status, "scheduled"), lte(scheduledTasks.runAt, now)))
      .orderBy(scheduledTasks.runAt)
      .limit(limit)
      .for("update", { skipLocked: true });

    if (dueRows.length === 0) return [];

    const ids = dueRows.map((r) => r.id);
    for (const id of ids) {
      const claimToken = `claim_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
      await tx
        .update(scheduledTasks)
        .set({
          status: "processing",
          claimedBy: workerId,
          claimToken,
          claimedAt: now,
          heartbeatAt: now,
          visibilityTimeoutAt,
        })
        .where(eq(scheduledTasks.id, id));
    }

    const claimed = await tx
      .select()
      .from(scheduledTasks)
      .where(inArray(scheduledTasks.id, ids));
    return claimed as ScheduledTaskRow[];
  });
}

export interface HeartbeatTaskParams {
  taskId: string;
  workerId: string;
  claimToken: string;
  extendSec?: number;
}

/** Gia hạn visibility timeout trong lúc worker vẫn đang xử lý task — nếu
 * heartbeat ngừng (worker chết/treo), sweeper sẽ reclaim sau khi hết hạn. */
export async function heartbeatTask(params: HeartbeatTaskParams): Promise<boolean> {
  const extendSec = params.extendSec ?? DEFAULT_VISIBILITY_TIMEOUT_SEC;
  const now = new Date();
  const visibilityTimeoutAt = new Date(now.getTime() + extendSec * 1000);

  return db.transaction(async (tx) => {
    const rows = await tx.select().from(scheduledTasks).where(eq(scheduledTasks.id, params.taskId)).for("update");
    const row = rows[0];
    if (!row || row.status !== "processing" || row.claimedBy !== params.workerId || row.claimToken !== params.claimToken) {
      return false;
    }
    await tx
      .update(scheduledTasks)
      .set({ heartbeatAt: now, visibilityTimeoutAt })
      .where(eq(scheduledTasks.id, params.taskId));
    return true;
  });
}

export interface CompleteTaskParams {
  taskId: string;
  workerId: string;
  claimToken: string;
  success: boolean;
  error?: string;
}

export interface CompleteTaskResult {
  ok: boolean;
  finalStatus: string;
}

/**
 * Hoàn tất task — fencing bằng (status='processing' AND claimed_by=workerId
 * AND claim_token=claimToken): worker cũ đã bị sweeper reclaim (claim_token
 * đã đổi/xoá) gọi complete_task() sẽ nhận `ok: false`, KHÔNG được phép ghi đè
 * kết quả của lần claim mới (crash test #6).
 */
export async function completeTask(params: CompleteTaskParams): Promise<CompleteTaskResult> {
  const { taskId, workerId, claimToken, success, error } = params;
  const now = new Date();

  return db.transaction(async (tx) => {
    const rows = await tx.select().from(scheduledTasks).where(eq(scheduledTasks.id, taskId)).for("update");
    const row = rows[0];
    if (!row) {
      return { ok: false, finalStatus: "not_found" };
    }
    if (row.status !== "processing" || row.claimedBy !== workerId || row.claimToken !== claimToken) {
      return { ok: false, finalStatus: row.status };
    }

    if (success) {
      await tx
        .update(scheduledTasks)
        .set({
          status: "completed",
          completedAt: now,
          claimedBy: null,
          claimToken: null,
          visibilityTimeoutAt: null,
        })
        .where(eq(scheduledTasks.id, taskId));
      return { ok: true, finalStatus: "completed" };
    }

    const nextAttempt = row.attemptCount + 1;
    if (nextAttempt >= row.maxAttempts) {
      await tx
        .update(scheduledTasks)
        .set({
          status: "failed",
          attemptCount: nextAttempt,
          lastError: error ?? null,
          deadLetterReason: error ?? "max attempts exceeded",
          claimedBy: null,
          claimToken: null,
          visibilityTimeoutAt: null,
        })
        .where(eq(scheduledTasks.id, taskId));
      return { ok: true, finalStatus: "failed" };
    }

    const nextRetryAt = new Date(now.getTime() + computeBackoffSeconds(nextAttempt) * 1000);
    await tx
      .update(scheduledTasks)
      .set({
        status: "scheduled",
        attemptCount: nextAttempt,
        lastError: error ?? null,
        nextRetryAt,
        runAt: nextRetryAt,
        claimedBy: null,
        claimToken: null,
        visibilityTimeoutAt: null,
      })
      .where(eq(scheduledTasks.id, taskId));
    return { ok: true, finalStatus: "scheduled" };
  });
}

export interface ReclaimResult {
  reclaimedToScheduled: number;
  deadLettered: number;
}

/**
 * Sweeper — quét task 'processing' đã hết visibility_timeout_at (worker chết
 * giữa chừng không complete/heartbeat kịp), gọi định kỳ từ cron
 * (control-plane.cron.ts). `FOR UPDATE SKIP LOCKED` để nhiều lần chạy sweeper
 * chồng nhau (hoặc nhiều instance) không double-reclaim cùng 1 row.
 */
export async function reclaimStuckTasks(limit = 50): Promise<ReclaimResult> {
  const now = new Date();

  return db.transaction(async (tx) => {
    const stuckRows = await tx
      .select()
      .from(scheduledTasks)
      .where(and(eq(scheduledTasks.status, "processing"), isNotNull(scheduledTasks.visibilityTimeoutAt), lte(scheduledTasks.visibilityTimeoutAt, now)))
      .limit(limit)
      .for("update", { skipLocked: true });

    let reclaimedToScheduled = 0;
    let deadLettered = 0;

    for (const row of stuckRows) {
      const nextAttempt = row.attemptCount + 1;
      if (nextAttempt >= row.maxAttempts) {
        await tx
          .update(scheduledTasks)
          .set({
            status: "failed",
            attemptCount: nextAttempt,
            lastError: "visibility timeout exceeded (worker crash) and max attempts reached",
            deadLetterReason: "visibility timeout exceeded, max attempts reached",
            claimedBy: null,
            claimToken: null,
            visibilityTimeoutAt: null,
          })
          .where(eq(scheduledTasks.id, row.id));
        deadLettered++;
      } else {
        const nextRetryAt = new Date(now.getTime() + computeBackoffSeconds(nextAttempt) * 1000);
        await tx
          .update(scheduledTasks)
          .set({
            status: "scheduled",
            attemptCount: nextAttempt,
            lastError: "visibility timeout exceeded (worker crash), reclaimed",
            nextRetryAt,
            runAt: nextRetryAt,
            claimedBy: null,
            claimToken: null,
            visibilityTimeoutAt: null,
          })
          .where(eq(scheduledTasks.id, row.id));
        reclaimedToScheduled++;
      }
    }

    return { reclaimedToScheduled, deadLettered };
  });
}
