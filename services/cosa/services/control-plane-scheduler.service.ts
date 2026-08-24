import { randomUUID } from "node:crypto";
import { and, eq, isNull, lte, sql } from "drizzle-orm";
import { db, schema } from "../models/db";

const { scheduledTasks } = schema;

/**
 * Port của packages/agent_core/coordination/scheduler.py::RunScheduler sang
 * durable Postgres (ADR-CONTROLPLANE-001 §2). Bản gốc Python hoàn toàn
 * in-memory (dict + asyncio.Lock trong 1 process).
 *
 * CHƯA verify được bằng Postgres thật trong môi trường phát triển này — xem
 * ghi chú trong control-plane-lease.service.ts.
 */

export interface ScheduleParams {
  targetSpecId: string;
  inputPayload: Record<string, unknown>;
  coalescingKey?: string;
  runAt?: Date;
  targetSpecKind?: string;
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
}

export async function scheduleTask(params: ScheduleParams): Promise<ScheduledTaskRow> {
  const now = new Date();
  const runAt = params.runAt ?? now;

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
    };
    await tx.insert(scheduledTasks).values(row);
    return row as ScheduledTaskRow;
  });
}

/**
 * Atomic claim: `FOR UPDATE SKIP LOCKED` để nhiều worker poll đồng thời không
 * lấy trùng task (khác với bản Python gốc chỉ chạy 1 process nên không cần
 * SKIP LOCKED — đây là cải tiến thật sự khi có nhiều worker/replica).
 */
export async function pollDueTasks(limit = 10): Promise<ScheduledTaskRow[]> {
  const now = new Date();

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
    await tx
      .update(scheduledTasks)
      .set({ status: "processing" })
      .where(sql`${scheduledTasks.id} = ANY(${ids})`);

    const claimed = await tx
      .select()
      .from(scheduledTasks)
      .where(sql`${scheduledTasks.id} = ANY(${ids})`);
    return claimed as ScheduledTaskRow[];
  });
}

export async function completeTask(taskId: string, success = true): Promise<void> {
  await db
    .update(scheduledTasks)
    .set({ status: success ? "completed" : "failed" })
    .where(eq(scheduledTasks.id, taskId));
}
