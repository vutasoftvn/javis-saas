import { describe, it, expect } from "vitest";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  createExecutionPlan,
  listExecutionPlans,
  getExecutionPlan,
  patchExecutionPlanItem,
  acceptExecutionPlan,
  rejectExecutionPlan,
} from "../handlers/execution-plan.handler";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";

async function seed() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "WGA handler project",
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
  return {
    workspaceId: ws.workspaceId,
    projectId: project.id,
    auth: ws.bearerToken,
    weeklyPlanId: goal.weeklyPlanId,
  };
}

function planItem() {
  return {
    title: "Soạn SOP onboarding",
    decisionReason: "Chuẩn hoá quy trình onboarding tuần đầu",
    evidenceRefs: ["note-1"],
    suggestedDomain: "operations",
    expectedCapability: "operations.sop.draft",
    capabilityRisk: "LOW" as const,
    tenantPolicyDecision: "ALLOW" as const,
    dependsOnTitles: [],
  };
}

describe("execution-plan handlers", () => {
  it("create -> list -> get -> accept happy path", async () => {
    const s = await seed();
    const created = await createExecutionPlan({
      authorization: s.auth,
      workspaceId: s.workspaceId,
      projectId: s.projectId,
      weeklyPlanId: s.weeklyPlanId,
      goalText: "Goal",
      items: [planItem()],
    });
    expect(created.status).toBe("draft");

    const listed = await listExecutionPlans({
      authorization: s.auth,
      workspaceId: s.workspaceId,
      projectId: s.projectId,
      status: "draft",
    });
    expect(listed.plans.length).toBe(1);

    const got = await getExecutionPlan({
      id: created.id,
      authorization: s.auth,
      workspaceId: s.workspaceId,
    });
    expect(got.id).toBe(created.id);

    const accepted = await acceptExecutionPlan({
      id: created.id,
      authorization: s.auth,
      workspaceId: s.workspaceId,
    });
    expect(accepted.taskIds.length).toBe(1);
  });

  it("patch item drop then reject the plan", async () => {
    const s = await seed();
    const created = await createExecutionPlan({
      authorization: s.auth,
      workspaceId: s.workspaceId,
      projectId: s.projectId,
      weeklyPlanId: s.weeklyPlanId,
      goalText: "Goal",
      items: [planItem(), { ...planItem(), title: "Bỏ việc này" }],
    });
    const dropTarget = created.items.find((i) => i.title === "Bỏ việc này")!;
    const patched = await patchExecutionPlanItem({
      id: created.id,
      itemId: dropTarget.id,
      authorization: s.auth,
      workspaceId: s.workspaceId,
      drop: true,
    });
    expect(patched.status).toBe("dropped");

    await rejectExecutionPlan({ id: created.id, authorization: s.auth, workspaceId: s.workspaceId });
  });

  it("rejects a request missing the workspace header", async () => {
    const s = await seed();
    await expect(
      listExecutionPlans({
        authorization: s.auth,
        // @ts-expect-error intentionally missing header for guard test
        workspaceId: undefined,
        projectId: s.projectId,
      })
    ).rejects.toThrow();
  });

  it("returns not-found for a cross-workspace plan id", async () => {
    const a = await seed();
    const b = await seed();
    const created = await createExecutionPlan({
      authorization: a.auth,
      workspaceId: a.workspaceId,
      projectId: a.projectId,
      weeklyPlanId: a.weeklyPlanId,
      goalText: "Goal",
      items: [planItem()],
    });
    await expect(
      getExecutionPlan({ id: created.id, authorization: b.auth, workspaceId: b.workspaceId })
    ).rejects.toThrow();
  });
});
