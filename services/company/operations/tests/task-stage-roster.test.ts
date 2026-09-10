// services/company/operations/tests/task-stage-roster.test.ts
//
// listStageRosterService: roster của 1 stage tăng trưởng — chỉ trả task
// thuộc project đang chọn đúng stage đó trong workspace.
import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { createTaskService, listStageRosterService } from "../services/task.service";
import { createTestWorkspaceWithMember } from "./_helpers";

describe("listStageRosterService", () => {
  it("returns tasks only for projects whose selected_stage matches", async () => {
    // Startup Core: helper seed sẵn một project (id === workspaceId); dùng đúng
    // project đó cho cả operating-setup lẫn task (task gắn project qua cột trực
    // tiếp `tasks.project_id`).
    const ws = await createTestWorkspaceWithMember();

    await db.insert(schema.projectOperatingSetups).values({
      projectId: BigInt(ws.projectId),
      workspaceId: BigInt(ws.workspaceId),
      status: "IN_PROGRESS",
      selectedStage: "P0_DISCOVERY",
    });

    const task = await createTaskService(
      { title: "Ship pricing page", workspaceId: ws.workspaceId, priority: "high", projectId: ws.projectId },
      ws.bearerToken
    );

    const roster = await listStageRosterService(ws.workspaceId, "P0_DISCOVERY");

    expect(roster.stage.stageCode).toBe("P0_DISCOVERY");
    expect(roster.roster.some((r) => r.taskId === task.id)).toBe(true);
    expect(roster.summary.total).toBe(roster.roster.length);
    expect(roster.summary.highPriority).toBe(1);
    expect(roster.summary.locked).toBe(0);
  });

  it("returns empty roster for a stage with no matching projects", async () => {
    const ws = await createTestWorkspaceWithMember();
    const roster = await listStageRosterService(ws.workspaceId, "P1_PROBLEM_VALIDATION");
    expect(roster.roster).toEqual([]);
    expect(roster.summary.total).toBe(0);
  });
});
