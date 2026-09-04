import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";
import { createExecutionPlan } from "../handlers/execution-plan.handler";
import { advanceTask, listAgentClaimableTasks } from "../handlers/task.handler";
import {
  createExecutionPlanService,
  acceptExecutionPlanService,
  CreatePlanItemInput,
} from "../services/execution-plan.service";

const { tasks } = schema;

function item(over: Partial<CreatePlanItemInput> = {}): CreatePlanItemInput {
  return {
    title: over.title ?? "Draft onboarding SOP",
    decisionReason: "Standardise week-one onboarding process",
    evidenceRefs: ["note-1"],
    suggestedDomain: "operations",
    expectedCapability:
      over.expectedCapability === undefined ? "operations.sop.draft" : over.expectedCapability,
    capabilityRisk: "LOW",
    tenantPolicyDecision: "ALLOW",
    dependsOnTitles: [],
  };
}

async function seed() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "WGA delegation project",
  });
  const goal = await setWeeklyGoalService(
    {
      projectId: project.id,
      workspaceId: ws.workspaceId,
      focus: "Goal",
      triggerDecomposition: false,
      origin: "command_center",
    },
    ws.bearerToken
  );
  return { ws, projectId: project.id, weeklyPlanId: goal.weeklyPlanId };
}

describe("WGA delegation auth", () => {
  it("createExecutionPlan accepts a valid cosa delegation token when runId is present", async () => {
    const { ws, projectId, weeklyPlanId } = await seed();
    const runId = `wga_decomp_${generateSnowflake()}`;
    const token = mintCompanyDelegation({
      sub: "42",
      workspace_id: ws.workspaceId,
      run_id: runId,
      capability_ids: ["operations.execution_plan.create", "operations.task.list"],
    });

    const plan = await createExecutionPlan({
      authorization: `Bearer ${token}`,
      workspaceId: ws.workspaceId,
      projectId,
      weeklyPlanId,
      goalText: "Goal",
      runId,
      items: [item()],
    });
    expect(plan.status).toBe("draft");
    expect(plan.items[0]!.autonomyClass).toBe("AUTO");
  });

  it("createExecutionPlan rejects a token whose run_id does not match", async () => {
    const { ws, projectId, weeklyPlanId } = await seed();
    const token = mintCompanyDelegation({
      sub: "42",
      workspace_id: ws.workspaceId,
      run_id: "some_other_run",
      capability_ids: ["operations.execution_plan.create"],
    });
    await expect(
      createExecutionPlan({
        authorization: `Bearer ${token}`,
        workspaceId: ws.workspaceId,
        projectId,
        weeklyPlanId,
        goalText: "Goal",
        runId: "wga_decomp_expected",
        items: [item()],
      })
    ).rejects.toThrow(/delegation/i);
  });

  it("createExecutionPlan rejects a token missing the create capability in scope", async () => {
    const { ws, projectId, weeklyPlanId } = await seed();
    const runId = "wga_decomp_x";
    const token = mintCompanyDelegation({
      sub: "42",
      workspace_id: ws.workspaceId,
      run_id: runId,
      capability_ids: ["operations.task.list"],
    });
    await expect(
      createExecutionPlan({
        authorization: `Bearer ${token}`,
        workspaceId: ws.workspaceId,
        projectId,
        weeklyPlanId,
        goalText: "Goal",
        runId,
        items: [item()],
      })
    ).rejects.toThrow(/delegation/i);
  });

  it("advanceTask accepts a delegation token scoped to operations.task.advance + runId", async () => {
    const { ws, projectId, weeklyPlanId } = await seed();
    // materialize an AI task via the service (session path)
    const plan = await createExecutionPlanService(
      {
        workspaceId: ws.workspaceId,
        projectId,
        weeklyPlanId,
        goalText: "Goal",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item()],
      },
      ws.bearerToken
    );
    const founderId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: founderId,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });
    const accepted = await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ws.workspaceId, acceptedByMemberId: founderId.toString() },
      ws.bearerToken
    );
    const taskId = accepted.taskIds[0]!;

    const runId = "wga_sweep_1";
    const token = mintCompanyDelegation({
      sub: "42",
      workspace_id: ws.workspaceId,
      run_id: runId,
      capability_ids: ["operations.task.advance", "operations.task.list"],
    });

    const inprog = await advanceTask({
      id: taskId,
      toStatus: "in_progress",
      runId,
      authorization: `Bearer ${token}`,
      workspaceId: ws.workspaceId,
    });
    expect(inprog.status).toBe("in_progress");

    const done = await advanceTask({
      id: taskId,
      toStatus: "done",
      runId,
      authorization: `Bearer ${token}`,
      workspaceId: ws.workspaceId,
    });
    expect(done.status).toBe("done");

    const [row] = await db.select().from(tasks).where(eq(tasks.id, BigInt(taskId)));
    expect(row!.status).toBe("done");
  });

  it("advanceTask rejects a session bearer (no cosa delegation claims)", async () => {
    const { ws, projectId, weeklyPlanId } = await seed();
    const plan = await createExecutionPlanService(
      {
        workspaceId: ws.workspaceId,
        projectId,
        weeklyPlanId,
        goalText: "Goal",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item()],
      },
      ws.bearerToken
    );
    const founderId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: founderId,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });
    const accepted = await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ws.workspaceId, acceptedByMemberId: founderId.toString() },
      ws.bearerToken
    );
    await expect(
      advanceTask({
        id: accepted.taskIds[0]!,
        toStatus: "in_progress",
        runId: "r",
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
      })
    ).rejects.toThrow(/delegation/i);
  });

  it("listAgentClaimableTasks accepts a delegation token scoped to operations.task.list", async () => {
    const { ws, projectId, weeklyPlanId } = await seed();
    const plan = await createExecutionPlanService(
      {
        workspaceId: ws.workspaceId,
        projectId,
        weeklyPlanId,
        goalText: "Goal",
        origin: "command_center",
        originRef: null,
        runId: null,
        items: [item({ title: "one" }), item({ title: "two" })],
      },
      ws.bearerToken
    );
    const founderId = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id: founderId,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });
    await acceptExecutionPlanService(
      plan.id,
      { workspaceId: ws.workspaceId, acceptedByMemberId: founderId.toString() },
      ws.bearerToken
    );

    const token = mintCompanyDelegation({
      sub: "42",
      workspace_id: ws.workspaceId,
      run_id: "wga_sweep_2",
      capability_ids: ["operations.task.list", "operations.task.advance"],
    });
    const res = await listAgentClaimableTasks({
      authorization: `Bearer ${token}`,
      workspaceId: ws.workspaceId,
      limit: 10,
    });
    expect(res.tasks.length).toBe(2);
  });
});
