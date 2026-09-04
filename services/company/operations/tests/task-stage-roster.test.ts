// services/company/operations/tests/task-stage-roster.test.ts
//
// listStageRosterService: roster của 1 stage tăng trưởng — chỉ trả task
// thuộc project đang chọn đúng stage đó trong workspace.
import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import { createTaskService, listStageRosterService } from "../services/task.service";
import { createTestWorkspaceWithMember } from "./_helpers";

describe("listStageRosterService", () => {
  it("returns tasks only for projects whose selected_stage matches", async () => {
    // Seed workspace/project bằng đúng helper các test operations khác trong
    // thư mục này dùng (xem agent-claimable.test.ts, project-operating-setup.test.ts) —
    // các cột workspaceId/projectId là bigint nên phải là snowflake id thật,
    // không phải chuỗi tay như "test-ws-...".
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Stage roster project",
    });

    await db.insert(schema.projectOperatingSetups).values({
      projectId: BigInt(project.id),
      workspaceId: BigInt(ws.workspaceId),
      status: "IN_PROGRESS",
      selectedStage: "P0_DISCOVERY",
    });

    const task = await createTaskService(
      { title: "Ship pricing page", workspaceId: ws.workspaceId, priority: "high" },
      ws.bearerToken
    );
    await db.insert(schema.taskProjects).values({
      workspaceId: BigInt(ws.workspaceId),
      taskId: BigInt(task.id),
      projectId: BigInt(project.id),
    });

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
