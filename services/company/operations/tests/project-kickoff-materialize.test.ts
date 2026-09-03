import { describe, it, expect, beforeAll, afterEach } from "vitest";
import { and, eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { materializeFirstWeekPlan } from "../strategy/services/project-kickoff-materialize.service";
import { makeTenantContext } from "./tenant-context.fixture";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks, taskProjects } = schema;

const testTaskIds = [
  BigInt("1001"), BigInt("1002"),
  BigInt("2001"), BigInt("2002"), BigInt("2003"),
  BigInt("3001"), BigInt("3002"), BigInt("3003"),
];

// Clean up test tasks before and after tests to avoid primary key conflicts
beforeAll(async () => {
  await db.delete(tasks).where(inArray(tasks.id, testTaskIds));
});

afterEach(async () => {
  await db.delete(tasks).where(inArray(tasks.id, testTaskIds));
});

describe("materializeFirstWeekPlan", () => {
  it("creates a cycle, week-1 plan, commitments and tasks for new actions", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Materialize test project",
    });
    const ctx = makeTenantContext({ workspaceId: ws.workspaceId, userId: ws.userId }, { membershipRole: "admin" });

    const actions = [
      { id: "1001", title: "Interview lead #1" },
      { id: "1002", title: "Interview lead #2" },
    ];

    await db.transaction(async (tx) => {
      await materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: [],
        actions,
        firstWeekOutcome: "Talk to 2 leads",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      });
    });

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycle).toBeDefined();
    expect(cycle!.durationWeeks).toBe(2);

    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));
    expect(plan).toBeDefined();
    expect(plan!.weekNo).toBe(1);
    expect(plan!.focus).toBe("Talk to 2 leads");

    const commitments = await db.select().from(weeklyCommitments).where(eq(weeklyCommitments.weeklyPlanId, plan!.id));
    expect(commitments).toHaveLength(2);
    expect(commitments.every((c) => c.initiativeId === null)).toBe(true);

    const taskRows = await db.select().from(tasks).where(eq(tasks.id, BigInt("1001")));
    expect(taskRows).toHaveLength(1);
    expect(taskRows[0]!.title).toBe("Interview lead #1");
    expect(taskRows[0]!.weeklyCommitmentId).not.toBeNull();

    const links = await db.select().from(taskProjects).where(
      and(eq(taskProjects.taskId, BigInt("1001")), eq(taskProjects.projectId, BigInt(project.id)))
    );
    expect(links).toHaveLength(1);
  });

  it("reuses the existing cycle/plan when a 3rd action is added later", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Reuse cycle test",
    });
    const ctx = makeTenantContext({ workspaceId: ws.workspaceId, userId: ws.userId }, { membershipRole: "admin" });

    const firstTwo = [
      { id: "2001", title: "Action A" },
      { id: "2002", title: "Action B" },
    ];

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: [],
        actions: firstTwo,
        firstWeekOutcome: "Outcome v1",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const allThree = [...firstTwo, { id: "2003", title: "Action C" }];

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: firstTwo,
        actions: allThree,
        firstWeekOutcome: "Outcome v2",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const cycles = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycles).toHaveLength(1);

    const plans = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycles[0]!.id));
    expect(plans).toHaveLength(1);
    expect(plans[0]!.focus).toBe("Outcome v2");

    const commitments = await db.select().from(weeklyCommitments).where(eq(weeklyCommitments.weeklyPlanId, plans[0]!.id));
    expect(commitments).toHaveLength(3);

    const thirdTask = await db.select().from(tasks).where(eq(tasks.id, BigInt("2003")));
    expect(thirdTask).toHaveLength(1);
  });

  it("soft-deletes the task and commitment when an action is removed", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Remove action test",
    });
    const ctx = makeTenantContext({ workspaceId: ws.workspaceId, userId: ws.userId }, { membershipRole: "admin" });

    const threeActions = [
      { id: "3001", title: "Keep A" },
      { id: "3002", title: "Remove me" },
      { id: "3003", title: "Keep C" },
    ];

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: [],
        actions: threeActions,
        firstWeekOutcome: "Outcome",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const twoActions = threeActions.filter((a) => a.id !== "3002");

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: threeActions,
        actions: twoActions,
        firstWeekOutcome: "Outcome",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const [removedTask] = await db.select().from(tasks).where(eq(tasks.id, BigInt("3002")));
    expect(removedTask!.deletedAt).not.toBeNull();
    expect(removedTask!.status).toBe("cancelled");

    const [removedCommitment] = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, removedTask!.weeklyCommitmentId!));
    expect(removedCommitment!.deletedAt).not.toBeNull();

    const [keptTask] = await db.select().from(tasks).where(eq(tasks.id, BigInt("3001")));
    expect(keptTask!.deletedAt).toBeNull();
  });
});
