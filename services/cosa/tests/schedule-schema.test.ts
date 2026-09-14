import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

describe("workspace_schedule_definitions.project_id", () => {
  it("stores and reads back project_id and is_legacy_unscoped", async () => {
    const id = `sched_def_test_${Date.now()}`;
    const [row] = await db
      .insert(schema.workspaceScheduleDefinitions)
      .values({
        id,
        workspaceId: "ws_schema_test",
        createdBy: "test_user",
        scheduleKind: "daily",
        promptTemplate: "test prompt",
        projectId: "proj_schema_test",
        isLegacyUnscoped: false,
        state: "enabled",
      })
      .returning();

    expect(row.projectId).toBe("proj_schema_test");
    expect(row.isLegacyUnscoped).toBe(false);

    await db
      .delete(schema.workspaceScheduleDefinitions)
      .where(eq(schema.workspaceScheduleDefinitions.id, id));
  });
});
