import { describe, it, expect } from "vitest";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import {
  putProjectOperatingSetupEndpoint,
  activateProjectOperatingSetupEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks, taskProjects } = schema;

describe("saveProjectOperatingSetup materializes first-week actions immediately", () => {
  it("creates a real task the moment an action is saved via draft, before activate", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Draft materialize project",
    });

    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Interview 3 controllers",
      firstWeekActions: [{ title: "Prepare interview script" }],
    });

    expect(saved.status).toBe("IN_PROGRESS");
    expect(saved.firstWeekActions).toHaveLength(1);
    const actionId = saved.firstWeekActions[0]!.id;

    const [task] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionId)));
    expect(task).toBeDefined();
    expect(task!.title).toBe("Prepare interview script");
    expect(task!.deletedAt).toBeNull();

    const [link] = await db
      .select()
      .from(taskProjects)
      .where(and(eq(taskProjects.taskId, BigInt(actionId)), eq(taskProjects.projectId, BigInt(project.id))));
    expect(link).toBeDefined();

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycle).toBeDefined();

    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));
    expect(plan!.focus).toBe("Interview 3 controllers");
  });

  it("removes the task when the action is dropped from a later draft save", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Draft remove project",
    });

    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ title: "Action to remove" }],
    });
    const actionId = saved.firstWeekActions[0]!.id;

    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      firstWeekActions: [],
    });

    const [task] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionId)));
    expect(task!.deletedAt).not.toBeNull();
  });

  it("activate() also materializes even if the founder never saved a draft first", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Activate-only materialize project",
    });

    const result = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Finance leads",
      problemStatement: "Slow close",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 3 leads",
      firstWeekActions: [{ title: "List prospects" }, { title: "Book calls" }],
    });

    expect(result.setup.firstWeekActions).toHaveLength(2);

    for (const action of result.setup.firstWeekActions) {
      const [task] = await db.select().from(tasks).where(eq(tasks.id, BigInt(action.id)));
      expect(task).toBeDefined();
      expect(task!.deletedAt).toBeNull();
    }

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));
    const liveCommitments = await db
      .select()
      .from(weeklyCommitments)
      .where(and(eq(weeklyCommitments.weeklyPlanId, plan!.id), isNull(weeklyCommitments.deletedAt)));
    expect(liveCommitments).toHaveLength(2);
  });
});
