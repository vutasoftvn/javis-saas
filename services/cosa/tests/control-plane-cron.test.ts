import { describe, it, expect, beforeEach } from "vitest";
import { reclaimStuckScheduledTasksCron } from "../control-plane.cron";
import * as schedulerSvc from "../services/control-plane-scheduler.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

const { scheduledTasks } = schema;

/**
 * Part 2E.3 — sweeper end-to-end qua ĐÚNG endpoint mà CronJob
 * `reclaim-stuck-scheduled-tasks` (every: "1m") gọi. Cron schedule tự nó
 * không test được trong CI, nên test endpoint + giữ cron config trong
 * control-plane.cron.ts là đủ (xem docs/runbooks/dead-letter-queue.md).
 *
 * Postgres THẬT (không mock) — đúng pattern control-plane-scheduler-crash-
 * recovery.test.ts.
 */
describe("reclaim-stuck-scheduled-tasks cron endpoint (Part 2E.3)", () => {
  beforeEach(async () => {
    await db.delete(scheduledTasks);
  });

  it("task kẹt 'processing' quá visibility timeout -> cron tick đưa về 'scheduled', attempt_count++", async () => {
    const task = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "cron_reclaims_stuck" },
    });

    // Worker claim rồi "biến mất" (không complete/heartbeat). visibilityTimeoutSec=0
    // -> visibility_timeout_at ở quá khứ ngay khi claim xong.
    const claimed = await schedulerSvc.pollDueTasks({
      workerId: "worker_ghost",
      visibilityTimeoutSec: 0,
    });
    expect(claimed.some((t) => t.id === task.id)).toBe(true);
    await new Promise((r) => setTimeout(r, 20));

    // Mô phỏng 1 cron tick — gọi đúng endpoint CronJob dùng.
    await reclaimStuckScheduledTasksCron();

    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, task.id));
    expect(rows[0].status).toBe("scheduled");
    expect(rows[0].attemptCount).toBe(1);
    expect(rows[0].claimedBy).toBeNull();
    expect(rows[0].claimToken).toBeNull();
  });

  it("cron tick không đụng task đang chạy khoẻ (chưa hết visibility timeout)", async () => {
    const healthy = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "cron_leaves_healthy_alone" },
    });

    await schedulerSvc.pollDueTasks({ workerId: "worker_ok", visibilityTimeoutSec: 120 });
    await reclaimStuckScheduledTasksCron();

    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, healthy.id));
    expect(rows[0].status).toBe("processing");
    expect(rows[0].claimedBy).toBe("worker_ok");
    expect(rows[0].attemptCount).toBe(0);
  });
});
