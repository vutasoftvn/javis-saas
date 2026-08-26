import { describe, it, expect } from "vitest";
import { createCycle, listCycles, createWeeklyPlan, createWeeklyCommitment } from "../handlers/twelve-week-year.handler";

describe("TwelveWeekYear Service", () => {
  const workspaceId = "100";

  it("creates a twelve week cycle and lists it", async () => {
    const cycle = await createCycle({
      workspaceId,
      theme: "Q3 Hyper-Growth",
      visionStatement: "Launch MVP and onboard 100 users",
      durationWeeks: 12,
    });

    expect(cycle.id).toBeDefined();
    expect(typeof cycle.id).toBe("string");
    expect(cycle.workspaceId).toBe(String(workspaceId));
    expect(cycle.theme).toBe("Q3 Hyper-Growth");
    expect(cycle.status).toBe("ACTIVE");

    const list = await listCycles({ workspaceId });
    expect(list.cycles.some((c) => c.id === cycle.id)).toBe(true);
  });

  it("creates a weekly plan and weekly commitment", async () => {
    const cycle = await createCycle({
      workspaceId,
      theme: "Execution sprint",
    });

    const plan = await createWeeklyPlan({
      workspaceId,
      cycleId: cycle.id,
      weekNo: 1,
      focus: "Customer Discovery",
      mission: "Conduct 15 customer interviews",
    });

    expect(plan.id).toBeDefined();
    expect(plan.cycleId).toBe(cycle.id);
    expect(plan.weekNo).toBe(1);

    const commitment = await createWeeklyCommitment({
      workspaceId,
      weeklyPlanId: plan.id,
      title: "Design interview questionnaire",
      plannedEffort: "4h",
      commitmentOwnerType: "FOUNDER",
    });

    expect(commitment.id).toBeDefined();
    expect(commitment.weeklyPlanId).toBe(plan.id);
    expect(commitment.title).toBe("Design interview questionnaire");
    expect(commitment.status).toBe("todo");
  });
});
