import { describe, it, expect } from "vitest";
import { db } from "../models/db";
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
  getTaskAgentContextService,
  createTaskService,
} from "../services/task.service";

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

const CRITERIA = {
  version: 1,
  criteria: [{ id: "c1", description: "Có tài liệu", required: true, check: "rubric", rubric: "Có tài liệu" }],
};

describe("getTaskAgentContextService", () => {
  it("returns title, profile, project and done criteria of a plan-materialized task", async () => {
    const s = await seedAcceptedPlan([autoItem("Có tiêu chí", { doneCriteria: CRITERIA })]);
    const [claimable] = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    const ctx = await getTaskAgentContextService(BigInt(s.workspaceId), claimable!.taskId);
    expect(ctx).toMatchObject({
      taskId: claimable!.taskId,
      workspaceId: s.workspaceId,
      title: "Có tiêu chí",
      projectId: s.projectId,
      autonomyClass: "AUTO",
      ownerAgentProfile: "operations",
      doneCriteria: CRITERIA,
    });
  });

  it("returns null criteria when the item has none", async () => {
    const s = await seedAcceptedPlan([autoItem("Trống", {})]);
    const [claimable] = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect((await getTaskAgentContextService(BigInt(s.workspaceId), claimable!.taskId)).doneCriteria).toBeNull();
  });

  it("does not leak a task from another workspace", async () => {
    const a = await seedAcceptedPlan([autoItem("A", {})]);
    const b = await seedAcceptedPlan([autoItem("B", {})]);
    const [claimable] = await listAgentClaimableTasksService(a.workspaceId, 10, a.auth);
    await expect(
      getTaskAgentContextService(BigInt(b.workspaceId), claimable!.taskId),
    ).rejects.toThrow(/not found/);
  });

  it("rejects a task that is not materialized from a plan item", async () => {
    const s = await seedAcceptedPlan([autoItem("Có plan", {})]);
    const manual = await createTaskService(
      { workspaceId: s.workspaceId, title: "Task tạo tay", projectId: s.projectId },
      s.auth,
    );
    await expect(
      getTaskAgentContextService(BigInt(s.workspaceId), manual.id),
    ).rejects.toThrow(/not found/);
  });

  it("rejects a non-numeric task id", async () => {
    await expect(getTaskAgentContextService(1n, "abc")).rejects.toThrow(/numeric/);
  });
});
