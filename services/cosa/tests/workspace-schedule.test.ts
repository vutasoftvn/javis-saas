import { describe, it, expect, beforeEach, vi } from "vitest";
import { eq } from "drizzle-orm";
import * as scheduleSvc from "../services/workspace-schedule.service";
import * as schedulerSvc from "../services/control-plane-scheduler.service";
import { db, schema } from "../models/db";

const {
  workspaceScheduleDefinitions,
  workspaceScheduleExecutions,
  scheduledTasks,
} = schema;


beforeEach(async () => {
  await db.delete(workspaceScheduleExecutions);
  await db.delete(workspaceScheduleDefinitions);
  await db.delete(scheduledTasks);
});

describe("Workspace Schedules Service & Dispatcher (Task 4)", () => {
  it("creates one_time schedule with valid future timestamp", async () => {
    const future = new Date(Date.now() + 3600000);
    const def = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_1",
      createdBy: "user_alice",
      scheduleKind: "one_time",
      runAt: future,
      promptTemplate: "Run weekly compliance scan",
      agentProfile: "operations",
    });

    expect(def.id).toBeDefined();
    expect(def.state).toBe("enabled");
    expect(def.nextRunAt?.toISOString()).toBe(future.toISOString());
  });

  it("rejects past one_time schedule or invalid timezone", async () => {
    const past = new Date(Date.now() - 10000);
    await expect(
      scheduleSvc.createWorkspaceSchedule({
        workspaceId: "ws_1",
        createdBy: "user_alice",
        scheduleKind: "one_time",
        runAt: past,
        promptTemplate: "Past scan",
      })
    ).rejects.toThrow(/future/i);

    await expect(
      scheduleSvc.createWorkspaceSchedule({
        workspaceId: "ws_1",
        createdBy: "user_alice",
        scheduleKind: "daily",
        timezone: "Invalid/Timezone_Name",
        hour: 9,
        minute: 0,
        promptTemplate: "Daily standup",
      })
    ).rejects.toThrow(/invalid IANA timezone/i);
  });

  it("calculates next daily and weekdays run dates properly", () => {
    const now = new Date("2026-08-26T08:00:00Z"); // 15:00 in Asia/Ho_Chi_Minh (+7)
    
    // Daily at 16:00 VN (+7) -> 09:00 UTC today
    const nextDaily = scheduleSvc.calculateNextRun(
      "daily",
      "Asia/Ho_Chi_Minh",
      16,
      0,
      null,
      now
    );
    expect(nextDaily).not.toBeNull();
    expect(nextDaily!.getUTCHours()).toBe(9);
    expect(nextDaily!.getUTCMinutes()).toBe(0);
  });

  it("dispatches due schedules with snapshot and enqueues low-level scheduled_task", async () => {
    const pastDue = new Date(Date.now() - 5000);
    const def = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_1",
      createdBy: "user_alice",
      scheduleKind: "daily",
      timezone: "Asia/Ho_Chi_Minh",
      hour: 9,
      minute: 0,
      promptTemplate: "Generate morning finance summary",
      agentProfile: "finance",
      connectorGrantIds: ["grant_1"],
    });

    // Manually force nextRunAt to pastDue to simulate cron trigger
    await db
      .update(workspaceScheduleDefinitions)
      .set({ nextRunAt: pastDue })
      .where(eq(workspaceScheduleDefinitions.id, def.id));


    const dispatched = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
    expect(dispatched).toBe(1);

    // Verify execution record
    const executions = await db.select().from(workspaceScheduleExecutions);
    expect(executions.length).toBe(1);
    expect(executions[0].promptTemplateSnapshot).toBe("Generate morning finance summary");
    expect(executions[0].agentProfileSnapshot).toBe("finance");
    expect(executions[0].taskId).toBeDefined();
    expect(executions[0].state).toBe("queued");

    // Verify low level task
    const tasks = await db.select().from(scheduledTasks);
    expect(tasks.length).toBe(1);
    expect((tasks[0].inputPayload as any).schedule_execution_id).toBe(executions[0].id);

    // Idempotent: re-dispatching now should not create a duplicate execution
    const reDispatched = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
    expect(reDispatched).toBe(0);
  });

  it("handles scheduleTask failure gracefully with enqueue_retry and retries on next tick", async () => {
    const pastDue = new Date(Date.now() - 5000);
    const def = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_1",
      createdBy: "user_alice",
      scheduleKind: "daily",
      timezone: "Asia/Ho_Chi_Minh",
      hour: 9,
      minute: 0,
      promptTemplate: "Retryable scan",
    });

    await db
      .update(workspaceScheduleDefinitions)
      .set({ nextRunAt: pastDue })
      .where(eq(workspaceScheduleDefinitions.id, def.id));

    let attempts = 0;
    const originalScheduleTask = schedulerSvc.scheduleTask;
    const spy = vi.spyOn(schedulerSvc, "scheduleTask").mockImplementation(async (input: any) => {
      attempts++;
      if (attempts === 1) {
        throw new Error("Simulated enqueue failure");
      }
      return originalScheduleTask(input);
    });

    try {
      // First tick: scheduleTask fails
      const firstDispatch = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
      expect(firstDispatch).toBe(0);

      // Verify execution is in 'enqueue_retry' and taskId is null
      const executions = await db.select().from(workspaceScheduleExecutions);
      expect(executions.length).toBe(1);
      expect(executions[0].taskId).toBeNull();
      expect(executions[0].state).toBe("enqueue_retry");

      // Verify definition nextRunAt was NOT advanced
      const [defAfterFirst] = await db
        .select()
        .from(workspaceScheduleDefinitions)
        .where(eq(workspaceScheduleDefinitions.id, def.id));
      expect(defAfterFirst.nextRunAt?.getTime()).toBe(pastDue.getTime());

      // Second tick: retry succeeds
      const secondDispatch = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
      expect(secondDispatch).toBe(1);

      // Verify execution is now 'queued' with taskId
      const executionsAfterSecond = await db.select().from(workspaceScheduleExecutions);
      expect(executionsAfterSecond.length).toBe(1);
      expect(executionsAfterSecond[0].taskId).toBeDefined();
      expect(executionsAfterSecond[0].state).toBe("queued");

      // Verify definition nextRunAt was advanced
      const [defAfterSecond] = await db
        .select()
        .from(workspaceScheduleDefinitions)
        .where(eq(workspaceScheduleDefinitions.id, def.id));
      expect(defAfterSecond.nextRunAt?.getTime()).not.toBe(pastDue.getTime());
    } finally {
      spy.mockRestore();
    }
  });

  it("terminates into enqueue_failed after MAX_ENQUEUE_RETRIES consecutive enqueue failures (no infinite retry, no duplicate occurrence)", async () => {
    const pastDue = new Date(Date.now() - 5000);
    const def = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_1",
      createdBy: "user_alice",
      scheduleKind: "daily",
      timezone: "Asia/Ho_Chi_Minh",
      hour: 9,
      minute: 0,
      promptTemplate: "Always-fails scan",
    });

    await db
      .update(workspaceScheduleDefinitions)
      .set({ nextRunAt: pastDue })
      .where(eq(workspaceScheduleDefinitions.id, def.id));

    const spy = vi
      .spyOn(schedulerSvc, "scheduleTask")
      .mockRejectedValue(new Error("Simulated permanent enqueue failure"));

    try {
      // Force every retry attempt to be immediately due regardless of backoff,
      // so the test doesn't need to sleep through exponential backoff windows.
      for (let i = 0; i < scheduleSvc.MAX_ENQUEUE_RETRIES; i++) {
        await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
        await db
          .update(workspaceScheduleExecutions)
          .set({ nextAttemptAt: new Date(Date.now() - 1000) })
          .where(eq(workspaceScheduleExecutions.definitionId, def.id));
      }

      const executions = await db
        .select()
        .from(workspaceScheduleExecutions)
        .where(eq(workspaceScheduleExecutions.definitionId, def.id));

      // Exactly one occurrence for this (definitionId, scheduledFor) — retries
      // must never create a duplicate occurrence.
      expect(executions.length).toBe(1);
      expect(executions[0].taskId).toBeNull();
      expect(executions[0].state).toBe("enqueue_failed");
      expect(executions[0].attemptCount).toBe(scheduleSvc.MAX_ENQUEUE_RETRIES);
      expect(executions[0].error).toBeTruthy();

      // Definition must never have advanced past this occurrence — a task
      // was never successfully dispatched for it.
      const [defAfter] = await db
        .select()
        .from(workspaceScheduleDefinitions)
        .where(eq(workspaceScheduleDefinitions.id, def.id));
      expect(defAfter.nextRunAt?.getTime()).toBe(pastDue.getTime());

      // One more tick must be a no-op: terminal rows are not retried further,
      // and no duplicate occurrence gets created for the same slot.
      const noopDispatch = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
      expect(noopDispatch).toBe(0);
      const executionsAfterNoop = await db
        .select()
        .from(workspaceScheduleExecutions)
        .where(eq(workspaceScheduleExecutions.definitionId, def.id));
      expect(executionsAfterNoop.length).toBe(1);
      expect(executionsAfterNoop[0].state).toBe("enqueue_failed");
    } finally {
      spy.mockRestore();
    }
  });

  it("allows runScheduleNow to trigger immediate execution", async () => {
    const def = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_1",
      createdBy: "user_alice",
      scheduleKind: "daily",
      hour: 18,
      minute: 0,
      promptTemplate: "Evening report",
    });

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: def.id,
      workspaceId: "ws_1",
      principalId: "user_alice",
    });

    expect(execution.id).toBeDefined();
    expect(execution.state).toBe("queued");

    // Complete execution
    const completed = await scheduleSvc.completeScheduleExecution({
      executionId: execution.id,
      state: "succeeded",
      conversationId: "conv_sched_1",
      runId: "run_sched_1",
    });
    expect(completed?.state).toBe("succeeded");
    expect(completed?.conversationId).toBe("conv_sched_1");
  });
});
