import { describe, it, expect } from "vitest";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import {
  putProjectOperatingSetupEndpoint,
  activateProjectOperatingSetupEndpoint,
  getProjectOperatingSetupEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";
import { updateTaskStatus, updateTaskSchedule } from "../handlers/task.handler";
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

  it("sets weekly_plans.startDate/endDate from the resolved round start on activate", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Week-1 plan dates project",
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
      firstWeekActions: [{ title: "List prospects" }],
    });

    expect(result.setup.roundStartDate).not.toBeNull();

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));

    expect(plan!.startDate).not.toBeNull();
    expect(plan!.endDate).not.toBeNull();
    expect(plan!.startDate!.getTime()).toBe(new Date(result.setup.roundStartDate!).getTime());
    expect(plan!.endDate!.getTime()).toBe(plan!.startDate!.getTime() + 7 * 24 * 60 * 60 * 1000);
  });
});

describe("normalizeFirstWeekActions is server-authoritative about client-supplied ids", () => {
  it("ignores a client-supplied id that does not belong to this project's known actions, without 500ing", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Untrusted id project",
    });

    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ id: "not-a-real-id-999999", title: "Injected" }],
    });

    expect(saved.firstWeekActions).toHaveLength(1);
    expect(saved.firstWeekActions[0]!.id).not.toBe("not-a-real-id-999999");

    const [task] = await db
      .select()
      .from(tasks)
      .where(eq(tasks.id, BigInt(saved.firstWeekActions[0]!.id)));
    expect(task).toBeDefined();
    expect(task!.deletedAt).toBeNull();
  });

  it("does not throw a raw SyntaxError on a malformed (non-numeric) client id", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Malformed id project",
    });

    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ id: "abc-not-a-number", title: "Malformed" }],
    });

    expect(saved.firstWeekActions).toHaveLength(1);
    expect(saved.firstWeekActions[0]!.id).not.toBe("abc-not-a-number");
    expect(() => BigInt(saved.firstWeekActions[0]!.id)).not.toThrow();
  });
});

describe("kickoff materialize round-trips ids without churn end-to-end", () => {
  it("round-trips ids across draft → add → remove → activate without churning tasks", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "End-to-end round-trip project",
    });

    // 1. First draft: 1 action
    const first = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Outcome v1",
      firstWeekActions: [{ title: "Action A" }],
    });
    const actionAId = first.firstWeekActions[0]!.id;

    // 2. Second draft: echo action A's real id (as the frontend now correctly does), add action B
    const second = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      firstWeekActions: [
        { id: actionAId, title: "Action A" },
        { title: "Action B" },
      ],
    });
    const actionBId = second.firstWeekActions.find((a) => a.title === "Action B")!.id;

    // Task A must NOT have been re-created (still the same id, still alive)
    const [taskAAfterSecond] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionAId)));
    expect(taskAAfterSecond!.deletedAt).toBeNull();

    // 3. Third draft: remove action A, keep only B
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      firstWeekActions: [{ id: actionBId, title: "Action B" }],
    });

    const [taskAAfterRemove] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionAId)));
    expect(taskAAfterRemove!.deletedAt).not.toBeNull();

    // 4. Activate with only B remaining — must not re-churn B's task
    const activated = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Cust",
      problemStatement: "Prob",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Outcome v2",
      firstWeekActions: [{ id: actionBId, title: "Action B" }],
    });

    expect(activated.setup.firstWeekActions).toHaveLength(1);
    expect(activated.setup.firstWeekActions[0]!.id).toBe(actionBId);

    const [taskBFinal] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionBId)));
    expect(taskBFinal!.deletedAt).toBeNull();

    // Exactly 1 cycle and 1 plan for this project — no duplicates from any of the 4 calls
    const cycles = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycles).toHaveLength(1);
    const plans = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycles[0]!.id));
    expect(plans).toHaveLength(1);
    expect(plans[0]!.focus).toBe("Outcome v2");
  });
});

describe("firstWeekActions view includes live task status/schedule fields", () => {
  it("returns status/plannedStartAt/updatedAt per action, and reflects later updates", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "First week action view project",
    });

    const activated = await activateProjectOperatingSetupEndpoint({
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
      firstWeekActions: [{ title: "List prospects" }],
    });

    const action = activated.setup.firstWeekActions[0]!;
    expect(action.status).toBe("todo");
    expect(action.plannedStartAt).toBeNull();
    expect(action.updatedAt).not.toBeNull();

    await updateTaskStatus({
      id: action.id,
      status: "done",
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    await updateTaskSchedule({
      id: action.id,
      plannedStartAt: "2026-09-08T09:00:00.000Z",
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });

    const refreshed = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    const refreshedAction = refreshed.firstWeekActions[0]!;
    expect(refreshedAction.status).toBe("done");
    expect(refreshedAction.plannedStartAt).toBe("2026-09-08T09:00:00.000Z");
  });
});
