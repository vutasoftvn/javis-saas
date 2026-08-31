import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  createOkrCycle,
  createObjective,
  listOkrCycles,
  listObjectives,
  deleteObjective,
  getObjectiveProgress,
} from "../handlers/okr.handler";
import {
  createCycle,
  createWeeklyPlan,
  createWeeklyCommitment,
  listTwelveWeekCycles,
  listTwelveWeekPlans,
  listTwelveWeekCommitments,
} from "../handlers/twelve-week-year.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("MVP OKR & 12-Week Contracts", () => {
  it("creates, lists, and deletes OKR cycles and objectives", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("OKR MVP Test");

    const emptyCycles = await listOkrCycles({ workspaceId, authorization });
    expect(emptyCycles.meta.dataState).toBe("empty");
    expect(emptyCycles.data).toEqual([]);

    const cycle = await createOkrCycle({
      workspaceId,
      authorization,
      name: "Q3 2026",
    });

    const objective = await createObjective({
      workspaceId,
      authorization,
      cycleId: cycle.id,
      title: "Achieve Product-Market Fit",
      why: "Ensure long-term growth",
    });

    const cycles = await listOkrCycles({ workspaceId, authorization });
    expect(cycles.data.length).toBe(1);
    expect(cycles.data[0].name).toBe("Q3 2026");

    const objectives = await listObjectives({ workspaceId, authorization });
    expect(objectives.data.length).toBe(1);
    expect(objectives.data[0].title).toBe("Achieve Product-Market Fit");

    const progress = await getObjectiveProgress({
      id: objective.id,
      workspaceId,
      authorization,
    });
    expect(progress.objectiveId).toBe(objective.id);
    expect(progress.score).toBe(0);

    await deleteObjective({ id: objective.id, workspaceId, authorization });
    const afterDelete = await listObjectives({ workspaceId, authorization });
    expect(afterDelete.data).toEqual([]);
  });

  it("creates and lists 12-Week cycles, plans, and commitments", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("12-Week MVP Test");

    const emptyCycles = await listTwelveWeekCycles({ workspaceId, authorization });
    expect(emptyCycles.meta.dataState).toBe("empty");

    const cycle = await createCycle({
      workspaceId,
      authorization,
      theme: "Execution Blitz",
      visionStatement: "Deliver Full MVP",
      durationWeeks: 12,
    });

    const plan = await createWeeklyPlan({
      workspaceId,
      authorization,
      cycleId: cycle.id,
      weekNo: 1,
      focus: "Foundation and Strategy contracts",
    });

    const commitment = await createWeeklyCommitment({
      workspaceId,
      authorization,
      weeklyPlanId: plan.id,
      title: "Ship Truth-Only Frontend Integration",
    });

    const cycles = await listTwelveWeekCycles({ workspaceId, authorization });
    expect(cycles.data.length).toBe(1);
    expect(cycles.data[0].visionStatement).toBe("Deliver Full MVP");

    const plans = await listTwelveWeekPlans({ workspaceId, authorization });
    expect(plans.data.length).toBe(1);
    expect(plans.data[0].focus).toBe("Foundation and Strategy contracts");

    const commitments = await listTwelveWeekCommitments({ workspaceId, authorization });
    expect(commitments.data.length).toBe(1);
    expect(commitments.data[0].title).toBe("Ship Truth-Only Frontend Integration");
  });
});
