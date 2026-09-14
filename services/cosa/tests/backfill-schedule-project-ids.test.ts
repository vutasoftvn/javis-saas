import { describe, it, expect, vi, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import { backfillLegacyScheduleProjectIds } from "../scripts/backfill-schedule-project-ids";

describe("backfillLegacyScheduleProjectIds", () => {
  it("assigns the first project and marks legacy-unscoped when a project exists", async () => {
    const id = `sched_def_backfill_${Date.now()}`;
    const workspaceId = "ws_backfill_1";
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId,
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [{ id: "proj_first" }] }),
    });
    global.fetch = fetchMock as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company", "test-token");

    // Assert fetch was called with correct headers
    expect(fetchMock).toHaveBeenCalledWith(
      "http://fake-company/operations/projects",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "X-Workspace-Id": workspaceId,
          "Authorization": "Bearer test-token",
          "Content-Type": "application/json",
        }),
      })
    );

    expect(result.updated).toBeGreaterThanOrEqual(1);
    expect(result.skippedDueToFetchError).toBe(0);
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.projectId).toBe("proj_first");
    expect(row.isLegacyUnscoped).toBe(true);
    expect(row.state).toBe("enabled");
  });

  it("pauses the schedule when the workspace has no project", async () => {
    const id = `sched_def_backfill_none_${Date.now()}`;
    const workspaceId = "ws_backfill_none";
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId,
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: "enabled",
    });

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [] }),
    });
    global.fetch = fetchMock as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company", "test-token");

    // Assert fetch was called with correct headers
    expect(fetchMock).toHaveBeenCalledWith(
      "http://fake-company/operations/projects",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "X-Workspace-Id": workspaceId,
          "Authorization": "Bearer test-token",
        }),
      })
    );

    expect(result.disabled).toBeGreaterThanOrEqual(1);
    expect(result.skippedDueToFetchError).toBe(0);
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.state).toBe("paused");
    expect(row.projectId).toBeNull();
  });

  it("skips schedule when fetch returns non-2xx status, does not pause it", async () => {
    const id = `sched_def_backfill_error_${Date.now()}`;
    const workspaceId = "ws_backfill_error";
    const originalState = "enabled";
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId,
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: originalState,
    });

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
    });
    global.fetch = fetchMock as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company", "test-token");

    expect(result.skippedDueToFetchError).toBeGreaterThanOrEqual(1);
    expect(result.updated).toBe(0);
    expect(result.disabled).toBe(0);

    // Verify schedule was NOT modified
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.state).toBe(originalState);
    expect(row.projectId).toBeNull();
  });

  it("skips schedule when fetch throws, does not pause it", async () => {
    const id = `sched_def_backfill_throw_${Date.now()}`;
    const workspaceId = "ws_backfill_throw";
    const originalState = "enabled";
    await db.insert(schema.workspaceScheduleDefinitions).values({
      id,
      workspaceId,
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "test",
      state: originalState,
    });

    const fetchMock = vi.fn().mockRejectedValue(new Error("Network error"));
    global.fetch = fetchMock as any;

    const result = await backfillLegacyScheduleProjectIds("http://fake-company", "test-token");

    expect(result.skippedDueToFetchError).toBeGreaterThanOrEqual(1);
    expect(result.updated).toBe(0);
    expect(result.disabled).toBe(0);

    // Verify schedule was NOT modified
    const [row] = await db
      .select()
      .from(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
    expect(row.state).toBe(originalState);
    expect(row.projectId).toBeNull();
  });
});
