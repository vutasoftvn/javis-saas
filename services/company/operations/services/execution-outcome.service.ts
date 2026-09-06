import { APIError } from "encore.dev/api";
import { and, eq, isNull, ne } from "drizzle-orm";
import { db } from "../models/db";
import { tasks, weeklyCommitments } from "../../shared/db/schema/operations";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";

export interface LinearProgressParams {
  baseline: number | null | undefined;
  target: number | null | undefined;
  current: number | null | undefined;
}

/**
 * Computes linear progress between baseline and target values, clamped to [0, 1].
 * Returns null if baseline, target or current are missing/non-finite, or if target === baseline.
 * Handles both increasing (target > baseline) and decreasing (target < baseline) directions.
 */
export function computeLinearProgress(params: LinearProgressParams): number | null {
  const { baseline, target, current } = params;

  if (
    baseline === null ||
    baseline === undefined ||
    target === null ||
    target === undefined ||
    current === null ||
    current === undefined
  ) {
    return null;
  }

  if (
    !Number.isFinite(baseline) ||
    !Number.isFinite(target) ||
    !Number.isFinite(current)
  ) {
    return null;
  }

  if (target === baseline) {
    return null;
  }

  if (target > baseline) {
    // Increasing goal
    const progress = (current - baseline) / (target - baseline);
    return Math.max(0, Math.min(1, progress));
  } else {
    // Decreasing goal
    const progress = (baseline - current) / (baseline - target);
    return Math.max(0, Math.min(1, progress));
  }
}

export interface CommitmentExecutionItem {
  id?: string;
  status: string;
  hasEligibleEvidence?: boolean;
}

/**
 * Execution score = (completed commitments with eligible evidence) / (locked commitments at week start).
 * Default equal weight.
 * Returns null if denominator is 0 (zero commitments locked).
 */
export function calculateExecutionScore(
  commitments: readonly CommitmentExecutionItem[]
): number | null {
  if (!commitments || commitments.length === 0) {
    return null;
  }

  const denominator = commitments.length;
  let completedCount = 0;

  for (const c of commitments) {
    const isDone = c.status.toLowerCase() === "done";
    const evidenceOk = c.hasEligibleEvidence !== false;
    if (isDone && evidenceOk) {
      completedCount++;
    }
  }

  return completedCount / denominator;
}

export interface KeyResultOutcomeItem {
  id?: string;
  score: number | null;
}

/**
 * Outcome score = average of available KR progress scores.
 * Returns null if no valid KR scores are available.
 */
export function calculateOutcomeScore(
  krItems: readonly KeyResultOutcomeItem[]
): number | null {
  if (!krItems || krItems.length === 0) {
    return null;
  }

  const validScores = krItems
    .map((k) => k.score)
    .filter((s): s is number => s !== null && Number.isFinite(s));

  if (validScores.length === 0) {
    return null;
  }

  const sum = validScores.reduce((acc, s) => acc + s, 0);
  return sum / validScores.length;
}

export interface ValidateTaskCompletionParams {
  taskId: string;
  expectedVersion?: number;
  evidenceRefs?: string[];
}

export interface ValidateTaskCompletionResult {
  taskId: string;
  status: string;
  revision: number;
}

/**
 * Validates task completion criteria and records task completion event.
 * Enforces CAS on task revision and verifies workspace boundaries.
 */
export async function validateTaskCompletion(
  ctx: TenantContext,
  params: ValidateTaskCompletionParams
): Promise<ValidateTaskCompletionResult> {
  const wsId = BigInt(ctx.workspaceId);
  const taskIdBig = BigInt(params.taskId);

  return await db.transaction(async (tx) => {
    const [task] = await tx
      .select()
      .from(tasks)
      .where(and(eq(tasks.id, taskIdBig), eq(tasks.workspaceId, wsId), isNull(tasks.deletedAt)))
      .limit(1);

    if (!task) {
      throw APIError.notFound(`Task ${params.taskId} not found`);
    }

    if (params.expectedVersion !== undefined && task.revision !== params.expectedVersion) {
      throw APIError.failedPrecondition(
        `Task revision conflict: expected ${params.expectedVersion}, current is ${task.revision}`
      );
    }

    // If task is already done, return current state
    if (task.status === "done") {
      return {
        taskId: task.id.toString(),
        status: "done",
        revision: task.revision,
      };
    }

    const nextRevision = (task.revision ?? 1) + 1;
    const now = new Date();

    // IA23: CAS trên chính revision vừa đọc — trước đây UPDATE không có điều
    // kiện revision trong WHERE, nên 2 lời gọi đồng thời cùng đọc revision N
    // đều tính nextRevision=N+1 và cùng ghi thành công, khiến revision không
    // phản ánh đúng số lần cập nhật thật (mất 1 lần tăng phiên bản).
    const [updated] = await tx
      .update(tasks)
      .set({
        status: "done",
        revision: nextRevision,
        updatedAt: now,
      })
      .where(
        and(
          eq(tasks.id, taskIdBig),
          eq(tasks.workspaceId, wsId),
          eq(tasks.revision, task.revision)
        )
      )
      .returning();

    if (!updated) {
      const err = APIError.aborted(
        `Concurrent modification: task ${params.taskId} revision changed during completion`
      );
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }

    // IA23: chỉ đóng commitment khi TẤT CẢ task khác thuộc cùng commitment
    // cũng đã done — trước đây đóng commitment ngay khi 1 task bất kỳ hoàn
    // thành, bỏ qua các task anh em (sibling) chưa xong.
    if (task.weeklyCommitmentId) {
      const [pendingSibling] = await tx
        .select({ id: tasks.id })
        .from(tasks)
        .where(
          and(
            eq(tasks.weeklyCommitmentId, task.weeklyCommitmentId),
            eq(tasks.workspaceId, wsId),
            isNull(tasks.deletedAt),
            ne(tasks.id, taskIdBig),
            ne(tasks.status, "done")
          )
        )
        .limit(1);

      if (!pendingSibling) {
        await tx
          .update(weeklyCommitments)
          .set({
            status: "done",
            updatedAt: now,
          })
          .where(
            and(
              eq(weeklyCommitments.id, task.weeklyCommitmentId),
              eq(weeklyCommitments.workspaceId, wsId)
            )
          );
      }
    }

    const event = makeBusinessEvent({
      eventType: "operating.task.completed.v1",
      workspaceId: ctx.workspaceId,
      aggregateType: "task",
      aggregateId: params.taskId,
      correlationId: ctx.correlationId || "task-complete",
      actor: { kind: "user", id: ctx.userId || "0" },
      classification: "internal",
      payload: {
        workspaceId: ctx.workspaceId,
        taskId: params.taskId,
        revision: nextRevision,
        evidenceRefs: params.evidenceRefs || [],
        completedAt: now.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      taskId: updated!.id.toString(),
      status: "done",
      revision: nextRevision,
    };
  });
}
