import { describe, expect, it } from "vitest";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { createOkrCycle, createObjective, addKeyResult, checkin, getObjectiveProgress } from "../handlers/okr.handler";

async function makeCycle() {
  const workspace = await createWorkspace({ name: `OKR Test ${Date.now()}` });
  const cycle = await createOkrCycle({ workspaceId: workspace.id, name: "Q1" });
  return { workspace, cycle };
}

describe("createOkrCycle", () => {
  it("creates a cycle with the default draft status", async () => {
    const { cycle } = await makeCycle();
    expect(cycle.id).toBeTruthy();
    expect(typeof cycle.id).toBe("string");
    expect(cycle.status).toBe("draft");
  });

  it("rejects a cycle for a workspace that doesn't exist", async () => {
    await expect(createOkrCycle({ workspaceId: 999999999, name: "Bad" })).rejects.toThrow();
  });
});

describe("createObjective", () => {
  it("creates an objective under a cycle", async () => {
    const { workspace, cycle } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue" });
    expect(objective.id).toBeTruthy();
    expect(typeof objective.id).toBe("string");
    expect(objective.cycleId).toBe(cycle.id);
  });

  it("rejects an objective under a cycle that doesn't exist (real DB FK)", async () => {
    const { workspace } = await makeCycle();
    await expect(
      createObjective({ workspaceId: workspace.id, cycleId: 999999999, title: "Orphan" })
    ).rejects.toThrow();
  });
});

describe("addKeyResult + checkin + getObjectiveProgress", () => {
  it("scores an objective from its key results after check-ins", async () => {
    const { workspace, cycle } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue" });
    const kr1 = await addKeyResult({ objectiveId: objective.id, title: "Sign 10 customers", targetValue: 10 });
    const kr2 = await addKeyResult({ objectiveId: objective.id, title: "Reach $10k MRR", targetValue: 10000 });

    await checkin({ id: kr1.id, value: 5 });
    await checkin({ id: kr2.id, value: 10000 });

    const progress = await getObjectiveProgress({ objectiveId: objective.id });
    expect(progress.score).toBeCloseTo(0.75);
    expect(progress.keyResults).toHaveLength(2);
  });
});
