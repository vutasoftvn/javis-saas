import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { scheduledTasks } = schema;

/**
 * P1 Task 7 — durable hierarchical supervisor. Child task là một row
 * `scheduled_tasks` bình thường (tái dùng claim/fence/DLQ/reclaim) cộng các
 * cột edge: parent_task_id / child_id / depends_on / join_policy /
 * join_quorum. `DurableSupervisor` (packages/agent/coordination) gọi qua
 * `HttpControlPlaneSchedulerClient`.
 */

export interface ScheduleChildParams {
  parentTaskId: string;
  childId: string;
  targetSpecId: string;
  targetSpecKind?: string;
  inputPayload: Record<string, unknown>;
  dependsOn?: string[];
  joinPolicy: "all" | "any" | "quorum";
  joinQuorum?: number | null;
  maxAttempts?: number;
}

export interface ChildRow {
  childId: string;
  scheduledTaskId: string;
  status: string;
  dependsOn: string[];
  joinPolicy: string | null;
  joinQuorum: number | null;
  result: unknown;
  completionKey: string | null;
}

function mapChild(r: typeof scheduledTasks.$inferSelect): ChildRow {
  return {
    childId: r.childId as string,
    scheduledTaskId: r.id,
    status: r.status,
    dependsOn: (r.dependsOn as string[]) ?? [],
    joinPolicy: r.joinPolicy,
    joinQuorum: r.joinQuorum,
    result: r.childResult ?? null,
    completionKey: r.completionKey,
  };
}

async function completedChildIds(tx: any, parentTaskId: string): Promise<Set<string>> {
  const rows = await tx
    .select()
    .from(scheduledTasks)
    .where(and(eq(scheduledTasks.parentTaskId, parentTaskId), eq(scheduledTasks.status, "completed")));
  return new Set(rows.map((r: any) => r.childId as string));
}

export async function scheduleChildTask(params: ScheduleChildParams): Promise<ChildRow> {
  const deps = params.dependsOn ?? [];
  const now = new Date();

  return db.transaction(async (tx) => {
    const existing = (
      await tx
        .select()
        .from(scheduledTasks)
        .where(
          and(
            eq(scheduledTasks.parentTaskId, params.parentTaskId),
            eq(scheduledTasks.childId, params.childId),
          ),
        )
        .for("update")
    )[0];
    if (existing) return mapChild(existing);

    const done = await completedChildIds(tx, params.parentTaskId);
    const blocked = deps.length > 0 && !deps.every((d) => done.has(d));

    const row = {
      id: `child_${randomUUID().replace(/-/g, "").slice(0, 12)}`,
      coalescingKey: null,
      targetSpecId: params.targetSpecId,
      targetSpecKind: params.targetSpecKind ?? "agent",
      inputPayload: params.inputPayload,
      runAt: now,
      status: blocked ? "blocked" : "scheduled",
      createdAt: now,
      attemptCount: 0,
      maxAttempts: params.maxAttempts ?? 5,
      claimedBy: null,
      claimToken: null,
      claimedAt: null,
      heartbeatAt: null,
      visibilityTimeoutAt: null,
      lastError: null,
      nextRetryAt: null,
      completedAt: null,
      deadLetterReason: null,
      parentTaskId: params.parentTaskId,
      childId: params.childId,
      dependsOn: deps,
      joinPolicy: params.joinPolicy,
      joinQuorum: params.joinQuorum ?? null,
      childResult: null,
      completionKey: null,
    };
    await tx.insert(scheduledTasks).values(row);
    return mapChild(row as typeof scheduledTasks.$inferSelect);
  });
}

export async function listChildren(parentTaskId: string): Promise<ChildRow[]> {
  const rows = await db
    .select()
    .from(scheduledTasks)
    .where(eq(scheduledTasks.parentTaskId, parentTaskId));
  return rows.map(mapChild);
}

export interface CompleteChildParams {
  parentTaskId: string;
  childId: string;
  result: Record<string, unknown>;
  idempotencyKey: string;
}

export async function completeChild(
  params: CompleteChildParams,
): Promise<{ ok: boolean; deduped: boolean }> {
  const now = new Date();
  return db.transaction(async (tx) => {
    const row = (
      await tx
        .select()
        .from(scheduledTasks)
        .where(
          and(
            eq(scheduledTasks.parentTaskId, params.parentTaskId),
            eq(scheduledTasks.childId, params.childId),
          ),
        )
        .for("update")
    )[0];
    if (!row) return { ok: false, deduped: false };

    if (row.status === "completed" && row.completionKey === params.idempotencyKey) {
      return { ok: true, deduped: true };
    }

    await tx
      .update(scheduledTasks)
      .set({
        status: "completed",
        completedAt: now,
        childResult: params.result,
        completionKey: params.idempotencyKey,
        claimedBy: null,
        claimToken: null,
        visibilityTimeoutAt: null,
      })
      .where(eq(scheduledTasks.id, row.id));

    // Unblock siblings whose depends_on ⊆ completed set.
    const done = await completedChildIds(tx, params.parentTaskId);
    const blockedSiblings = await tx
      .select()
      .from(scheduledTasks)
      .where(and(eq(scheduledTasks.parentTaskId, params.parentTaskId), eq(scheduledTasks.status, "blocked")))
      .for("update");
    for (const sib of blockedSiblings) {
      const deps = (sib.dependsOn as string[]) ?? [];
      if (deps.every((d) => done.has(d))) {
        await tx.update(scheduledTasks).set({ status: "scheduled" }).where(eq(scheduledTasks.id, sib.id));
      }
    }
    return { ok: true, deduped: false };
  });
}

export interface JoinResult {
  satisfied: boolean;
  completed: string[];
  pending: string[];
}

export async function resolveJoin(parentTaskId: string): Promise<JoinResult> {
  const children = await listChildren(parentTaskId);
  const completed = children.filter((c) => c.status === "completed").map((c) => c.childId);
  const pending = children.filter((c) => c.status !== "completed").map((c) => c.childId);
  const policy = children[0]?.joinPolicy ?? "all";
  const quorum = children[0]?.joinQuorum ?? children.length;

  let satisfied: boolean;
  if (policy === "any") satisfied = completed.length >= 1;
  else if (policy === "quorum") satisfied = completed.length >= quorum;
  else satisfied = children.length > 0 && pending.length === 0;

  return { satisfied, completed, pending };
}
