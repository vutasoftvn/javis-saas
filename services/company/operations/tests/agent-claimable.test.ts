import { describe, it, expect } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";
import {
  createExecutionPlanService,
  acceptExecutionPlanService,
  CreatePlanItemInput,
} from "../services/execution-plan.service";
import {
  listAgentClaimableTasksService,
  advanceTaskByAgentService,
  getWorkspaceExecutionSettingsService,
  setWorkspaceExecutionSettingsService,
} from "../services/task.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { tasks } = schema;

function ctxFor(workspaceId: string): TenantContext {
  return Object.freeze({
    workspaceId, userId: "1", workforceMemberId: undefined,
    membershipRole: "founder", permissions: [], correlationId: "t", platformUserId: null,
  }) as unknown as TenantContext;
}

async function seedAcceptedPlan(items: CreatePlanItemInput[]) {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const project = await createProject({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, title: "claimable project",
  });
  const founderId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: founderId, workspaceId: BigInt(ws.workspaceId), memberType: "HUMAN",
    humanUserId: BigInt(ws.userId), roleTitle: "Founder", status: "active",
  });
  const goal = await setWeeklyGoalService(
    { projectId: project.id, workspaceId: ws.workspaceId, focus: "Goal", triggerDecomposition: false, origin: "command_center" },
    ws.bearerToken
  );
  const plan = await createExecutionPlanService(
    {
      workspaceId: ws.workspaceId, projectId: project.id, weeklyPlanId: goal.weeklyPlanId,
      goalText: "Goal", origin: "command_center", originRef: null, runId: null, items,
    },
    ws.bearerToken
  );
  const res = await acceptExecutionPlanService(
    plan.id, { workspaceId: ws.workspaceId, acceptedByMemberId: founderId.toString() }, ws.bearerToken
  );
  return { workspaceId: ws.workspaceId, auth: ws.bearerToken, plan, res, projectId: String(project.id) };
}

function autoItem(title: string, over: Partial<CreatePlanItemInput> = {}): CreatePlanItemInput {
  return {
    title, decisionReason: "lý do đủ dài cho item",
    evidenceRefs: ["e1"], suggestedDomain: "operations",
    expectedCapability: "operations.sop.draft", capabilityRisk: "LOW",
    tenantPolicyDecision: "ALLOW", dependsOnTitles: [], ...over,
  };
}

describe("listAgentClaimableTasksService", () => {
  it("returns AUTO todo tasks assigned to AI members", async () => {
    const s = await seedAcceptedPlan([autoItem("A"), autoItem("B")]);
    const claimable = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(claimable.length).toBe(2);
    expect(claimable.every((t) => t.autonomyClass === "AUTO")).toBe(true);
    expect(claimable.every((t) => t.ownerAgentProfile === "operations")).toBe(true);
    expect(claimable[0]!.planItemId).toBeTruthy();
    expect(claimable.every((t) => t.projectId === s.projectId)).toBe(true);
    expect(claimable.every((t) => t.planOrigin === "command_center" && t.planOriginRef === null)).toBe(true);
  });

  it("filters by projectId so a sweep never crosses Projects", async () => {
    const s = await seedAcceptedPlan([autoItem("A")]);
    const own = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth, undefined, s.projectId);
    expect(own.map((t) => t.title)).toEqual(["A"]);
    const other = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth, undefined, "999999999");
    expect(other).toEqual([]);
  });

  it("excludes FOUNDER_ONLY tasks", async () => {
    const s = await seedAcceptedPlan([
      autoItem("auto one"),
      autoItem("manual one", { expectedCapability: null }),
    ]);
    const claimable = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(claimable.length).toBe(1);
    expect(claimable[0]!.title).toBe("auto one");
  });

  it("excludes a task whose dependency is not done, includes it once the dep completes", async () => {
    const s = await seedAcceptedPlan([autoItem("first"), autoItem("second", { dependsOnTitles: ["first"] })]);
    let claimable = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(claimable.map((t) => t.title).sort()).toEqual(["first"]);

    // complete "first"
    const firstTaskId = claimable[0]!.taskId;
    await advanceTaskByAgentService({ taskId: firstTaskId, toStatus: "in_progress", runId: "r" }, ctxFor(s.workspaceId));
    await advanceTaskByAgentService({ taskId: firstTaskId, toStatus: "done", runId: "r", evidenceRefs: ["artifact:a1"] }, ctxFor(s.workspaceId));

    claimable = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(claimable.map((t) => t.title)).toEqual(["second"]);
  });

  it("excludes tasks that are no longer 'todo'", async () => {
    const s = await seedAcceptedPlan([autoItem("solo")]);
    const claimable1 = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    const taskId = claimable1[0]!.taskId;
    await advanceTaskByAgentService({ taskId, toStatus: "in_progress", runId: "r" }, ctxFor(s.workspaceId));
    const claimable2 = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(claimable2.length).toBe(0);
  });

  it("returns nothing when the workspace kill-switch (sweepEnabled=false) is set", async () => {
    const s = await seedAcceptedPlan([autoItem("a"), autoItem("b")]);
    expect((await listAgentClaimableTasksService(s.workspaceId, 10, s.auth)).length).toBe(2);

    await setWorkspaceExecutionSettingsService(s.workspaceId, false, ctxFor(s.workspaceId));
    expect((await listAgentClaimableTasksService(s.workspaceId, 10, s.auth)).length).toBe(0);

    const back = await setWorkspaceExecutionSettingsService(s.workspaceId, true, ctxFor(s.workspaceId));
    expect(back.sweepEnabled).toBe(true);
    expect((await listAgentClaimableTasksService(s.workspaceId, 10, s.auth)).length).toBe(2);
  });

  it("getWorkspaceExecutionSettingsService defaults to sweepEnabled=true", async () => {
    const s = await seedAcceptedPlan([autoItem("a")]);
    const v = await getWorkspaceExecutionSettingsService(s.workspaceId, s.auth);
    expect(v.sweepEnabled).toBe(true);
  });

  it("rate-limit: stops returning tasks once 24h agent run count hits the cap", async () => {
    const prev = process.env.WGA_MAX_TASK_RUNS_PER_WORKSPACE_PER_DAY;
    process.env.WGA_MAX_TASK_RUNS_PER_WORKSPACE_PER_DAY = "1";
    try {
      const s = await seedAcceptedPlan([autoItem("a"), autoItem("b")]);
      const first = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
      expect(first.length).toBe(2);

      // simulate one completed agent run (advance writes a task_execution_records row)
      await advanceTaskByAgentService(
        { taskId: first[0]!.taskId, toStatus: "in_progress", runId: "wga_task_x_1" },
        ctxFor(s.workspaceId)
      );

      const after = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
      expect(after.length).toBe(0);
    } finally {
      process.env.WGA_MAX_TASK_RUNS_PER_WORKSPACE_PER_DAY = prev;
    }
  });
});

describe("listAgentClaimableTasksService goal ancestry and done criteria", () => {
  const criteria = {
    version: 1,
    criteria: [{ id: "c1", description: "Có tài liệu", check: "rubric", rubric: "Có tài liệu" }],
  };
  const normalized = {
    version: 1,
    criteria: [{ id: "c1", description: "Có tài liệu", required: true, check: "rubric", rubric: "Có tài liệu" }],
  };

  it("returns done criteria of the plan item and the goal ancestry of the task", async () => {
    const s = await seedAcceptedPlan([autoItem("Có tiêu chí", { doneCriteria: criteria })]);
    const { createGoalService } = await import("../services/goals.service");
    const { createObjectiveService } = await import("../services/okr.service");
    const goal = await createGoalService({ workspaceId: s.workspaceId, title: "Mục tiêu năm", goalType: "strategic" });
    const company = await createObjectiveService({
      workspaceId: s.workspaceId, scope: "company", goalId: goal.goalId, title: "Tăng trưởng", authorization: s.auth,
    });
    await db.update(schema.projects).set({ objectiveId: BigInt(company.id) })
      .where(eq(schema.projects.id, BigInt(s.projectId)));

    const [task] = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(task!.doneCriteria).toEqual(normalized);
    expect(task!.goalAncestry.resolvedVia).toBe("project");
    expect(task!.goalAncestry.goalChain[0]?.title).toBe("Mục tiêu năm");
    expect(task!.goalAncestry.companyObjective?.title).toBe("Tăng trưởng");
  });

  it("returns null criteria and an unlinked ancestry when nothing is configured", async () => {
    const s = await seedAcceptedPlan([autoItem("Trống", {})]);
    const [task] = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(task!.doneCriteria).toBeNull();
    expect(task!.goalAncestry.unlinkedReason).toBe("project_not_linked");
  });

  it("maps done criteria per plan item", async () => {
    const s = await seedAcceptedPlan([
      autoItem("Có tiêu chí", { doneCriteria: criteria }),
      autoItem("Không tiêu chí", {}),
    ]);
    const claimable = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect(claimable).toHaveLength(2);
    expect(claimable.find((t) => t.title === "Có tiêu chí")!.doneCriteria).toEqual(normalized);
    expect(claimable.find((t) => t.title === "Không tiêu chí")!.doneCriteria).toBeNull();
  });

  it("resolves ancestry per task using the task's own initiative", async () => {
    const s = await seedAcceptedPlan([autoItem("Có initiative", {}), autoItem("Không initiative", {})]);
    const { createGoalService } = await import("../services/goals.service");
    const { createObjectiveService, addKeyResultService } = await import("../services/okr.service");
    const goal = await createGoalService({ workspaceId: s.workspaceId, title: "Chiến lược", goalType: "strategic" });
    const company = await createObjectiveService({
      workspaceId: s.workspaceId, scope: "company", goalId: goal.goalId, title: "Tăng trưởng", authorization: s.auth,
    });
    const projObj = await createObjectiveService({
      workspaceId: s.workspaceId, projectId: s.projectId, parentObjectiveId: company.id, title: "MRR dự án", authorization: s.auth,
    });
    const kr = await addKeyResultService({
      objectiveId: projObj.id, title: "MRR", targetValue: 100, baselineValue: 10, unit: "triệu", authorization: s.auth,
    });
    const initiativeId = generateSnowflake();
    await db.insert(schema.initiatives).values({
      id: initiativeId, workspaceId: BigInt(s.workspaceId), projectId: BigInt(s.projectId),
      keyResultId: BigInt(kr.id), title: "Chiến dịch",
    });
    await db.update(tasks).set({ initiativeId })
      .where(and(eq(tasks.workspaceId, BigInt(s.workspaceId)), eq(tasks.title, "Có initiative")));

    const claimable = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    const withInit = claimable.find((t) => t.title === "Có initiative")!;
    const without = claimable.find((t) => t.title === "Không initiative")!;
    expect(withInit.goalAncestry.resolvedVia).toBe("initiative");
    expect(withInit.goalAncestry.keyResult).toMatchObject({ id: kr.id });
    expect(without.goalAncestry.resolvedVia).not.toBe("initiative");
    expect(without.goalAncestry.keyResult).toBeNull();
  });

  it("keeps row order across ancestry batches (more than 8 tasks)", async () => {
    const titles = Array.from({ length: 10 }, (_, i) => `T${i}`);
    const s = await seedAcceptedPlan(titles.map((t) => autoItem(t)));
    const claimable = await listAgentClaimableTasksService(s.workspaceId, 20, s.auth);
    expect(claimable).toHaveLength(10);
    expect(claimable.map((t) => t.title)).toEqual(titles); // sortKey order T0..T9
    const again = await listAgentClaimableTasksService(s.workspaceId, 20, s.auth);
    expect(again.map((t) => t.taskId)).toEqual(claimable.map((t) => t.taskId));
  });
});
