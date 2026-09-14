import { describe, it, expect, vi, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import { backfillLegacyScheduleProjectIds } from "../scripts/backfill-schedule-project-ids";

describe("backfillLegacyScheduleProjectIds", () => {
  it("assigns the first project and marks legacy-unscoped when a project exists", async () => {
    const id = `sched_def_backfill_${Date.now()}`;
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId: "ws_backfill_1",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [{ id: "proj_first" }] }),
    }) as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company");

    expect(result.updated).toBeGreaterThanOrEqual(1);
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.projectId).toBe("proj_first");
    expect(row.isLegacyUnscoped).toBe(true);
    expect(row.state).toBe("enabled");
  });

  it("disables the schedule when the workspace has no project", async () => {
    const id = `sched_def_backfill_none_${Date.now()}`;
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId: "ws_backfill_none",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [] }),
    }) as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company");

    expect(result.disabled).toBeGreaterThanOrEqual(1);
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.state).toBe("paused");
    expect(row.projectId).toBeNull();
  });
});
