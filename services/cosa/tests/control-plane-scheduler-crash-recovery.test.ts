import { describe, it, expect, beforeEach } from "vitest";
import * as schedulerSvc from "../services/control-plane-scheduler.service";
import * as leaseSvc from "../services/control-plane-lease.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

const { scheduledTasks, workers } = schema;

// `pollDueTasks` claim theo thứ tự run_at (cũ nhất trước) trên TOÀN bộ bảng
// — dọn sạch trước mỗi test để task vừa tạo trong test không bị các row sót
// lại từ test trước (hoặc lần chạy trước) che khuất khỏi top `limit`.
beforeEach(async () => {
  await db.delete(scheduledTasks);
});

/**
 * Phase 3 — Durable Queue Recovery (docs/implementation/production-runtime-
 * closure.md §7, exit criteria "cả 8 crash test pass"). Test trực tiếp qua
 * service function (không qua HTTP) với Postgres THẬT (không mock) — đúng
 * pattern control-plane.test.ts hiện có. `visibilityTimeoutSec` cực ngắn
 * (0-1s) để mô phỏng "đã hết hạn" mà không phải sleep dài trong test.
 *
 * 8 kịch bản theo plan gốc §7.3:
 *   1. worker crash ngay sau poll
 *   2. worker crash sau lease (run-level, test riêng ở lease service)
 *   3. worker crash giữa model call (tương đương #1 ở tầng scheduler — task
 *      kẹt 'processing' không complete/heartbeat)
 *   4. worker mất heartbeat
 *   5. lease hết hạn (run-level lease, không phải scheduled_tasks claim)
 *   6. stale worker cố completeTask sau khi đã bị reclaim
 *   7. retry vượt max_attempts -> dead-letter
 *   8. hai worker cạnh tranh cùng task (SKIP LOCKED)
 */
describe("Scheduled task crash recovery (Phase 3)", () => {
  it("1. worker crash ngay sau poll: task claimed nhưng không ai complete/heartbeat -> sweeper reclaim về scheduled", async () => {
    const task = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "crash_after_poll" },
    });

    const claimed = await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 0 });
    expect(claimed.some((t) => t.id === task.id)).toBe(true);

    // Worker "crash" — không completeTask, không heartbeat. visibilityTimeoutSec=0
    // nghĩa là visibility_timeout_at đã ở quá khứ ngay khi claim xong.
    await new Promise((r) => setTimeout(r, 20));

    const result = await schedulerSvc.reclaimStuckTasks();
    expect(result.reclaimedToScheduled).toBeGreaterThanOrEqual(1);

    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, task.id));
    expect(rows[0].status).toBe("scheduled");
    expect(rows[0].attemptCount).toBe(1);
    expect(rows[0].claimedBy).toBeNull();
    expect(rows[0].claimToken).toBeNull();
  });

  it("3. worker crash giữa model call: task kẹt 'processing' quá visibility timeout -> reclaim đúng task đó (không đụng task khác)", async () => {
    const stuckTask = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "crash_mid_execution" },
    });
    const healthyTask = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "still_running_fine" },
    });

    await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 0, limit: 1 });
    // healthyTask vẫn 'scheduled' — chưa claim, không nên bị sweeper động vào.
    await new Promise((r) => setTimeout(r, 20));
    await schedulerSvc.reclaimStuckTasks();

    const healthyRows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, healthyTask.id));
    expect(healthyRows[0].status).toBe("scheduled");
    expect(healthyRows[0].attemptCount).toBe(0); // chưa từng bị claim -> không tăng attempt

    const stuckRows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, stuckTask.id));
    expect(stuckRows[0].status).toBe("scheduled");
    expect(stuckRows[0].attemptCount).toBe(1);
  });

  it("4. worker mất heartbeat: heartbeat dừng -> visibility timeout không được gia hạn -> reclaim", async () => {
    const task = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "heartbeat_stopped" },
    });

    const [claimed] = await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 0 });
    expect(claimed.id).toBe(task.id);

    // 1 heartbeat thành công lúc đầu (worker vẫn sống lúc này)...
    const hb1 = await schedulerSvc.heartbeatTask({
      taskId: task.id,
      workerId: "worker_A",
      claimToken: claimed.claimToken!,
      extendSec: 0,
    });
    expect(hb1).toBe(true);

    // ...rồi worker treo, không heartbeat lần 2 nữa. extendSec=0 nên
    // visibility_timeout_at lại ở quá khứ ngay sau lần heartbeat cuối.
    await new Promise((r) => setTimeout(r, 20));
    const result = await schedulerSvc.reclaimStuckTasks();
    expect(result.reclaimedToScheduled).toBeGreaterThanOrEqual(1);

    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, task.id));
    expect(rows[0].status).toBe("scheduled");
  });

  it("6. stale worker cố completeTask sau khi đã bị sweeper reclaim -> fencing từ chối (ok=false), không ghi đè lần claim mới", async () => {
    const task = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "stale_worker_completes_after_reclaim" },
    });

    const [claimedByA] = await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 0 });
    const staleClaimToken = claimedByA.claimToken!;

    await new Promise((r) => setTimeout(r, 20));
    await schedulerSvc.reclaimStuckTasks();

    // Reclaim đặt run_at vào tương lai theo backoff — đẩy về quá khứ để
    // worker B poll được ngay trong test thay vì phải đợi backoff thật.
    await db.update(scheduledTasks).set({ runAt: new Date(Date.now() - 1000) }).where(eq(scheduledTasks.id, task.id));

    // Task giờ 'scheduled' lại — worker B claim được lần mới.
    const [claimedByB] = await schedulerSvc.pollDueTasks({ workerId: "worker_B", visibilityTimeoutSec: 120 });
    expect(claimedByB.id).toBe(task.id);
    expect(claimedByB.claimToken).not.toBe(staleClaimToken);

    // Worker A (stale) giờ mới "tỉnh dậy" và cố complete với claim_token cũ.
    const staleComplete = await schedulerSvc.completeTask({
      taskId: task.id,
      workerId: "worker_A",
      claimToken: staleClaimToken,
      success: true,
    });
    expect(staleComplete.ok).toBe(false);

    // Task vẫn đang được worker B xử lý — không bị worker A ghi đè thành completed.
    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, task.id));
    expect(rows[0].status).toBe("processing");
    expect(rows[0].claimedBy).toBe("worker_B");

    // Worker B complete hợp lệ — fencing chấp nhận.
    const validComplete = await schedulerSvc.completeTask({
      taskId: task.id,
      workerId: "worker_B",
      claimToken: claimedByB.claimToken!,
      success: true,
    });
    expect(validComplete.ok).toBe(true);
    expect(validComplete.finalStatus).toBe("completed");
  });

  it("7. retry vượt max_attempts -> dead-letter (status=failed, deadLetterReason set), không retry vô hạn", async () => {
    const task = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "always_fails" },
      maxAttempts: 2,
    });

    // Lần thử 1: fail -> quay lại 'scheduled' (attempt_count=1 < max_attempts=2).
    const [claim1] = await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 120 });
    const result1 = await schedulerSvc.completeTask({
      taskId: task.id,
      workerId: "worker_A",
      claimToken: claim1.claimToken!,
      success: false,
      error: "boom 1",
    });
    expect(result1.finalStatus).toBe("scheduled");

    // Backoff đẩy run_at vào tương lai — set lại run_at về quá khứ để poll
    // ngay trong test thay vì phải sleep theo backoff thật.
    await db.update(scheduledTasks).set({ runAt: new Date(Date.now() - 1000) }).where(eq(scheduledTasks.id, task.id));

    // Lần thử 2: fail -> attempt_count=2 >= max_attempts=2 -> dead-letter.
    const [claim2] = await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 120 });
    const result2 = await schedulerSvc.completeTask({
      taskId: task.id,
      workerId: "worker_A",
      claimToken: claim2.claimToken!,
      success: false,
      error: "boom 2",
    });
    expect(result2.finalStatus).toBe("failed");

    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, task.id));
    expect(rows[0].status).toBe("failed");
    expect(rows[0].attemptCount).toBe(2);
    expect(rows[0].deadLetterReason).toBe("boom 2");

    // Task đã dead-letter -> không còn poll được nữa (không retry vô hạn).
    const rePolled = await schedulerSvc.pollDueTasks({ workerId: "worker_B", visibilityTimeoutSec: 120 });
    expect(rePolled.some((t) => t.id === task.id)).toBe(false);
  });

  it("8. hai worker cạnh tranh cùng task -> SKIP LOCKED đảm bảo chỉ 1 worker claim được", async () => {
    const task = await schedulerSvc.scheduleTask({
      targetSpecId: "cosa.test",
      inputPayload: { scenario: "concurrent_claim" },
    });

    const [resultA, resultB] = await Promise.all([
      schedulerSvc.pollDueTasks({ workerId: "worker_A", limit: 1 }),
      schedulerSvc.pollDueTasks({ workerId: "worker_B", limit: 1 }),
    ]);

    const claimedByA = resultA.some((t) => t.id === task.id);
    const claimedByB = resultB.some((t) => t.id === task.id);
    // Đúng 1 trong 2 worker claim được — không cả hai, không cả không ai.
    expect(claimedByA !== claimedByB).toBe(true);

    const rows = await db.select().from(scheduledTasks).where(eq(scheduledTasks.id, task.id));
    expect(rows[0].claimedBy).toBe(claimedByA ? "worker_A" : "worker_B");
  });
});

/**
 * Kịch bản #2 (worker crash sau lease) và #5 (lease hết hạn) thuộc tầng
 * runtime_leases (run-level), khác `scheduled_tasks` claim (task-level) —
 * test riêng ở control-plane-lease.service.
 */
describe("Runtime lease crash recovery (Phase 3, run-level)", () => {
  it("2/5. lease hết hạn (worker crash sau khi acquire lease, không release) -> worker khác acquire được sau khi expire", async () => {
    const runId = `run_crash_after_lease_${Date.now()}`;

    // runtime_leases.worker_id có FK tới workers.id — đăng ký 2 worker trước.
    await db
      .insert(workers)
      .values([
        { id: "worker_A", runtimeKind: "test" },
        { id: "worker_B", runtimeKind: "test" },
      ])
      .onConflictDoNothing();

    const first = await leaseSvc.acquireLease({ runId, workerId: "worker_A", ttlSec: -1 });
    expect(first.success).toBe(true);

    // ttlSec=-1 -> expiresAt đã ở quá khứ ngay lập tức, mô phỏng lease "đã hết hạn"
    // do worker_A crash giữa chừng không renew/release kịp.
    const second = await leaseSvc.acquireLease({ runId, workerId: "worker_B", ttlSec: 30 });
    expect(second.success).toBe(true);
    expect(second.leaseToken).not.toBe(first.leaseToken);

    // worker_A (stale) không còn renew được — lease đã thuộc về worker_B.
    const staleRenew = await leaseSvc.renewLease({ runId, workerId: "worker_A", leaseToken: first.leaseToken! });
    expect(staleRenew).toBe(false);
  });
});
