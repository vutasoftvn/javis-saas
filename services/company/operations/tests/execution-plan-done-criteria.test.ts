import { describe, expect, it } from "vitest";
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

const CRITERIA = {
  version: 1,
  criteria: [
    { id: "c1", description: "Lưu tài liệu", required: true, check: "rubric", rubric: "Có tài liệu" },
  ],
};

async function seedDraftPlan(items: CreatePlanItemInput[]) {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const project = await createProject({
    authorization: ws.bearerToken, workspaceId: ws.workspaceId, title: "done criteria project",
  });
  const founderId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: founderId, workspaceId: BigInt(ws.workspaceId), memberType: "HUMAN",
    humanUserId: BigInt(ws.userId), roleTitle: "Founder", status: "active",
  });
  const goal = await setWeeklyGoalService(
    { projectId: project.id, workspaceId: ws.workspaceId, focus: "Goal", triggerDecomposition: false, origin: "command_center" },
    ws.bearerToken,
  );
  const plan = await createExecutionPlanService(
    {
      workspaceId: ws.workspaceId, projectId: project.id, weeklyPlanId: goal.weeklyPlanId,
      goalText: "Goal", origin: "command_center", originRef: null, runId: null, items,
    },
    ws.bearerToken,
  );
  return { workspaceId: ws.workspaceId, auth: ws.bearerToken, plan, projectId: String(project.id), founderId };
}

async function seedAcceptedPlanWith(items: CreatePlanItemInput[]) {
  const s = await seedDraftPlan(items);
  const res = await acceptExecutionPlanService(
    s.plan.id, { workspaceId: s.workspaceId, acceptedByMemberId: s.founderId.toString() }, s.auth,
  );
  return { ...s, res };
}

function autoItem(title: string, over: Partial<CreatePlanItemInput> = {}): CreatePlanItemInput {
  return {
    title, decisionReason: "lý do đủ dài cho item",
    evidenceRefs: ["e1"], suggestedDomain: "operations",
    expectedCapability: "operations.sop.draft", capabilityRisk: "LOW",
    tenantPolicyDecision: "ALLOW", dependsOnTitles: [], ...over,
  };
}

describe("execution plan item done_criteria", () => {
  it("stores validated criteria on the item and returns them in the view", async () => {
    const s = await seedDraftPlan([autoItem("A", { doneCriteria: CRITERIA })]);
    expect(s.plan.items[0]!.doneCriteria).toEqual(CRITERIA);
  });

  it("rejects malformed criteria with invalid_argument", async () => {
    await expect(
      seedDraftPlan([autoItem("A", { doneCriteria: { version: 1, criteria: [] } })]),
    ).rejects.toThrow(/criteria must contain 1\.\.10 items/);
  });

  it("copies criteria to weekly_commitments.done_criteria on accept", async () => {
    const s = await seedAcceptedPlanWith([autoItem("A", { doneCriteria: CRITERIA })]);
    const [commitment] = await db
      .select({ doneCriteria: schema.weeklyCommitments.doneCriteria })
      .from(schema.weeklyCommitments)
      .where(eq(schema.weeklyCommitments.projectId, BigInt(s.projectId)));
    expect(commitment?.doneCriteria).toEqual(CRITERIA);
  });

  it("items without criteria still work (criteria optional by default)", async () => {
    const s = await seedDraftPlan([autoItem("A", {})]);
    expect(s.plan.items[0]!.doneCriteria).toBeNull();
  });

  it("WGA_REQUIRE_DONE_CRITERIA=1 rejects a non-LOW risk item without criteria", async () => {
    process.env.WGA_REQUIRE_DONE_CRITERIA = "1";
    try {
      await expect(
        seedDraftPlan([autoItem("A", { capabilityRisk: "MEDIUM" })]),
      ).rejects.toThrow(/done_criteria is required/);
      await expect(seedDraftPlan([autoItem("B", { capabilityRisk: "LOW" })])).resolves.toBeTruthy();
      await expect(seedDraftPlan([autoItem("C", { capabilityRisk: null })])).resolves.toBeTruthy();
    } finally {
      delete process.env.WGA_REQUIRE_DONE_CRITERIA;
    }
  });
});
