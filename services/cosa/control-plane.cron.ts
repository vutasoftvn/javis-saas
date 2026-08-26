import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import * as schedulerSvc from "./services/control-plane-scheduler.service";

import * as workspaceScheduleSvc from "./services/workspace-schedule.service";

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

