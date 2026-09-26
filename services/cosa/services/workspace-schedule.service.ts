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
  organizationId: string;
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
  projectId: string;
}) {
  const tz = input.timezone || "Asia/Ho_Chi_Minh";
  validateIanaTimezone(tz);

  if (!input.promptTemplate || !input.promptTemplate.trim()) {
    throw APIError.invalidArgument("promptTemplate cannot be empty");
  }
  if (!input.projectId || !input.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }

  // Check active schedule quota
  const activeCount = await repo.countActiveSchedulesByWorkspace(input.organizationId);
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
    organizationId: input.organizationId,
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
    projectId: input.projectId,
    isLegacyUnscoped: false,
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
    const executions24h = await repo.countExecutionsIn24Hours(def.organizationId, twentyFourHoursAgo);

    if (executions24h >= MAX_EXECUTIONS_24H) {
      console.warn(
        `[ScheduleDispatcher] Quota reached for workspace ${def.organizationId} (>= ${MAX_EXECUTIONS_24H} in 24h)`
      );
      continue;
    }

    const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    let execution: repo.ScheduleExecutionRow | undefined = undefined;

    try {
      execution = await repo.insertExecutionOnConflictDoNothing({
        id: execId,
        definitionId: def.id,
        organizationId: def.organizationId,
        scheduledFor,
        promptTemplateSnapshot: def.promptTemplate,
        agentProfileSnapshot: def.agentProfile,
        connectorGrantIdsSnapshot: (def.connectorGrantIds as string[]) || [],
        projectIdSnapshot: def.projectId,
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
  organizationId: string;
  principalId: string;
}) {
  const def = await repo.findScheduleDefinitionByIdAndWorkspace(input.scheduleId, input.organizationId);
  if (!def) {
    throw APIError.notFound("schedule definition not found in workspace");
  }
  // Cùng điều kiện với dispatcher (findDueScheduleDefinitions): business run
  // mới phải có project scope (CLAUDE.md quy tắc 14) và tôn trọng quota 24h.
  if (def.isLegacyUnscoped || !def.projectId) {
    throw APIError.failedPrecondition("schedule has no project scope; re-create it inside a project");
  }

  const now = new Date();
  const executions24h = await repo.countExecutionsIn24Hours(
    def.organizationId,
    new Date(now.getTime() - 24 * 3600000)
  );
  if (executions24h >= MAX_EXECUTIONS_24H) {
    throw APIError.resourceExhausted("schedule execution quota for the last 24h reached");
  }
  const execId = `sched_exec_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  const execution = await repo.insertExecution({
    id: execId,
    definitionId: def.id,
    organizationId: def.organizationId,
    scheduledFor: now,
    promptTemplateSnapshot: def.promptTemplate,
    agentProfileSnapshot: def.agentProfile,
    connectorGrantIdsSnapshot: (def.connectorGrantIds as string[]) || [],
    projectIdSnapshot: def.projectId,
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
  organizationId: string
): Promise<{ items: repo.ScheduleDefinitionRow[]; total: number }> {
  const items = await repo.listScheduleDefinitions(organizationId);
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

export async function rebindLegacyWorkspaceSchedule(input: {
  scheduleId: string;
  organizationId: string;
  projectId: string;
  principalId?: string;
}): Promise<repo.ScheduleDefinitionRow> {
  const { scheduleId, organizationId, projectId } = input;
  if (!projectId || !projectId.trim()) {
    throw APIError.invalidArgument("projectId is required for schedule rebind");
  }

  const def = await repo.findScheduleDefinitionByIdAndWorkspace(scheduleId, organizationId);
  if (!def) {
    throw APIError.notFound("schedule definition not found in workspace");
  }

  if (!def.isLegacyUnscoped || def.state !== "paused") {
    throw APIError.failedPrecondition("only paused legacy unscoped schedules can be rebound");
  }

  const updated = await repo.rebindLegacyScheduleDefinition({
    scheduleId,
    organizationId,
    projectId: projectId.trim(),
  });

  if (!updated) {
    throw APIError.internal("failed to rebind legacy schedule definition");
  }

  return updated;
}

