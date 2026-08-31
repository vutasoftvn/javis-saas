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
export const MAX_ENQUEUE_BACKOFF_SEC = 300;
