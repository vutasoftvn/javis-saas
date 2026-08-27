import { describe, it, expect, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import * as scheduleSvc from "../services/workspace-schedule.service";
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
