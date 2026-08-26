import { eq, and, lte, gte, sql, count } from "drizzle-orm";
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

export function validateIanaTimezone(tz: string): void {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: tz });
  } catch {
    throw new Error(`invalid IANA timezone: '${tz}'`);
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
    throw new Error(`invalid hour (${h}) or minute (${m})`);
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
  companyId: string;
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
    throw new Error("promptTemplate cannot be empty");
  }

  // Check active schedule quota
  const [{ value: activeCount }] = await db
    .select({ value: count() })
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.companyId, input.companyId),
        eq(workspaceScheduleDefinitions.workspaceId, input.workspaceId),
        eq(workspaceScheduleDefinitions.state, "enabled")
      )
    );

  if (Number(activeCount) >= MAX_ACTIVE_SCHEDULES_PER_WORKSPACE) {
    throw new Error(
      `active schedule quota exceeded: maximum of ${MAX_ACTIVE_SCHEDULES_PER_WORKSPACE} enabled schedules allowed per workspace`
    );
  }

  let nextRunAt: Date | null = null;
  if (input.scheduleKind === "one_time") {
    if (!input.runAt || input.runAt <= new Date()) {
      throw new Error("one_time schedule requires runAt in the future");
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
      companyId: input.companyId,
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

export async function dispatchDueWorkspaceSchedules(
  now: Date = new Date(),
  limit: number = DEFAULT_DISPATCH_BATCH_SIZE
): Promise<number> {
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

  let dispatchedCount = 0;

  for (const def of dueDefinitions) {
    const scheduledFor = def.nextRunAt || now;

    // Check rolling 24h quota
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 3600000);
    const [{ value: executions24h }] = await db
      .select({ value: count() })
      .from(workspaceScheduleExecutions)
      .where(
        and(
          eq(workspaceScheduleExecutions.companyId, def.companyId),
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

    try {
      const [execution] = await db
        .insert(workspaceScheduleExecutions)
        .values({
          id: execId,
          definitionId: def.id,
          companyId: def.companyId,
          workspaceId: def.workspaceId,
          scheduledFor,
          promptTemplateSnapshot: def.promptTemplate,
          agentProfileSnapshot: def.agentProfile,
          connectorGrantIdsSnapshot: def.connectorGrantIds || [],
          state: "queued",
        })
        .onConflictDoNothing({ target: [workspaceScheduleExecutions.definitionId, workspaceScheduleExecutions.scheduledFor] })
        .returning();

      if (!execution) {
        // Idempotency: occurrence already created
        continue;
      }

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
        .set({ taskId: task.id, updatedAt: new Date() })
        .where(eq(workspaceScheduleExecutions.id, execution.id));

      // Advance next_run_at
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

      dispatchedCount++;
    } catch (err) {
      console.error(`[ScheduleDispatcher] Error dispatching schedule ${def.id}:`, err);
    }
  }

  return dispatchedCount;
}

export async function runScheduleNow(input: {
  scheduleId: string;
  companyId: string;
  workspaceId: string;
  principalId: string;
}) {
  const [def] = await db
    .select()
    .from(workspaceScheduleDefinitions)
    .where(
      and(
        eq(workspaceScheduleDefinitions.id, input.scheduleId),
        eq(workspaceScheduleDefinitions.companyId, input.companyId),
        eq(workspaceScheduleDefinitions.workspaceId, input.workspaceId)
      )
    );

  if (!def) {
    throw new Error("schedule definition not found in workspace");
  }

  const now = new Date();
  const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  const [execution] = await db
    .insert(workspaceScheduleExecutions)
    .values({
      id: execId,
      definitionId: def.id,
      companyId: def.companyId,
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
