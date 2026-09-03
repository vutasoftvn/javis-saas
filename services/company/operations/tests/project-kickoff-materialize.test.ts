import { describe, it, expect, afterEach } from "vitest";
import { and, eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { materializeFirstWeekPlan } from "../strategy/services/project-kickoff-materialize.service";
import { makeTenantContext } from "./tenant-context.fixture";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks, taskProjects } = schema;

// Id do từng test tự sinh trong lượt chạy đó — tránh xoá theo id cứng không
// giới hạn workspaceId (nguy hiểm trên DB dev dùng chung nếu id trùng dữ liệu thật).
let generatedTaskIds: bigint[] = [];

function mintId(): string {
  const id = generateSnowflake();
  generatedTaskIds.push(id);
  return id.toString();
}

afterEach(async () => {
  if (generatedTaskIds.length > 0) {
    await db.delete(tasks).where(inArray(tasks.id, generatedTaskIds));
  }
  generatedTaskIds = [];
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

    const id1 = mintId();
    const id2 = mintId();
    const actions = [
      { id: id1, title: "Interview lead #1" },
      { id: id2, title: "Interview lead #2" },
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

    const taskRows = await db.select().from(tasks).where(eq(tasks.id, BigInt(id1)));
    expect(taskRows).toHaveLength(1);
    expect(taskRows[0]!.title).toBe("Interview lead #1");
    expect(taskRows[0]!.weeklyCommitmentId).not.toBeNull();

    const links = await db.select().from(taskProjects).where(
      and(eq(taskProjects.taskId, BigInt(id1)), eq(taskProjects.projectId, BigInt(project.id)))
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

    const idA = mintId();
    const idB = mintId();
    const idC = mintId();
    const firstTwo = [
      { id: idA, title: "Action A" },
      { id: idB, title: "Action B" },
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

    const allThree = [...firstTwo, { id: idC, title: "Action C" }];

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

    const thirdTask = await db.select().from(tasks).where(eq(tasks.id, BigInt(idC)));
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

    const idKeepA = mintId();
    const idRemove = mintId();
    const idKeepC = mintId();
    const threeActions = [
      { id: idKeepA, title: "Keep A" },
      { id: idRemove, title: "Remove me" },
      { id: idKeepC, title: "Keep C" },
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

    const twoActions = threeActions.filter((a) => a.id !== idRemove);

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

    const [removedTask] = await db.select().from(tasks).where(eq(tasks.id, BigInt(idRemove)));
    expect(removedTask!.deletedAt).not.toBeNull();
    expect(removedTask!.status).toBe("cancelled");

    const [removedCommitment] = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, removedTask!.weeklyCommitmentId!));
    expect(removedCommitment!.deletedAt).not.toBeNull();

    const [keptTask] = await db.select().from(tasks).where(eq(tasks.id, BigInt(idKeepA)));
    expect(keptTask!.deletedAt).toBeNull();
  });
});
