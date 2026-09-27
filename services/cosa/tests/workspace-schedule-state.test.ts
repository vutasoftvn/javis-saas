import { describe, it, expect, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import * as scheduleSvc from "../services/workspace-schedule.service";
import { db, schema } from "../models/db";

const { workspaceScheduleDefinitions, workspaceScheduleExecutions, scheduledTasks } = schema;

// Hub đợt 1 (spec 2026-09-27-hub-operations-workspace-design §3): founder tạm dừng /
// tiếp tục / lưu trữ lịch và xem các lần chạy gần nhất.

beforeEach(async () => {
  await db.delete(workspaceScheduleExecutions);
  await db.delete(workspaceScheduleDefinitions);
  await db.delete(scheduledTasks);
});

async function createDaily(organizationId = "ws_state") {
  return scheduleSvc.createWorkspaceSchedule({
    organizationId,
    createdBy: "user_alice",
    scheduleKind: "daily",
    hour: 8,
    minute: 0,
    promptTemplate: "Morning digest",
    projectId: "proj_state",
  });
}

describe("setWorkspaceScheduleState", () => {
  it("pauses, then resumes with a recomputed next run", async () => {
    const def = await createDaily();

    const paused = await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: def.id,
      organizationId: "ws_state",
      state: "paused",
    });
    expect(paused.state).toBe("paused");

    const now = new Date();
    const resumed = await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: def.id,
      organizationId: "ws_state",
      state: "enabled",
      now,
    });
    expect(resumed.state).toBe("enabled");
    expect(resumed.nextRunAt).not.toBeNull();
    expect(resumed.nextRunAt!.getTime()).toBeGreaterThan(now.getTime());
  });

  it("is idempotent when the state does not change", async () => {
    const def = await createDaily();
    const same = await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: def.id,
      organizationId: "ws_state",
      state: "enabled",
    });
    expect(same.state).toBe("enabled");
    expect(same.updatedAt.getTime()).toBe(def.updatedAt.getTime());
  });

  it("archives without deleting, clears next run and never reopens", async () => {
    const def = await createDaily();
    const archived = await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: def.id,
      organizationId: "ws_state",
      state: "archived",
    });
    expect(archived.state).toBe("archived");
    expect(archived.nextRunAt).toBeNull();

    for (const state of ["enabled", "paused"] as const) {
      await expect(
        scheduleSvc.setWorkspaceScheduleState({ scheduleId: def.id, organizationId: "ws_state", state })
      ).rejects.toMatchObject({ code: "failed_precondition" });
    }
    const rows = await db
      .select()
      .from(workspaceScheduleDefinitions)
      .where(eq(workspaceScheduleDefinitions.id, def.id));
    expect(rows).toHaveLength(1);
  });

  it("rejects unknown states and schedules of another organization", async () => {
    const def = await createDaily();
    await expect(
      scheduleSvc.setWorkspaceScheduleState({
        scheduleId: def.id,
        organizationId: "ws_state",
        state: "deleted" as never,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
    await expect(
      scheduleSvc.setWorkspaceScheduleState({
        scheduleId: def.id,
        organizationId: "ws_other",
        state: "paused",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("refuses to resume a one_time schedule whose time has passed", async () => {
    const def = await scheduleSvc.createWorkspaceSchedule({
      organizationId: "ws_state",
      createdBy: "user_alice",
      scheduleKind: "one_time",
      runAt: new Date(Date.now() + 60_000),
      promptTemplate: "One-off",
      projectId: "proj_state",
    });
    await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: def.id,
      organizationId: "ws_state",
      state: "paused",
    });
    await expect(
      scheduleSvc.setWorkspaceScheduleState({
        scheduleId: def.id,
        organizationId: "ws_state",
        state: "enabled",
        now: new Date(Date.now() + 120_000),
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("dispatcher skips paused and archived schedules", async () => {
    const paused = await createDaily();
    const archived = await createDaily();
    const pastDue = new Date(Date.now() - 5_000);
    await db
      .update(workspaceScheduleDefinitions)
      .set({ nextRunAt: pastDue })
      .where(eq(workspaceScheduleDefinitions.organizationId, "ws_state"));
    await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: paused.id,
      organizationId: "ws_state",
      state: "paused",
    });
    await scheduleSvc.setWorkspaceScheduleState({
      scheduleId: archived.id,
      organizationId: "ws_state",
      state: "archived",
    });

    const dispatched = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
    expect(dispatched).toBe(0);
    const executions = await db.select().from(workspaceScheduleExecutions);
    expect(executions).toHaveLength(0);
  });
});

describe("listWorkspaceScheduleExecutions", () => {
  it("returns latest executions first, bounded and scoped to the organization", async () => {
    const def = await createDaily();
    // Chèn trực tiếp với scheduledFor khác nhau (unique theo definition + scheduledFor).
    const base = Date.now() - 3 * 3_600_000;
    for (let i = 0; i < 3; i++) {
      await db.insert(workspaceScheduleExecutions).values({
        id: `sched_exec_state_${i}`,
        definitionId: def.id,
        organizationId: "ws_state",
        scheduledFor: new Date(base + i * 3_600_000),
        promptTemplateSnapshot: def.promptTemplate,
        agentProfileSnapshot: def.agentProfile,
        connectorGrantIdsSnapshot: [],
        projectIdSnapshot: def.projectId,
        state: "queued",
      });
    }
    const latest = { id: "sched_exec_state_2" };
    await scheduleSvc.completeScheduleExecution({
      executionId: latest.id,
      state: "failed",
      error: "x".repeat(500),
    });

    const items = await scheduleSvc.listWorkspaceScheduleExecutions({
      scheduleId: def.id,
      organizationId: "ws_state",
      limit: 2,
    });
    expect(items.map((item) => item.id)).toEqual(["sched_exec_state_2", "sched_exec_state_1"]);

    const all = await scheduleSvc.listWorkspaceScheduleExecutions({
      scheduleId: def.id,
      organizationId: "ws_state",
      limit: 100,
    });
    expect(all).toHaveLength(3);
    const failed = all.find((item) => item.id === latest.id)!;
    expect(failed.error).toHaveLength(200);

    await expect(
      scheduleSvc.listWorkspaceScheduleExecutions({ scheduleId: def.id, organizationId: "ws_other" })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
