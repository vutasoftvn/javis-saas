import { describe, it, expect } from "vitest";
import { createWorkspaceSchedule } from "../services/workspace-schedule.service";
import { APIError } from "encore.dev/api";

describe("createWorkspaceSchedule — project scope", () => {
  it("rejects when projectId is missing", async () => {
    await expect(
      createWorkspaceSchedule({
        workspaceId: "ws_proj_test",
        createdBy: "user_1",
        scheduleKind: "daily",
        promptTemplate: "daily report",
        // projectId intentionally omitted
      } as any)
    ).rejects.toThrow(APIError);
  });

  it("stores projectId on the created definition", async () => {
    const def = await createWorkspaceSchedule({
      workspaceId: "ws_proj_test_2",
      createdBy: "user_1",
      scheduleKind: "daily",
      promptTemplate: "daily report",
      projectId: "proj_abc",
    });
    expect(def.projectId).toBe("proj_abc");
    expect(def.isLegacyUnscoped).toBe(false);
  });
});
