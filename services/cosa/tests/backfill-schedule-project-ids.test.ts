import { describe, it, expect, vi, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import { backfillLegacyScheduleProjectIds } from "../scripts/backfill-schedule-project-ids";
import * as scheduleSvc from "../services/workspace-schedule.service";
import * as schedulerSvc from "../services/control-plane-scheduler.service";

describe("backfillLegacyScheduleProjectIds", () => {
  beforeEach(async () => {
    await db.delete(schema.workspaceScheduleExecutions);
    await db.delete(schema.workspaceScheduleDefinitions);
    await db.delete(schema.scheduledTasks);
    vi.restoreAllMocks();
  });

  it("pauses an unscoped legacy schedule without calling Company project list", async () => {
    const id = `sched_def_backfill_${Date.now()}`;
    const organizationId = "ws_backfill_1";
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      organizationId,
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    const fetchMock = vi.fn();
    global.fetch = fetchMock as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company", "test-token");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.pausedDefinitionIds).toEqual([id]);

    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.projectId).toBeNull();
    expect(row.state).toBe("paused");
    expect(row.isLegacyUnscoped).toBe(true);
  });

  it("does not dispatch a paused or legacy-unscoped definition", async () => {
    const id = `sched_def_unscoped_${Date.now()}`;
    const pastDue = new Date(Date.now() - 5000);
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      organizationId: "ws_backfill_unscoped",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "paused",
      isLegacyUnscoped: true,
      nextRunAt: pastDue,
      projectId: null,
    });

    const scheduleTaskSpy = vi.spyOn(schedulerSvc, "scheduleTask");
    const dispatched = await scheduleSvc.dispatchDueWorkspaceSchedules(new Date());
    expect(dispatched).toBe(0);
    expect(scheduleTaskSpy).not.toHaveBeenCalled();
  });
});

