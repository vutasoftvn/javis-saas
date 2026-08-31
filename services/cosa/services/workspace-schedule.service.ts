import { APIError } from "encore.dev/api";
import { scheduleTask } from "./control-plane-scheduler.service";
import {
  ScheduleKind,
  ScheduleState,
  ScheduleExecutionState,
  MAX_ACTIVE_SCHEDULES_PER_WORKSPACE,
  MAX_EXECUTIONS_24H,
  DEFAULT_DISPATCH_BATCH_SIZE,
  MAX_ENQUEUE_RETRIES,
  MAX_ENQUEUE_BACKOFF_SEC,
} from "./schedule/schedule-types";
import {
  validateIanaTimezone,
  calculateNextRun,
  getUtcDateFromTzWallClock,
  getTzDayOfWeek,
} from "./schedule/schedule-recurrence.engine";
import {
  computeEnqueueBackoffSeconds,
  logEnqueueRetryMetric,
} from "./schedule/schedule-retry.policy";
import * as repo from "./schedule/schedule.repository";

// Re-export types and constants to guarantee 100% backward compatibility
export {
  ScheduleKind,
  ScheduleState,
  ScheduleExecutionState,
  MAX_ACTIVE_SCHEDULES_PER_WORKSPACE,
  MAX_EXECUTIONS_24H,
  DEFAULT_DISPATCH_BATCH_SIZE,
  MAX_ENQUEUE_RETRIES,
  MAX_ENQUEUE_BACKOFF_SEC,
  validateIanaTimezone,
  calculateNextRun,
  getUtcDateFromTzWallClock,
  getTzDayOfWeek,
  computeEnqueueBackoffSeconds,
  logEnqueueRetryMetric,
};

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
  const activeCount = await repo.countActiveSchedulesByWorkspace(input.workspaceId);
  if (activeCount >= MAX_ACTIVE_SCHEDULES_PER_WORKSPACE) {
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
  return repo.insertScheduleDefinition({
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
  });
}

export async function dispatchDueWorkspaceSchedules(
  now: Date = new Date(),
  limit: number = DEFAULT_DISPATCH_BATCH_SIZE
): Promise<number> {
  let dispatchedCount = 0;

  // 1. Re-attempt due 'enqueue_retry' executions with null taskId atomically
  const retryExecutions = await repo.claimDueEnqueueRetries(now, limit);

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

      await repo.updateExecutionTaskIdAndQueued(execution.id, task.id);

      // Advance schedule definition nextRunAt if not advanced yet
      const def = await repo.findScheduleDefinitionById(execution.definitionId);
      if (def && (!def.lastRunAt || def.lastRunAt < execution.scheduledFor)) {
        await repo.advanceDefinitionAfterDispatch(def, now);
      }

      dispatchedCount++;
    } catch (retryErr) {
      console.error(`[ScheduleDispatcher] Retry enqueue failed for execution ${execution.id}:`, retryErr);
      await repo.recordEnqueueFailure({
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
  const dueDefinitions = await repo.findDueScheduleDefinitions(now, limit);

  for (const def of dueDefinitions) {
    const scheduledFor = def.nextRunAt || now;

    // Check rolling 24h quota
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 3600000);
    const executions24h = await repo.countExecutionsIn24Hours(def.workspaceId, twentyFourHoursAgo);

    if (executions24h >= MAX_EXECUTIONS_24H) {
      console.warn(
        `[ScheduleDispatcher] Quota reached for workspace ${def.workspaceId} (>= ${MAX_EXECUTIONS_24H} in 24h)`
      );
      continue;
    }

    const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    let execution: repo.ScheduleExecutionRow | undefined = undefined;

    try {
      execution = await repo.insertExecutionOnConflictDoNothing({
        id: execId,
        definitionId: def.id,
        workspaceId: def.workspaceId,
        scheduledFor,
        promptTemplateSnapshot: def.promptTemplate,
        agentProfileSnapshot: def.agentProfile,
        connectorGrantIdsSnapshot: (def.connectorGrantIds as string[]) || [],
        state: "queued",
      });

      if (!execution) {
        // Idempotency: occurrence already exists
        continue;
      }

      const task = await scheduleTask({
        targetSpecId: "cosa.schedule-execution",
        targetSpecKind: "agent",
        coalescingKey: `schedule-execution:${execution.id}`,
        inputPayload: {
          task_type: "scheduled_session",
          schedule_execution_id: execution.id,
        },
      });

      await repo.updateExecutionTaskIdAndQueued(execution.id, task.id);
      await repo.advanceDefinitionAfterDispatch(def, now);

      dispatchedCount++;
    } catch (err) {
      console.error(`[ScheduleDispatcher] Error dispatching schedule ${def.id}:`, err);
      if (execution) {
        await repo.recordEnqueueFailure({
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
  const def = await repo.findScheduleDefinitionByIdAndWorkspace(input.scheduleId, input.workspaceId);
  if (!def) {
    throw APIError.notFound("schedule definition not found in workspace");
  }

  const now = new Date();
  const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  const execution = await repo.insertExecution({
    id: execId,
    definitionId: def.id,
    workspaceId: def.workspaceId,
    scheduledFor: now,
    promptTemplateSnapshot: def.promptTemplate,
    agentProfileSnapshot: def.agentProfile,
    connectorGrantIdsSnapshot: (def.connectorGrantIds as string[]) || [],
    state: "queued",
  });

  const task = await scheduleTask({
    targetSpecId: "cosa.schedule-execution",
    targetSpecKind: "agent",
    coalescingKey: `schedule-execution:${execution.id}`,
    inputPayload: {
      task_type: "scheduled_session",
      schedule_execution_id: execution.id,
    },
  });

  await repo.updateExecutionTaskIdOnly(execution.id, task.id);
  return execution;
}

export async function completeScheduleExecution(input: {
  executionId: string;
  state: ScheduleExecutionState;
  conversationId?: string;
  runId?: string;
  error?: string;
}) {
  return repo.updateExecutionCompletion(input);
}

export async function listWorkspaceSchedules(
  workspaceId: string
): Promise<{ items: repo.ScheduleDefinitionRow[]; total: number }> {
  const items = await repo.listScheduleDefinitions(workspaceId);
  return { items, total: items.length };
}

export async function getScheduleExecution(
  executionId: string
): Promise<repo.ScheduleExecutionRow> {
  const execution = await repo.findExecutionById(executionId);
  if (!execution) {
    throw APIError.notFound("schedule execution not found");
  }
  return execution;
}
