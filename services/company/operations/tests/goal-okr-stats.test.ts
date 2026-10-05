import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createGoalService, getGoalTreeService, completeGoalService } from "../services/goals.service";
import { createObjectiveService, addKeyResultService, checkinService } from "../services/okr.service";

async function setup() {
  const user = await createTestSession({
    email: `goal-stats-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Goal Stats",
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const { goalId } = await createGoalService({
    workspaceId: user.workspaceId, title: "Goal", goalType: "strategic",
  });
  const company = await createObjectiveService({
    workspaceId: user.workspaceId, scope: "company", goalId, title: "Company O", authorization,
  });
  const project = await createObjectiveService({
    workspaceId: user.workspaceId, projectId: user.projectId,
    parentObjectiveId: company.id, title: "Project O", authorization,
  });
  return { user, authorization, goalId, company, project };
}

describe("goal tree stats from unified OKR", () => {
  it("counts company and aligned project objectives and KRs under the goal", async () => {
    const { user, authorization, goalId, company, project } = await setup();
    await addKeyResultService({ objectiveId: company.id, title: "KR company", targetValue: 10, authorization });
    await addKeyResultService({ objectiveId: project.id, title: "KR project", targetValue: 10, authorization });

    const { tree } = await getGoalTreeService(user.workspaceId);
    const node = tree.find((n) => n.id === goalId)!;
    expect(node.objectiveCount).toBe(2);
    expect(node.krTotal).toBe(2);
    expect(node.krAchieved).toBe(0);
  });

  it("marks a decrease KR achieved by progress, not by current >= target", async () => {
    const { user, authorization, goalId, project } = await setup();
    const kr = await addKeyResultService({
      objectiveId: project.id, title: "Churn", targetValue: 5, baselineValue: 10,
      scoringType: "LINEAR_DECREASE", authorization,
    });
    await checkinService(kr.id, 5, authorization);
    const { tree } = await getGoalTreeService(user.workspaceId);
    expect(tree.find((n) => n.id === goalId)!.krAchieved).toBe(1);
  });

  it("does not count a project objective without a parent under any goal", async () => {
    const { user, authorization, goalId } = await setup();
    await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, title: "Unaligned", authorization,
    });
    const { tree } = await getGoalTreeService(user.workspaceId);
    expect(tree.find((n) => n.id === goalId)!.objectiveCount).toBe(2);
  });

  it("completeGoal requires force while objectives are open, then closes objectives and KRs", async () => {
    const { user, authorization, goalId, project } = await setup();
    const kr = await addKeyResultService({ objectiveId: project.id, title: "KR", targetValue: 10, authorization });
    await expect(
      completeGoalService({ workspaceId: user.workspaceId, goalId }),
    ).rejects.toThrow(/objective/);
    const res = await completeGoalService({
      workspaceId: user.workspaceId, goalId, forceCompleteActiveObjectives: true,
    });
    expect(res.completedObjectivesCount).toBe(2);
    const { tree } = await getGoalTreeService(user.workspaceId);
    expect(tree.find((n) => n.id === goalId)!.status).toBe("completed");
    expect(kr.id).toBeTruthy();
  });
});
