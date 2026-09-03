import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createCycle, createWeeklyPlan } from "../handlers/twelve-week-year.handler";
import { updateWeeklyPlanService } from "../services/twelve-week-year.service";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("updateWeeklyPlanService", () => {
  it("updates executionScore, outcomeScore and reflection", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Weekly Review Test");
    const cycle = await createCycle({ workspaceId, authorization, theme: "Blitz", visionStatement: "MVP", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId, authorization, cycleId: cycle.id, weekNo: 1, focus: "Tuần 1" });

    const updated = await updateWeeklyPlanService(plan.id, {
      workspaceId,
      authorization,
      executionScore: 85.5,
      outcomeScore: 70,
      reflection: "Đã hoàn thành hầu hết cam kết, cần cải thiện tốc độ phản hồi khách hàng.",
    });

    expect(updated.executionScore).toBe(85.5);
    expect(updated.outcomeScore).toBe(70);
    expect(updated.reflection).toBe("Đã hoàn thành hầu hết cam kết, cần cải thiện tốc độ phản hồi khách hàng.");
  });

  it("rejects executionScore out of 0-100 range", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Weekly Review Range Test");
    const cycle = await createCycle({ workspaceId, authorization, theme: "Blitz", visionStatement: "MVP", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId, authorization, cycleId: cycle.id, weekNo: 1, focus: "Tuần 1" });

    await expect(
      updateWeeklyPlanService(plan.id, { workspaceId, authorization, executionScore: 150 })
    ).rejects.toThrow(/executionScore/i);
  });

  it("rejects cross-workspace update with not_found or permission_denied", async () => {
    const wsA = await makeAuthedWorkspace("Workspace A Weekly");
    const wsB = await makeAuthedWorkspace("Workspace B Weekly");
    const cycle = await createCycle({ workspaceId: wsA.workspaceId, authorization: wsA.authorization, theme: "A", visionStatement: "A", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId: wsA.workspaceId, authorization: wsA.authorization, cycleId: cycle.id, weekNo: 1, focus: "A" });

    await expect(
      updateWeeklyPlanService(plan.id, { workspaceId: wsB.workspaceId, authorization: wsB.authorization, executionScore: 50 })
    ).rejects.toThrow();
  });
});
