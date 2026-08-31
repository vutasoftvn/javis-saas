import { eq, and, lte, gte, sql, count, inArray, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { ScheduleKind, ScheduleState, MAX_ENQUEUE_RETRIES } from "./schedule-types";
import { computeEnqueueBackoffSeconds, logEnqueueRetryMetric } from "./schedule-retry.policy";
import { calculateNextRun } from "./schedule-recurrence.engine";

const {
  workspaceScheduleDefinitions,
  workspaceScheduleExecutions,
} = schema;

export type ScheduleDefinitionRow = typeof workspaceScheduleDefinitions.$inferSelect;
export type ScheduleExecutionRow = typeof workspaceScheduleExecutions.$inferSelect;

export async function countActiveSchedulesByWorkspace(workspaceId: string): Promise<number> {
  const [{ value }] = await db
    .select({ value: count() })
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.workspaceId, workspaceId),
        eq(workspaceScheduleDefinitions.state, "enabled")
      )
    );
  return Number(value);
}

export async function countExecutionsIn24Hours(workspaceId: string, since: Date): Promise<number> {
  const [{ value }] = await db
    .select({ value: count() })
    .from(workspaceScheduleExecutions)
    .where(
      and(
        eq(workspaceScheduleExecutions.workspaceId, workspaceId),
        gte(workspaceScheduleExecutions.createdAt, since)
      )
    );
  return Number(value);
}

export async function insertScheduleDefinition(values: {
  id: string;
  workspaceId: string;
  createdBy: string;
  scheduleKind: ScheduleKind;
  timezone: string;
  runAt: Date | null;
  hour: number | null;
  minute: number | null;
  weekdays: number[];
  promptTemplate: string;
  agentProfile: string;
  connectorGrantIds: string[];
  state: ScheduleState;
  nextRunAt: Date | null;
}): Promise<ScheduleDefinitionRow> {
  const [created] = await db
    .insert(workspaceScheduleDefinitions)
    .values(values)
    .returning();
  return created;
}

export async function findScheduleDefinitionByIdAndWorkspace(
  id: string,
  workspaceId: string
): Promise<ScheduleDefinitionRow | undefined> {
  const [def] = await db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.id, id),
        eq(workspaceScheduleDefinitions.workspaceId, workspaceId)
      )
    );
  return def;
}

export async function findScheduleDefinitionById(id: string): Promise<ScheduleDefinitionRow | undefined> {
  const [def] = await db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(eq(workspaceScheduleDefinitions.id, id));
  return def;
}

export async function listScheduleDefinitions(workspaceId: string): Promise<ScheduleDefinitionRow[]> {
  return db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(eq(workspaceScheduleDefinitions.workspaceId, workspaceId))
    .orderBy(desc(workspaceScheduleDefinitions.createdAt));
}

export async function findDueScheduleDefinitions(
  now: Date,
  limit: number
): Promise<ScheduleDefinitionRow[]> {
  return db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.state, "enabled"),
        lte(workspaceScheduleDefinitions.nextRunAt, now)
      )
    )
    .limit(limit);
}

/**
 * Claim due 'enqueue_retry' rows atomically via `FOR UPDATE SKIP LOCKED`
 */
export async function claimDueEnqueueRetries(
  now: Date,
  limit: number
): Promise<ScheduleExecutionRow[]> {
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
 * Ghi nhận một lần enqueue thất bại và tính toán retry/terminal state
 */
export async function recordEnqueueFailure(params: {
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
 * Advance nextRunAt/lastRunAt của schedule definition sau khi taskId được lưu durable
 */
export async function advanceDefinitionAfterDispatch(
  def: ScheduleDefinitionRow,
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

export async function insertExecutionOnConflictDoNothing(values: {
  id: string;
  definitionId: string;
  workspaceId: string;
  scheduledFor: Date;
  promptTemplateSnapshot: string;
  agentProfileSnapshot: string;
  connectorGrantIdsSnapshot: string[];
  state: "queued";
}): Promise<ScheduleExecutionRow | undefined> {
  const [inserted] = await db
    .insert(workspaceScheduleExecutions)
    .values(values)
    .onConflictDoNothing({ target: [workspaceScheduleExecutions.definitionId, workspaceScheduleExecutions.scheduledFor] })
    .returning();
  return inserted;
}

export async function insertExecution(values: {
  id: string;
  definitionId: string;
  workspaceId: string;
  scheduledFor: Date;
  promptTemplateSnapshot: string;
  agentProfileSnapshot: string;
  connectorGrantIdsSnapshot: string[];
  state: "queued";
}): Promise<ScheduleExecutionRow> {
  const [execution] = await db
    .insert(workspaceScheduleExecutions)
    .values(values)
    .returning();
  return execution;
}

export async function updateExecutionTaskIdAndQueued(
  executionId: string,
  taskId: string
): Promise<void> {
  await db
    .update(workspaceScheduleExecutions)
    .set({ taskId, state: "queued", error: null, nextAttemptAt: null, updatedAt: new Date() })
    .where(eq(workspaceScheduleExecutions.id, executionId));
}

export async function updateExecutionTaskIdOnly(
  executionId: string,
  taskId: string
): Promise<void> {
  await db
    .update(workspaceScheduleExecutions)
    .set({ taskId, updatedAt: new Date() })
    .where(eq(workspaceScheduleExecutions.id, executionId));
}

export async function updateExecutionCompletion(input: {
  executionId: string;
  state: string;
  conversationId?: string;
  runId?: string;
  error?: string;
}): Promise<ScheduleExecutionRow | null> {
  const [updated] = await db
    .update(workspaceScheduleExecutions)
    .set({
      state: input.state as any,
      conversationId: input.conversationId || null,
      runId: input.runId || null,
      error: input.error || null,
      updatedAt: new Date(),
    })
    .where(eq(workspaceScheduleExecutions.id, input.executionId))
    .returning();
  return updated || null;
}

export async function findExecutionById(executionId: string): Promise<ScheduleExecutionRow | undefined> {
  const [execution] = await db
    .select()
    .from(workspaceScheduleExecutions)
    .where(eq(workspaceScheduleExecutions.id, executionId));
  return execution;
}
