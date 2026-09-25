import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import * as schedulerSvc from "./services/control-plane-scheduler.service";

import * as workspaceScheduleSvc from "./services/workspace-schedule.service";
import * as snowflakeRegistrySvc from "./services/snowflake-registry.service";
import * as workspaceInvitationSvc from "./services/workspace-invitation.service";

/**
 * Phase 3 (Durable Queue Recovery, docs/implementation/production-runtime-
 * closure.md §7) — sweeper định kỳ reclaim `scheduled_tasks` bị kẹt ở
 * 'processing' khi worker chết giữa chừng (không complete/heartbeat kịp
 * trước khi hết `visibility_timeout_at`). Chạy mỗi phút — visibility timeout
 * mặc định 120s (xem DEFAULT_VISIBILITY_TIMEOUT_SEC trong
 * control-plane-scheduler.service.ts) nên task kẹt tối đa ~3 phút trước khi
 * được reclaim hoặc dead-letter.
 */
export const reclaimStuckScheduledTasksCron = api({}, async (): Promise<void> => {
  await schedulerSvc.reclaimStuckTasks();
});

const _reclaimStuckScheduledTasksJob = new CronJob("reclaim-stuck-scheduled-tasks", {
  title: "Reclaim stuck scheduled tasks (visibility timeout sweeper)",
  every: "1m",
  endpoint: reclaimStuckScheduledTasksCron,
});

export const dispatchWorkspaceSchedulesCron = api({}, async (): Promise<void> => {
  await workspaceScheduleSvc.dispatchDueWorkspaceSchedules();
});

const _dispatchWorkspaceSchedulesJob = new CronJob("dispatch-workspace-schedules", {
  title: "Dispatch due workspace business schedules",
  every: "1m",
  endpoint: dispatchWorkspaceSchedulesCron,
});

// M2 §2 — gia hạn lease Snowflake generator slot của process control-plane này.
// TTL lease mặc định 60s; heartbeat mỗi phút là biên — hạ TTL / tăng tần suất
// khi chạy nhiều replica. No-op nếu process chưa bootstrap slot.
export const heartbeatSnowflakeGeneratorCron = api({}, async (): Promise<void> => {
  await snowflakeRegistrySvc.heartbeatBoundGenerator(BigInt(Date.now()));
});

const _heartbeatSnowflakeGeneratorJob = new CronJob("heartbeat-snowflake-generator", {
  title: "Renew this control-plane's Snowflake generator slot lease",
  every: "1m",
  endpoint: heartbeatSnowflakeGeneratorCron,
});


// Spec 2026-09-25 §8 — reconciler cho saga cấp membership của invitation:
// chiếu grant đã `core_granted` và hỏi lại core (idempotent) cho grant
// `requested` bị bỏ dở do crash/timeout giữa chừng.
export const reconcileInvitationGrantsCron = api({}, async (): Promise<void> => {
  await workspaceInvitationSvc.reconcileInvitationGrants();
});

const _reconcileInvitationGrantsJob = new CronJob("reconcile-invitation-grants", {
  title: "Reconcile pending organization invitation membership grants",
  every: "5m",
  endpoint: reconcileInvitationGrantsCron,
});
