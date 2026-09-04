import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
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
import { listAgentClaimableTasksService, advanceTaskByAgentService } from "../services/task.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { tasks } = schema;

function ctxFor(workspaceId: string): TenantContext {
  return Object.freeze({
    workspaceId, userId: "1", workforceMemberId: undefined,
    membershipRole: "admin", permissions: [], correlationId: "t", platformUserId: null,
  }) as unknown as TenantContext;
}

async function seedAcceptedPlan(items: CreatePlanItemInput[]) {
  const ws = await createTestWorkspaceWithMember();
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
  return { workspaceId: ws.workspaceId, auth: ws.bearerToken, plan, res };
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
    await advanceTaskByAgentService({ taskId: firstTaskId, toStatus: "done", runId: "r" }, ctxFor(s.workspaceId));

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
});
